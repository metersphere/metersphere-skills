# -*- coding: utf-8 -*-
"""ms_generate_case.py 单元测试（v2 接口用例变体生成器）。

断言注入位置（根据实测 v2 DEFINITION GET 与 api-case create 回读确认）：
  request.hashTree[] 中追加一个 type=Assertions 的节点
  （clazzName=io.metersphere.api.dto.definition.request.assertions.MsAssertions），
  状态码断言存放在该节点 regex[0]：
    {type:'Regex', enable:True, subject:'Response Code', expression:'200', ...}
  同时携带规范载荷字段 {name:'状态码断言', assertionType:'RESPONSE_CODE',
  condition:'EQUALS', expectedValue:200}（服务端接受但在落库回读时丢弃，见 DoneClaim）。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, 'skills/scripts/v2')

from ms_generate_case import build_case_variants  # noqa: E402

FIXTURE = str(Path(__file__).resolve().parent / "fixtures" / "definition_get.json")

FI_LIVE_DEF_ID = '<definitionId>'
FI_PROJECT_ID = '<projectId>'


def load_live_detail() -> dict:
    """读取真实 API 抓取的 definition detail（fixture 为唯一数据来源）。"""
    with open(FIXTURE, encoding='utf-8') as f:
        envelope = json.load(f)
    return envelope['data']


def make_detail(name, request_obj, **overrides) -> dict:
    """构造与真实 definition/get 响应同构的 detail（request 为 JSON 字符串）。"""
    detail = {
        'id': FI_LIVE_DEF_ID,
        'projectId': FI_PROJECT_ID,
        'name': name,
        'method': 'GET',
        'path': '/api/books',
        'request': json.dumps(request_obj, ensure_ascii=False),
    }
    detail.update(overrides)
    return detail


def make_sampler(query=None, rest=None, headers=None, hash_tree=None) -> dict:
    """构造与真实 v2 MsHTTPSamplerProxy 同构的 request 元素。"""
    req = {
        'type': 'HTTPSamplerProxy',
        'clazzName': 'io.metersphere.api.dto.definition.request.sampler.MsHTTPSamplerProxy',
        'name': 'sampler',
        'enable': True,
        'method': 'GET',
        'path': '/api/books',
        'id': FI_LIVE_DEF_ID,
        'hashTree': hash_tree,
        'query': query,
        'rest': rest or [],
        'headers': headers or [],
        'body': {'type': None, 'raw': None, 'format': None, 'kvs': [], 'binary': []},
        'arguments': None,
        'authManager': {'authType': 'NONE', 'sslCertification': None},
        'domain': None,
        'protocol': 'HTTP',
        'url': '',
    }
    return req


def query_param(name, required=False, param_type='string', value=''):
    return {
        'name': name,
        'value': value,
        'type': param_type,
        'files': None,
        'description': '',
        'contentType': None,
        'enable': True,
        'urlEncode': False,
        'required': required,
        'min': None,
        'max': None,
        'file': False,
        'valid': True,
    }


def find_assertions_node(parsed_request):
    """在解析后的 request 中定位 v2 断言节点（request.hashTree[] 的 Assertions 节点）。"""
    for node in parsed_request.get('hashTree') or []:
        if isinstance(node, dict) and node.get('type') == 'Assertions':
            return node
    return None


def find_status_code_assertion(parsed_request):
    """返回 (断言节点, regex 状态码断言 dict)；未找到则返回 (None, None)。"""
    node = find_assertions_node(parsed_request)
    if node is None:
        return None, None
    for r in node.get('regex') or []:
        if r.get('subject') == 'Response Code':
            return node, r
    return node, None


# ---------------------------------------------------------------- (a)
def test_query_required_and_string_produce_three_variants():
    req = make_sampler(query=[
        query_param('keyword', required=True, param_type='string'),
        query_param('limit', required=False, param_type='integer', value='10'),
    ])
    detail = make_detail('搜索书籍', req)

    variants = build_case_variants(detail)

    assert len(variants) == 3
    assert variants[0]['name'] == '搜索书籍-成功场景'
    assert variants[1]['name'] == '搜索书籍-必填缺失'
    assert variants[2]['name'] == '搜索书籍-边界场景'

    # 成功场景：断言 200
    r0 = json.loads(variants[0]['request'])
    _, a0 = find_status_code_assertion(r0)
    assert a0 is not None
    assert a0['expression'] == '200'

    # 必填缺失：query 中第一个必填参数被置空，断言 400
    r1 = json.loads(variants[1]['request'])
    assert r1['query'][0]['name'] == 'keyword'
    assert r1['query'][0]['value'] == ''
    _, a1 = find_status_code_assertion(r1)
    assert a1['expression'] == '400'

    # 边界场景：第一个 string 参数为 128 个 'x'，断言 200
    r2 = json.loads(variants[2]['request'])
    assert r2['query'][0]['name'] == 'keyword'
    assert r2['query'][0]['value'] == 'x' * 128
    assert len(r2['query'][0]['value']) == 128
    _, a2 = find_status_code_assertion(r2)
    assert a2['expression'] == '200'


# ---------------------------------------------------------------- (b)
def test_no_params_only_success_variant():
    detail = make_detail('无参接口', make_sampler(query=None))
    variants = build_case_variants(detail)

    assert len(variants) == 1
    assert variants[0]['name'] == '无参接口-成功场景'
    assert json.loads(variants[0]['request'])['hashTree'] is not None


# ---------------------------------------------------------------- (c)
def test_fixture_json_string_request_parses_and_generates():
    detail = load_live_detail()  # request 为真实 JSON 字符串，且含一个 required rest 参数
    assert isinstance(detail['request'], str)

    variants = build_case_variants(detail)

    assert len(variants) == 2  # 成功 + 必填缺失；无 string 参数 → 无边界变体
    assert variants[0]['apiDefinitionId'] == FI_LIVE_DEF_ID
    assert variants[0]['projectId'] == FI_PROJECT_ID

    r1 = json.loads(variants[1]['request'])
    assert r1['rest'][0]['name'] == 'id'
    assert r1['rest'][0]['value'] == ''
    _, a1 = find_status_code_assertion(r1)
    assert a1['expression'] == '400'


# ---------------------------------------------------------------- (d)
def test_priorities_p1_p1_p2():
    req = make_sampler(query=[
        query_param('keyword', required=True, param_type='string'),
    ])
    variants = build_case_variants(make_detail('优先级接口', req))

    assert [v['priority'] for v in variants] == ['P1', 'P1', 'P2']


# ---------------------------------------------------------------- (e)
def test_assertion_payload_shape_at_v2_placement():
    req = make_sampler(query=[query_param('keyword', required=True, param_type='string')])
    variants = build_case_variants(make_detail('断言形状', req))

    parsed = json.loads(variants[0]['request'])
    node, assertion = find_status_code_assertion(parsed)

    assert node is not None
    assert node['type'] == 'Assertions'
    assert node['clazzName'] == 'io.metersphere.api.dto.definition.request.assertions.MsAssertions'
    assert node['name'] == '状态码断言'
    assert node['enable'] is True

    assert assertion is not None
    assert assertion['enable'] is True
    assert assertion['name'] == '状态码断言'
    assert assertion['assertionType'] == 'RESPONSE_CODE'
    assert assertion['condition'] == 'EQUALS'
    assert assertion['expectedValue'] == 200
    # v2 运行时字段必须同时存在（服务端落库回读时保留的是这两个字段）
    assert assertion['subject'] == 'Response Code'
    assert assertion['expression'] == '200'

    _, miss = find_status_code_assertion(json.loads(variants[1]['request']))
    assert miss['expectedValue'] == 400
    assert miss['expression'] == '400'


# ---------------------------------------------------------------- (f)
def test_malformed_request_string_raises_clear_error():
    detail = make_detail('坏请求', {'type': 'HTTPSamplerProxy', 'hashTree': None})
    detail['request'] = '{not-valid-json!!'

    with pytest.raises(ValueError) as exc:
        build_case_variants(detail)
    assert 'request' in str(exc.value)


def test_missing_request_field_raises_clear_error():
    detail = {
        'id': FI_LIVE_DEF_ID,
        'projectId': FI_PROJECT_ID,
        'name': '没有请求',
        'method': 'GET',
        'path': '/x',
    }
    with pytest.raises(ValueError) as exc:
        build_case_variants(detail)
    assert 'request' in str(exc.value)


# ------------------------------------------------- 增强行为
def test_deepcopy_no_mutation_of_input():
    req = make_sampler(query=[query_param('keyword', required=True, param_type='string')])
    detail = make_detail('原始对象', req)
    original = json.dumps(req, ensure_ascii=False, sort_keys=True)

    build_case_variants(detail)

    # 输入 request 不受影响（原 hashTree 仍为 null，query 值未改）
    assert json.dumps(json.loads(detail['request']), ensure_ascii=False, sort_keys=True) == original
    assert json.loads(detail['request'])['hashTree'] is None


def test_already_parsed_dict_request_supported():
    req = make_sampler()
    detail = make_detail('已解析对象', req)
    detail['request'] = req  # 直接传 dict，而非 JSON 字符串

    variants = build_case_variants(detail)
    assert len(variants) == 1
    assert json.loads(variants[0]['request']) is not None


def test_each_variant_is_separate_request_object():
    req = make_sampler(query=[query_param('keyword', required=True, param_type='string')])
    variants = build_case_variants(make_detail('独立对象', req))

    r0 = json.loads(variants[0]['request'])
    r1 = json.loads(variants[1]['request'])
    r2 = json.loads(variants[2]['request'])

    # 三种变体互不共享断言对象，且各含独立 Assertions 节点
    assert find_assertions_node(r0) is not find_assertions_node(r1)
    assert find_assertions_node(r1) is not find_assertions_node(r2)
    assert len(find_assertions_node(r0)['regex']) == 1


def test_prompt_injection_round_trips_as_plain_string():
    evil_name = '接口"; drop table users; --'
    req = make_sampler(query=[query_param('kw"; rm -rf /', required=True, param_type='string')])
    detail = make_detail(evil_name, req)

    variants = build_case_variants(detail)

    assert variants[0]['name'] == f'{evil_name}-成功场景'
    parsed = json.loads(variants[1]['request'])
    assert parsed['query'][0]['name'] == 'kw"; rm -rf /'
    assert parsed['query'][0]['value'] == ''


def test_status_and_protocol_fields_present():
    req = make_sampler()
    variants = build_case_variants(make_detail('状态字段', req))
    v = variants[0]

    assert v['status'] == 'PROCESSING'
    assert v['priority'] == 'P1'
    assert v['apiDefinitionId'] == FI_LIVE_DEF_ID
    assert v['projectId'] == FI_PROJECT_ID
    assert isinstance(v['description'], str) and v['description']


# ------------------------------------------------- CLI
_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "scripts" / "v2" / "ms_generate_case.py"


def _run_cli(args, stdin_text=None):
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)] + args,
        capture_output=True, text=True, input=stdin_text,
    )
    return proc


def test_cli_emits_json_array_to_stdout(tmp_path):
    req = make_sampler(query=[query_param('keyword', required=True, param_type='string')])
    detail = make_detail('CLI接口', req)
    f = tmp_path / 'detail.json'
    f.write_text(json.dumps(detail, ensure_ascii=False), encoding='utf-8')

    proc = _run_cli([str(f)])

    assert proc.returncode == 0
    variants = json.loads(proc.stdout)  # stdout 必须是纯 JSON，不得夹带 "generated 3" 之类文案
    assert len(variants) == 3
    assert variants[1]['name'] == 'CLI接口-必填缺失'


def test_cli_accepts_api_envelope(tmp_path):
    envelope = {'success': True, 'message': None, 'data': load_live_detail()}
    f = tmp_path / 'envelope.json'
    f.write_text(json.dumps(envelope, ensure_ascii=False), encoding='utf-8')

    proc = _run_cli([str(f)])

    assert proc.returncode == 0
    variants = json.loads(proc.stdout)
    assert variants[0]['apiDefinitionId'] == FI_LIVE_DEF_ID


def test_cli_reads_stdin_dash():
    req = make_sampler()
    detail = make_detail('stdin接口', req)

    proc = _run_cli(['-'], stdin_text=json.dumps(detail, ensure_ascii=False))

    assert proc.returncode == 0
    variants = json.loads(proc.stdout)
    assert len(variants) == 1


def test_cli_error_exit_nonzero_and_stderr():
    proc = _run_cli(['/nonexistent/def.json'])

    assert proc.returncode != 0
    assert proc.stdout == ''  # 不得输出伪造的成功行
    assert proc.stderr.strip() != ''


def test_cli_malformed_json_error_to_stderr(tmp_path):
    f = tmp_path / 'bad.json'
    f.write_text('{oops', encoding='utf-8')

    proc = _run_cli([str(f)])

    assert proc.returncode != 0
    assert proc.stdout == ''
    assert 'JSON' in proc.stderr or 'json' in proc.stderr or 'request' in proc.stderr