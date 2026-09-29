#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2 接口用例变体生成器（纯 Python，stdlib only，无网络）。

输入：`GET /api/definition/get/{id}` 返回的 definition detail（request 为 JSON
字符串，也兼容已解析的 dict）。输出：SaveApiTestCaseRequest 形变体列表。

三大变体规则：
  - 成功场景：深拷贝请求 + RESPONSE_CODE 断言 200
  - 必填缺失：仅当 query/rest 存在必填参数时 → 第一个必填置空 + 断言 400
  - 边界场景：仅当存在 string 参数时 → 第一个 string 设为 128 个 'x' + 断言 200

断言注入位置（v2 实测，见 tests/v2/fixtures/definition_get.json 与
DoneClaim）：request.hashTree[] 追加 type=Assertions 节点
（io.metersphere.api.dto.definition.request.assertions.MsAssertions），状态码
断言存放在该节点 regex[0]：
  {type:'Regex', enable:True, subject:'Response Code', expression:'200', ...}
为满足规范载荷，regex[0] 同时携带 name/assertionType/condition/expectedValue
字段（服务端容忍，落库回读时仅保留 subject/expression 等 v2 运行时字段）。

命令行：
  python3 ms_generate_case.py <definition-detail.json> [-]
支持裸 detail、{success,data:{...}} 包裹体两种输入；失败时向 stderr 输出错误并以
非零退出码退出（不打印伪造的成功行）。
"""
import argparse
import copy
import json
import sys

ASSERTIONS_CLAZZ = 'io.metersphere.api.dto.definition.request.assertions.MsAssertions'
RESPONSE_CODE_SUBJECT = 'Response Code'


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def _load_request(definition_detail: dict) -> dict:
    """归一化 definition detail 的 request 为 dict；解析失败抛出带上下文的 ValueError。"""
    request = definition_detail.get('request')
    if request is None:
        raise ValueError('definition detail 缺少 request 字段，无法生成用例变体')
    if isinstance(request, str):
        try:
            return json.loads(request)
        except ValueError as exc:
            raise ValueError(f'definition detail 的 request 不是合法 JSON 字符串: {exc}') from exc
    if isinstance(request, dict):
        return request
    if isinstance(request, (bytes, bytearray)):
        try:
            return json.loads(request.decode('utf-8'))
        except ValueError as exc:
            raise ValueError(f'definition detail 的 request 不是合法 JSON 字节串: {exc}') from exc
    raise ValueError(f'definition detail 的 request 类型不支持: {type(request).__name__}')


def _params(request: dict, group: str) -> list:
    items = request.get(group)
    return items if isinstance(items, list) else []


def _first_matching(request: dict, groups, predicate) -> tuple:
    for group in groups:
        for index, item in enumerate(_params(request, group)):
            if isinstance(item, dict) and predicate(item):
                return group, index
    return None


def _first_required(request: dict):
    return _first_matching(request, ('query', 'rest'), lambda p: bool(p.get('required')))


def _first_string_param(request: dict):
    def is_string(p):
        return p.get('type') == 'string' or p.get('paramType') == 'string'
    return _first_matching(request, ('query', 'rest'), is_string)


def build_assertion_node(expected_value) -> dict:
    """构造 v2 Assertions 节点（含 RESPONSE_CODE 断言于 regex[0]，携带规范载荷字段）。"""
    expected_value = int(expected_value)
    return {
        'type': 'Assertions',
        'clazzName': ASSERTIONS_CLAZZ,
        'name': '状态码断言',
        'enable': True,
        'hashTree': [],
        'regex': [{
            'type': 'Regex',
            'enable': True,
            'subject': RESPONSE_CODE_SUBJECT,
            'expression': str(expected_value),
            'description': f'{RESPONSE_CODE_SUBJECT} has: {expected_value}',
            'assumeSuccess': False,
            'testType': 2,
            # 规范载荷字段（后端宽容，落库回读时不保留）
            'name': '状态码断言',
            'assertionType': 'RESPONSE_CODE',
            'condition': 'EQUALS',
            'expectedValue': expected_value,
        }],
        'jsonPath': [],
        'jsr223': [],
        'xpath2': [],
        'duration': {'enable': True, 'label': None, 'type': 'Duration', 'value': 0, 'valid': False},
        'document': {
            'enable': True,
            'type': 'JSON',
            'data': {
                'jsonFollowAPI': 'false',
                'xmlFollowAPI': 'false',
                'json': [],
                'xml': [],
                'assertionName': None,
                'include': False,
                'typeVerification': False,
            },
            'label': None,
        },
    }


def _with_assertion(request: dict, expected_value) -> dict:
    compiled = copy.deepcopy(request)
    node = build_assertion_node(expected_value)
    hash_tree = compiled.get('hashTree')
    if isinstance(hash_tree, list):
        hash_tree.append(node)
    else:
        compiled['hashTree'] = [node]
    return compiled


def build_case_variants(definition_detail: dict) -> list:
    """根据接口定义生成功能相同的接口用例变体列表。

    返回 list[dict]，每个变体的 request 为紧凑 JSON 字符串（json.loads 可无损
    还原；落库写入时需由写入端 json.loads 回对象）。
    解析失败或输入不含 request 时抛出 ValueError（不产生部分变体）。
    """
    request = _load_request(definition_detail)

    def_name = definition_detail.get('name') or '未命名接口'
    def_id = definition_detail.get('id')
    project_id = definition_detail.get('projectId')

    variants = []
    success = _with_assertion(request, 200)
    variants.append({
        'name': f'{def_name}-成功场景',
        'priority': 'P1',
        'apiDefinitionId': def_id,
        'projectId': project_id,
        'status': 'PROCESSING',
        'request': json.dumps(success, ensure_ascii=False, separators=(',', ':')),
        'description': f'验证接口 {def_name} 正常返回，断言状态码 200',
    })

    required = _first_required(request)
    if required is not None:
        group, index = required
        miss = copy.deepcopy(request)
        miss[group][index]['value'] = ''
        miss = _with_assertion(miss, 400)
        variants.append({
            'name': f'{def_name}-必填缺失',
            'priority': 'P1',
            'apiDefinitionId': def_id,
            'projectId': project_id,
            'status': 'PROCESSING',
            'request': json.dumps(miss, ensure_ascii=False, separators=(',', ':')),
            'description': f'缺失第一个必填参数 {group}.{index} 时返回 400',
        })

    string_param = _first_string_param(request)
    if string_param is not None:
        group, index = string_param
        edge = copy.deepcopy(request)
        edge[group][index]['value'] = 'x' * 128
        edge = _with_assertion(edge, 200)
        variants.append({
            'name': f'{def_name}-边界场景',
            'priority': 'P2',
            'apiDefinitionId': def_id,
            'projectId': project_id,
            'status': 'PROCESSING',
            'request': json.dumps(edge, ensure_ascii=False, separators=(',', ':')),
            'description': f'第一个 string 参数 {group}.{index} 输入 128 个字符时返回 200',
        })

    return variants


def _read_input(path: str) -> str:
    if path == '-':
        return sys.stdin.read()
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except OSError as exc:
        raise ValueError(f'无法读取输入文件 {path}: {exc}') from exc


def _parse_detail(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f'输入不是合法 JSON: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('输入 JSON 必须是对象（definition detail 或 {success,data} 包裹体）')
    # 兼容 {success,data:{...}} 包裹体：存在 data 键且顶层没有 request 时取 data 层
    if isinstance(data.get('data'), dict) and data.get('request') is None:
        data = data['data']
    if not isinstance(data, dict) or not isinstance(data.get('request'), (str, dict, bytes, bytearray)):
        raise ValueError('输入中缺少 definition request，无法生成用例变体')
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog='ms_generate_case.py',
        description='v2 接口用例变体生成器（纯本地，无网络）：输入 definition detail JSON，输出变体 JSON 数组',
    )
    parser.add_argument('detail', help='definition detail JSON 文件路径，或 - 读 stdin')
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.detail)
        detail = _parse_detail(text)
        variants = build_case_variants(detail)
    except ValueError as exc:
        die(f'错误: {exc}')
    print(json.dumps(variants, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())