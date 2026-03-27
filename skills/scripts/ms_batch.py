#!/usr/bin/env python3
import copy
import json
import os
import sys
import urllib.request
import subprocess
import uuid
import time
from pathlib import Path

BASE_URL = os.environ.get('METERSPHERE_BASE_URL', '').rstrip('/')
AK = os.environ.get('METERSPHERE_ACCESS_KEY') or os.environ.get('CORDYS_ACCESS_KEY', '')
SK = os.environ.get('METERSPHERE_SECRET_KEY') or os.environ.get('CORDYS_SECRET_KEY', '')


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def signature():
    plain = f"{AK}|{uuid.uuid4()}|{int(time.time()*1000)}"
    p = subprocess.run([
        'openssl', 'enc', '-aes-128-cbc', '-K', SK.encode().hex(), '-iv', AK.encode().hex(), '-base64', '-A', '-nosalt'
    ], input=plain.encode(), capture_output=True, check=True)
    return p.stdout.decode().strip()


def headers():
    if not BASE_URL or not AK or not SK:
        die('缺少 METERSPHERE_BASE_URL / METERSPHERE_ACCESS_KEY / METERSPHERE_SECRET_KEY')
    return {'Content-Type': 'application/json', 'accessKey': AK, 'signature': signature()}


def request_json(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers(), method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


def create_functional_cases(payloads):
    return [request_json('POST', '/functional/case/add', item) for item in payloads]


def create_api_definitions_and_cases(bundle):
    results = []
    for definition, case_list in zip(bundle.get('definitions', []), bundle.get('cases', [])):
        r = request_json('POST', '/api/definition/add', definition)
        created = r.get('data') or {}
        api_id = created.get('id') if isinstance(created, dict) else None
        case_results = []
        if api_id:
            for case_tpl in case_list:
                case_body = copy.deepcopy(case_tpl)
                case_body['projectId'] = definition['projectId']
                case_body['apiDefinitionId'] = api_id
                case_body['request']['moduleId'] = definition['moduleId']
                case_results.append(request_json('POST', '/api/case/add', case_body))
        results.append({'definition': r, 'cases': case_results})
    return results


def main():
    if len(sys.argv) != 3:
        die('用法: ms_batch.py functional-cases <json-file> | api-import <json-file>')
    mode, file_path = sys.argv[1], sys.argv[2]
    payload = json.loads(Path(file_path).read_text(encoding='utf-8'))
    if mode == 'functional-cases':
        print(json.dumps(create_functional_cases(payload), ensure_ascii=False, indent=2))
    elif mode == 'api-import':
        print(json.dumps(create_api_definitions_and_cases(payload), ensure_ascii=False, indent=2))
    else:
        die('未知模式')

if __name__ == '__main__':
    main()
