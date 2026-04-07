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
import mimetypes
from urllib.parse import urlencode

BASE_URL = os.environ.get('METERSPHERE_BASE_URL', '').rstrip('/')
AK = os.environ.get('METERSPHERE_ACCESS_KEY') or os.environ.get('METERSPHERE_ACCESS_KEY', '')
SK = os.environ.get('METERSPHERE_SECRET_KEY') or os.environ.get('METERSPHERE_SECRET_KEY', '')


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

def request_multipart(method, path, fields=None, files=None):
    """发送multipart/form-data请求"""
    import io
    import random
    import string
    
    if fields is None:
        fields = {}
    if files is None:
        files = {}
    
    # 生成边界字符串
    boundary = '----WebKitFormBoundary' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # 构建multipart数据
    data_parts = []
    
    # 添加字段
    for key, value in fields.items():
        data_parts.append(f'--{boundary}')
        data_parts.append(f'Content-Disposition: form-data; name="{key}"')
        data_parts.append('')
        data_parts.append(str(value))
    
    # 添加文件（如果有）
    for key, file_info in files.items():
        filename = file_info.get('filename', 'file')
        content = file_info.get('content', b'')
        content_type = file_info.get('content_type', 'application/octet-stream')
        
        data_parts.append(f'--{boundary}')
        data_parts.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"')
        data_parts.append(f'Content-Type: {content_type}')
        data_parts.append('')
        data_parts.append('')  # 空行后是二进制内容
        
    data_parts.append(f'--{boundary}--')
    data_parts.append('')
    
    # 构建请求体
    body = '\r\n'.join(data_parts).encode('utf-8')
    
    # 如果是文件，需要特殊处理
    if files:
        # 对于文件上传，我们需要构建真正的multipart数据
        import tempfile
        import io as io_module
        
        # 创建临时文件来构建multipart数据
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
            # 写入boundary
            for part in data_parts[:-2]:  # 排除最后的boundary结束标记
                tmp.write(part.encode('utf-8') + b'\r\n')
            
            # 写入文件内容
            for key, file_info in files.items():
                content = file_info.get('content', b'')
                if isinstance(content, str):
                    content = content.encode('utf-8')
                tmp.write(content)
                tmp.write(b'\r\n')
            
            # 写入结束boundary
            tmp.write(data_parts[-2].encode('utf-8') + b'\r\n')
            tmp.write(data_parts[-1].encode('utf-8'))
            tmp.flush()
            
            # 读取文件内容
            with open(tmp.name, 'rb') as f:
                body = f.read()
        
        os.unlink(tmp.name)
    
    # 设置headers
    req_headers = headers()
    req_headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
    req_headers['Content-Length'] = str(len(body))
    
    req = urllib.request.Request(BASE_URL + path, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


def create_functional_cases(payloads):
    results = []
    for item in payloads:
        # 确保数据格式正确
        # 1. 确保tags是数组，不是字符串
        if 'tags' in item and isinstance(item['tags'], str):
            try:
                item['tags'] = json.loads(item['tags'])
            except:
                item['tags'] = []
        
        # 2. 确保customFields是数组，不是字符串
        if 'customFields' in item and isinstance(item['customFields'], str):
            try:
                item['customFields'] = json.loads(item['customFields'])
            except:
                item['customFields'] = []
        
        # 3. 确保有正确的templateId
        if not item.get('templateId'):
            # 尝试从环境变量获取默认templateId
            import os
            template_id = os.environ.get('METERSPHERE_DEFAULT_TEMPLATE_ID')
            if template_id:
                item['templateId'] = template_id
            else:
                # 如果没有设置环境变量，使用硬编码值并发出警告
                item['templateId'] = '1163437937827890'  # 项目1163437937827840的默认templateId
                print("警告: 使用硬编码的 templateId (1163437937827890)。建议设置 METERSPHERE_DEFAULT_TEMPLATE_ID 环境变量。")
                print("警告: 这可能导致数据被错误归属到项目 1163437937827840。请确保使用正确的项目 ID。")
        
        # 4. 确保有versionId（必需字段）
        if not item.get('versionId'):
            # 尝试从环境变量获取默认versionId
            import os
            version_id = os.environ.get('METERSPHERE_DEFAULT_VERSION_ID')
            if version_id:
                item['versionId'] = version_id
            else:
                # 如果没有设置环境变量，使用硬编码值并发出警告
                item['versionId'] = '1163437937827887'  # 项目1163437937827840的默认versionId
                print("警告: 使用硬编码的 versionId (1163437937827887)。建议设置 METERSPHERE_DEFAULT_VERSION_ID 环境变量。")
                print("警告: 这可能导致数据被错误归属到项目 1163437937827840。请确保使用正确的项目 ID。")
        
        # 4. 使用curl发送multipart/form-data请求
        try:
            import tempfile
            import subprocess
            
            # 创建临时文件保存JSON数据
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(item, f, ensure_ascii=False)
                json_file = f.name
            
            # 生成签名
            plain = f'{AK}|{uuid.uuid4()}|{int(time.time()*1000)}'
            p = subprocess.run([
                'openssl', 'enc', '-aes-128-cbc', '-K', SK.encode().hex(), '-iv', AK.encode().hex(), '-base64', '-A', '-nosalt'
            ], input=plain.encode(), capture_output=True, check=True)
            signature = p.stdout.decode().strip()
            
            # 构建curl命令
            curl_cmd = [
                'curl', '-X', 'POST',
                '-H', f'accessKey: {AK}',
                '-H', f'signature: {signature}',
                '-F', f'request=@{json_file};type=application/json',
                f'{BASE_URL}/functional/case/add'
            ]
            
            # 执行curl命令
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            
            # 解析响应
            if result.stdout:
                response_data = json.loads(result.stdout)
                results.append(response_data)
            else:
                results.append({'error': 'No response', 'data': None})
            
            # 清理临时文件
            import os
            os.unlink(json_file)
            
        except Exception as e:
            print(f"创建用例失败: {e}", file=sys.stderr)
            results.append({'error': str(e), 'data': None})
    
    return results


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
    
    # 支持从标准输入读取（当文件路径为"-"时）
    if file_path == '-':
        payload = json.loads(sys.stdin.read())
    else:
        payload = json.loads(Path(file_path).read_text(encoding='utf-8'))
    
    if mode == 'functional-cases':
        print(json.dumps(create_functional_cases(payload), ensure_ascii=False, indent=2))
    elif mode == 'api-import':
        print(json.dumps(create_api_definitions_and_cases(payload), ensure_ascii=False, indent=2))
    else:
        die('未知模式')

if __name__ == '__main__':
    main()
