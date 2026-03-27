#!/usr/bin/env python3
import copy
import json
import re
import sys
import urllib.request
from pathlib import Path

USAGE = '''
用法:
  ms_generate.py functional-cases <projectId> <moduleId> <templateId> <requirement-file>
  ms_generate.py api-import <projectId> <moduleId> <openapi-file-or-url>
'''


def load_text(path: str) -> str:
    p = Path(path)
    if p.exists():
        return p.read_text(encoding='utf-8')
    if path.startswith('http://') or path.startswith('https://'):
        with urllib.request.urlopen(path, timeout=30) as r:
            return r.read().decode('utf-8', errors='replace')
    raise FileNotFoundError(path)


def split_requirement_items(text: str):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    items = []
    for line in lines:
        clean = re.sub(r'^[\-\*\d\.\)\(\s]+', '', line).strip()
        if len(clean) >= 4:
            items.append(clean)
    if not items:
        items = [text.strip()]
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen[:50]


def infer_priority(text: str):
    t = text.lower()
    if any(k in t for k in ['登录', '支付', '权限', '下单', '注册', '核心', 'critical', 'login', 'pay']):
        return 'P0'
    if any(k in t for k in ['查询', '搜索', '导出', '上传', '保存']):
        return 'P1'
    return 'P2'


def infer_tags(text: str):
    tags = []
    mapping = {
        '登录': '登录', '注册': '注册', '支付': '支付', '权限': '权限', '查询': '查询', '搜索': '搜索',
        '导出': '导出', '导入': '导入', '上传': '上传', '下载': '下载', 'api': '接口', '接口': '接口'
    }
    for k, v in mapping.items():
        if k.lower() in text.lower() and v not in tags:
            tags.append(v)
    return tags[:5]


def build_case_variants(item: str):
    return [
        (f'{item}-主流程', item, '系统按需求正确处理主流程，结果符合预期'),
        (f'{item}-异常场景', f'{item}，并覆盖异常输入、非法输入、缺少必要信息等情况', '系统对异常输入给出正确拦截、提示或失败处理'),
        (f'{item}-边界场景', f'{item}，并覆盖长度边界、空值边界、数量边界、状态切换边界', '系统在边界条件下行为稳定，结果符合设计预期'),
    ]


def build_functional_cases(project_id: str, module_id: str, template_id: str, text: str):
    items = split_requirement_items(text)
    out = []
    for item in items:
        priority = infer_priority(item)
        tags = infer_tags(item)
        for idx, (name, desc, expected) in enumerate(build_case_variants(item), 1):
            out.append({
                'projectId': project_id,
                'templateId': template_id,
                'moduleId': module_id,
                'name': name[:255],
                'caseEditType': 'TEXT',
                'textDescription': desc,
                'expectedResult': expected,
                'description': f'根据需求自动生成的功能用例，优先级={priority}，类型={idx}',
                'aiCreate': True,
                'customFields': [],
                'tags': tags,
            })
    return out[:120]


def parse_openapi_source(text: str):
    try:
        return json.loads(text)
    except Exception:
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except Exception as e:
            raise RuntimeError('无法解析 OpenAPI/Swagger 文档，请提供 JSON 或 YAML') from e


def sample_value(schema_type: str, name: str = ''):
    if schema_type == 'integer':
        return '1'
    if schema_type == 'number':
        return '1'
    if schema_type == 'boolean':
        return 'true'
    if 'id' in name.lower():
        return '1001'
    return 'test'


def json_example_from_schema(schema: dict):
    if not isinstance(schema, dict):
        return None
    if 'example' in schema:
        return schema['example']
    t = schema.get('type')
    if t == 'object':
        props = schema.get('properties') or {}
        result = {}
        for k, v in props.items():
            val = json_example_from_schema(v)
            result[k] = val if val is not None else sample_value((v or {}).get('type', 'string'), k)
        return result
    if t == 'array':
        item = json_example_from_schema((schema.get('items') or {}))
        return [item] if item is not None else []
    if t == 'integer':
        return 1
    if t == 'number':
        return 1
    if t == 'boolean':
        return True
    return 'test'


def build_assertions(success_expected='200'):
    return [
        {
            'enable': True,
            'name': '状态码断言',
            'assertionType': 'RESPONSE_CODE',
            'condition': 'EQUALS',
            'expectedValue': success_expected,
        }
    ]


def build_http_request(method: str, path: str, summary: str, operation: dict):
    body_type = 'NONE'
    json_value = ''
    if 'requestBody' in operation:
        content = operation.get('requestBody', {}).get('content', {})
        if 'application/json' in content:
            body_type = 'JSON'
            schema = content['application/json'].get('schema') or {}
            ex = content['application/json'].get('example')
            if ex is None:
                examples = content['application/json'].get('examples') or {}
                if isinstance(examples, dict) and examples:
                    first = next(iter(examples.values()))
                    ex = first.get('value') if isinstance(first, dict) else None
            if ex is None:
                ex = json_example_from_schema(schema)
            json_value = json.dumps(ex if ex is not None else {}, ensure_ascii=False, indent=2)
        elif 'application/x-www-form-urlencoded' in content:
            body_type = 'WWW_FORM'
        elif 'multipart/form-data' in content:
            body_type = 'FORM_DATA'
        else:
            body_type = 'RAW'
    query = []
    rest = []
    headers = []
    for p in operation.get('parameters', []) or []:
        schema = p.get('schema') or {}
        value = p.get('example')
        if value is None:
            value = sample_value(schema.get('type', 'string'), p.get('name', ''))
        entry = {
            'key': p.get('name', ''),
            'value': str(value),
            'enable': True,
            'description': p.get('description'),
            'paramType': schema.get('type', 'string') or 'string',
            'required': p.get('required', False),
            'minLength': None,
            'maxLength': None,
            'encode': False,
        }
        where = p.get('in')
        if where == 'query':
            query.append(entry)
        elif where == 'path':
            rest.append(entry)
        elif where == 'header':
            headers.append({'key': entry['key'], 'value': entry['value'], 'enable': True, 'description': entry['description']})
    body = {
        'bodyType': body_type,
        'noneBody': {} if body_type == 'NONE' else None,
        'formDataBody': {'formValues': []},
        'wwwFormBody': {'formValues': []},
        'jsonBody': {'enableJsonSchema': body_type == 'JSON', 'jsonValue': json_value, 'jsonSchema': None},
        'xmlBody': {'value': ''},
        'rawBody': {'value': ''},
        'binaryBody': {'description': '', 'file': None},
    }
    return {
        'polymorphicName': 'MsHTTPElement',
        'stepId': '',
        'resourceId': '',
        'projectId': None,
        'name': summary or f'{method.upper()} {path}',
        'enable': True,
        'children': [{
            'polymorphicName': 'MsCommonElement',
            'stepId': None,
            'resourceId': None,
            'projectId': None,
            'name': None,
            'enable': True,
            'children': [],
            'parent': None,
            'csvIds': None,
            'preProcessorConfig': {'enableGlobal': False, 'processors': []},
            'postProcessorConfig': {'enableGlobal': False, 'processors': []},
            'assertionConfig': {'enableGlobal': False, 'assertions': build_assertions('200')},
        }],
        'parent': None,
        'csvIds': None,
        'customizeRequest': False,
        'customizeRequestEnvEnable': False,
        'path': path,
        'method': method.upper(),
        'body': body,
        'headers': headers,
        'rest': rest,
        'query': query,
        'otherConfig': {'connectTimeout': 60000, 'responseTimeout': 60000, 'certificateAlias': '', 'followRedirects': True, 'autoRedirects': False},
        'authConfig': {'authType': 'NONE', 'basicAuth': {'userName': '', 'password': '', 'valid': False}, 'digestAuth': {'userName': '', 'password': '', 'valid': False}, 'httpauthValid': False},
        'moduleId': '',
        'num': None,
        'mockNum': None,
    }


def build_default_response():
    return [{
        'id': None,
        'statusCode': '200',
        'defaultFlag': True,
        'name': None,
        'headers': [],
        'body': {
            'bodyType': 'JSON',
            'jsonBody': {'enableJsonSchema': False, 'jsonValue': '{ }', 'jsonSchema': {'type': 'string', 'properties': {}, 'enable': True}},
            'xmlBody': {'value': None},
            'rawBody': {'value': None},
            'binaryBody': {'sendAsBody': False, 'description': None, 'file': None},
        },
    }]


def set_assertion(request_obj: dict, expected_code: str):
    req = copy.deepcopy(request_obj)
    if req.get('children'):
        child = req['children'][0]
        child['assertionConfig'] = {'enableGlobal': False, 'assertions': build_assertions(expected_code)}
    return req


def build_case_variants_for_api(summary: str, req: dict, has_required: bool, has_params: bool):
    cases = []
    success_req = set_assertion(req, '200')
    cases.append({
        'name': f'{summary[:180]}-成功场景',
        'priority': 'P1',
        'status': 'PROCESSING',
        'request': success_req,
        'aiCreate': True,
    })
    if has_required:
        miss = copy.deepcopy(req)
        for group in ['query', 'rest']:
            for item in miss.get(group, []):
                if item.get('required'):
                    item['value'] = ''
                    break
        miss = set_assertion(miss, '400')
        cases.append({
            'name': f'{summary[:180]}-必填缺失',
            'priority': 'P1',
            'status': 'PROCESSING',
            'request': miss,
            'aiCreate': True,
        })
    if has_params:
        edge = copy.deepcopy(req)
        for group in ['query', 'rest']:
            for item in edge.get(group, []):
                if item.get('paramType') == 'string':
                    item['value'] = 'X' * 128
                    break
        edge = set_assertion(edge, '200')
        cases.append({
            'name': f'{summary[:180]}-边界场景',
            'priority': 'P2',
            'status': 'PROCESSING',
            'request': edge,
            'aiCreate': True,
        })
    return cases


def build_openapi_import(project_id: str, module_id: str, text: str):
    spec = parse_openapi_source(text)
    defs = []
    cases = []
    for path, path_item in (spec.get('paths') or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
            if method not in path_item:
                continue
            op = path_item[method] or {}
            summary = op.get('summary') or op.get('operationId') or f'{method.upper()} {path}'
            req = build_http_request(method, path, summary, op)
            definition = {
                'projectId': project_id,
                'moduleId': module_id,
                'name': summary[:255],
                'protocol': 'HTTP',
                'method': method.upper(),
                'path': path,
                'status': 'PROCESSING',
                'description': op.get('description') or '',
                'request': req,
                'response': build_default_response(),
            }
            defs.append(definition)
            has_required = any(x.get('required') for x in req.get('query', []) + req.get('rest', []))
            has_params = bool(req.get('query') or req.get('rest'))
            cases.append(build_case_variants_for_api(summary, req, has_required, has_params))
    return {'definitions': defs, 'cases': cases}


def main():
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    mode = sys.argv[1]
    if mode == 'functional-cases':
        if len(sys.argv) != 6:
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        project_id, module_id, template_id, req_file = sys.argv[2:6]
        text = load_text(req_file)
        print(json.dumps(build_functional_cases(project_id, module_id, template_id, text), ensure_ascii=False, indent=2))
    elif mode == 'api-import':
        if len(sys.argv) != 5:
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        project_id, module_id, src = sys.argv[2:5]
        text = load_text(src)
        print(json.dumps(build_openapi_import(project_id, module_id, text), ensure_ascii=False, indent=2))
    else:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
