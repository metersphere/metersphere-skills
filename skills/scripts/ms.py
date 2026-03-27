#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from urllib import request, error

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None):
        if dotenv_path and os.path.exists(dotenv_path):
            with open(dotenv_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ENV_FILE = SKILL_DIR / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

BASE_URL = os.environ.get('METERSPHERE_BASE_URL', '').rstrip('/')
ACCESS_KEY = os.environ.get('METERSPHERE_ACCESS_KEY') or os.environ.get('CORDYS_ACCESS_KEY', '')
SECRET_KEY = os.environ.get('METERSPHERE_SECRET_KEY') or os.environ.get('CORDYS_SECRET_KEY', '')
PROJECT_ID = os.environ.get('METERSPHERE_PROJECT_ID', '')
ORG_ID = os.environ.get('METERSPHERE_ORGANIZATION_ID', '100001')
HEADERS_JSON = os.environ.get('METERSPHERE_HEADERS_JSON', '')
PROTOCOLS_JSON = os.environ.get('METERSPHERE_PROTOCOLS_JSON', '["HTTP"]')
ORGANIZATION_LIST_PATH = os.environ.get('METERSPHERE_ORGANIZATION_LIST_PATH', '/system/organization/list')
PROJECT_LIST_PATH = os.environ.get('METERSPHERE_PROJECT_LIST_PATH', '/project/list/options/{organizationId}')
PROJECT_LIST_SYSTEM_PATH = os.environ.get('METERSPHERE_PROJECT_LIST_SYSTEM_PATH', '/system/project/list')
PROJECT_LIST_BY_ORG_PATH = os.environ.get('METERSPHERE_PROJECT_LIST_BY_ORG_PATH', '/organization/project/list/{organizationId}')
FUNCTIONAL_MODULE_TREE_PATH = os.environ.get('METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH', '/functional/case/module/tree/{projectId}')
FUNCTIONAL_TEMPLATE_FIELD_PATH = os.environ.get('METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH', '/functional/case/default/template/field/{projectId}')
API_MODULE_TREE_PATH = os.environ.get('METERSPHERE_API_MODULE_TREE_PATH', '/api/definition/module/tree')

PATHS = {
    'organization': {'list': ORGANIZATION_LIST_PATH, 'get': '', 'create': ''},
    'project': {'list': PROJECT_LIST_PATH, 'get': '', 'create': ''},
    'functional-module': {'list': FUNCTIONAL_MODULE_TREE_PATH, 'get': '', 'create': ''},
    'functional-template': {'list': FUNCTIONAL_TEMPLATE_FIELD_PATH, 'get': '', 'create': ''},
    'api-module': {'list': API_MODULE_TREE_PATH, 'get': '', 'create': ''},
    'functional-case': {
        'list': os.environ.get('METERSPHERE_FUNCTIONAL_CASE_LIST_PATH', '/functional/case/page'),
        'get': os.environ.get('METERSPHERE_FUNCTIONAL_CASE_GET_PATH', '/functional/case/detail/{id}'),
        'create': os.environ.get('METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH', '/functional/case/add'),
    },
    'api': {
        'list': os.environ.get('METERSPHERE_API_DEFINITION_LIST_PATH', '/api/definition/page'),
        'get': os.environ.get('METERSPHERE_API_DEFINITION_GET_PATH', '/api/definition/get-detail/{id}'),
        'create': os.environ.get('METERSPHERE_API_DEFINITION_CREATE_PATH', '/api/definition/add'),
    },
    'api-case': {
        'list': os.environ.get('METERSPHERE_API_CASE_LIST_PATH', '/api/case/page'),
        'get': os.environ.get('METERSPHERE_API_CASE_GET_PATH', '/api/case/get-detail/{id}'),
        'create': os.environ.get('METERSPHERE_API_CASE_CREATE_PATH', '/api/case/add'),
    },
}


def die(msg: str):
    print(f'错误: {msg}', file=sys.stderr)
    sys.exit(1)


def generate_signature():
    try:
        import uuid, time, base64
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        plain = f"{ACCESS_KEY}|{uuid.uuid4()}|{int(time.time() * 1000)}".encode('utf-8')
        cipher = AES.new(SECRET_KEY.encode('utf-8'), AES.MODE_CBC, ACCESS_KEY.encode('utf-8'))
        encrypted = cipher.encrypt(pad(plain, AES.block_size))
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception:
        import uuid, time, subprocess
        plain = f"{ACCESS_KEY}|{uuid.uuid4()}|{int(time.time() * 1000)}"
        proc = subprocess.run([
            'openssl', 'enc', '-aes-128-cbc',
            '-K', SECRET_KEY.encode('utf-8').hex(),
            '-iv', ACCESS_KEY.encode('utf-8').hex(),
            '-base64', '-A', '-nosalt'
        ], input=plain.encode('utf-8'), capture_output=True, check=True)
        return proc.stdout.decode('utf-8').strip()


def make_headers():
    headers = {'Content-Type': 'application/json'}
    if not ACCESS_KEY:
        die('未设置 METERSPHERE_ACCESS_KEY')
    if not SECRET_KEY:
        die('未设置 METERSPHERE_SECRET_KEY')
    headers['accessKey'] = ACCESS_KEY
    headers['signature'] = generate_signature()
    if HEADERS_JSON:
        headers.update(json.loads(HEADERS_JSON))
    return headers


def normalize_payload(resource: str, raw: str):
    data = json.loads(raw)
    if isinstance(data, dict):
        if PROJECT_ID and not data.get('projectId'):
            data['projectId'] = PROJECT_ID
        if ORG_ID and not data.get('organizationId'):
            data['organizationId'] = ORG_ID
        if resource in ('api', 'api-case') and not data.get('protocols'):
            try:
                data['protocols'] = json.loads(PROTOCOLS_JSON)
            except Exception:
                data['protocols'] = ['HTTP']
    return data


def default_list_payload(resource: str, keyword: str):
    data = {'current': 1, 'pageSize': 20}
    if keyword:
        data['keyword'] = keyword
    if PROJECT_ID:
        data['projectId'] = PROJECT_ID
    if ORG_ID:
        data['organizationId'] = ORG_ID
    if resource in ('api', 'api-case'):
        try:
            data['protocols'] = json.loads(PROTOCOLS_JSON)
        except Exception:
            data['protocols'] = ['HTTP']
    return data


def do_request(method: str, path: str, body=None):
    if not BASE_URL:
        die('未设置 METERSPHERE_BASE_URL')
    url = BASE_URL + path
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = request.Request(url, data=data, headers=make_headers(), method=method.upper())
    try:
        with request.urlopen(req) as resp:
            charset = resp.headers.get_content_charset() or 'utf-8'
            print(resp.read().decode(charset, errors='replace'))
    except error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        die(f'HTTP {e.code}: {detail}')
    except Exception as e:
        die(str(e))


def usage():
    print('''ms — MeterSphere CLI

用法:
  ms <resource> <action> [args...]
  ms raw <METHOD> <PATH> [JSON]

资源:
  organization
  project
  functional-module
  functional-template
  api-module
  functional-case
  api
  api-case

动作:
  list [关键词|JSON]
  get <id>
  create <JSON>

示例:
  ms organization list
  ms organization list 默认
  ms project list
  ms project list all
  ms project list 100001
  ms functional-module list 100001100001
  ms functional-template list 100001100001
  ms api-module list 100001100001
  ms functional-case list 登录
''')


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd in ('help', '-h', '--help'):
        usage()
        return

    if cmd == 'raw':
        if len(sys.argv) < 4:
            die('raw 需要 METHOD 和 PATH')
        method = sys.argv[2]
        path = sys.argv[3]
        body = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
        do_request(method, path, body)
        return

    resource = cmd
    if resource not in PATHS:
        die(f'不支持的资源: {resource}')
    if len(sys.argv) < 3:
        die('缺少 action')
    action = sys.argv[2]

    if action == 'list':
        arg = sys.argv[3] if len(sys.argv) > 3 else ''
        if resource == 'organization':
            if arg.startswith('{'):
                body = json.loads(arg)
            elif arg:
                body = {'current': 1, 'pageSize': 20, 'keyword': arg}
            else:
                body = {'current': 1, 'pageSize': 20}
            do_request('POST', ORGANIZATION_LIST_PATH, body)
        elif resource == 'project':
            if arg == 'all':
                do_request('GET', PROJECT_LIST_SYSTEM_PATH)
            elif arg:
                do_request('GET', PROJECT_LIST_BY_ORG_PATH.replace('{organizationId}', arg))
            else:
                do_request('GET', PROJECT_LIST_PATH.replace('{organizationId}', ORG_ID))
        elif resource == 'functional-module':
            project_id = arg or PROJECT_ID
            if not project_id:
                die('functional-module list 需要 projectId')
            do_request('GET', FUNCTIONAL_MODULE_TREE_PATH.replace('{projectId}', project_id))
        elif resource == 'functional-template':
            project_id = arg or PROJECT_ID
            if not project_id:
                die('functional-template list 需要 projectId')
            do_request('GET', FUNCTIONAL_TEMPLATE_FIELD_PATH.replace('{projectId}', project_id))
        elif resource == 'api-module':
            project_id = arg or PROJECT_ID
            if not project_id:
                die('api-module list 需要 projectId')
            do_request('POST', API_MODULE_TREE_PATH, {'projectId': project_id, 'protocols': json.loads(PROTOCOLS_JSON)})
        else:
            body = normalize_payload(resource, arg) if arg.startswith('{') else default_list_payload(resource, arg)
            do_request('POST', PATHS[resource]['list'], body)
    elif action == 'get':
        if len(sys.argv) < 4:
            die('get 需要 id')
        path = PATHS[resource]['get'].replace('{id}', sys.argv[3])
        do_request('GET', path)
    elif action == 'create':
        if len(sys.argv) < 4:
            die('create 需要 JSON body')
        body = normalize_payload(resource, sys.argv[3])
        do_request('POST', PATHS[resource]['create'], body)
    else:
        die(f'不支持的 action: {action}')


if __name__ == '__main__':
    main()
