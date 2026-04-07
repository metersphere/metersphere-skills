#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib import request, error

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ENV_FILE = SKILL_DIR / '.env'

if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

BASE_URL = os.environ.get('METERSPHERE_BASE_URL', '').rstrip('/')
ACCESS_KEY = os.environ.get('METERSPHERE_ACCESS_KEY') or os.environ.get('METERSPHERE_ACCESS_KEY', '')
SECRET_KEY = os.environ.get('METERSPHERE_SECRET_KEY') or os.environ.get('METERSPHERE_SECRET_KEY', '')


def die(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(1)


def signature() -> str:
    plain = f"{ACCESS_KEY}|{uuid.uuid4()}|{int(time.time() * 1000)}"
    proc = subprocess.run([
        'openssl', 'enc', '-aes-128-cbc',
        '-K', SECRET_KEY.encode('utf-8').hex(),
        '-iv', ACCESS_KEY.encode('utf-8').hex(),
        '-base64', '-A', '-nosalt'
    ], input=plain.encode('utf-8'), capture_output=True, check=True)
    return proc.stdout.decode('utf-8').strip()


def headers():
    if not BASE_URL or not ACCESS_KEY or not SECRET_KEY:
        die('缺少 METERSPHERE_BASE_URL / METERSPHERE_ACCESS_KEY / METERSPHERE_SECRET_KEY')
    return {
        'Content-Type': 'application/json',
        'accessKey': ACCESS_KEY,
        'signature': signature(),
    }


def post_json(path: str, body: dict):
    req = request.Request(
        BASE_URL + path,
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers=headers(),
        method='POST',
    )
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8', errors='replace'))


def get_json(path: str):
    req = request.Request(BASE_URL + path, headers=headers(), method='GET')
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8', errors='replace'))


def fetch_all_functional_cases(project_id: str, keyword: str):
    current = 1
    page_size = 100
    rows = []
    while True:
        body = {'projectId': project_id, 'current': current, 'pageSize': page_size}
        if keyword:
            body['keyword'] = keyword
        data = post_json('/functional/case/page', body).get('data') or {}
        lst = data.get('list') or []
        rows.extend(lst)
        total = data.get('total') or len(rows)
        if len(rows) >= total or not lst:
            break
        current += 1
    return rows


def fetch_case_reviews(case_id: str):
    data = post_json('/functional/case/review/page', {'caseId': case_id, 'current': 1, 'pageSize': 100}).get('data') or {}
    return data.get('list') or []


def fetch_case_detail(case_id: str):
    return (get_json(f'/functional/case/detail/{case_id}').get('data') or {})


def main():
    if len(sys.argv) < 2:
        die('用法: ms_review_summary.py <projectId> [keyword]')
    project_id = sys.argv[1]
    keyword = sys.argv[2] if len(sys.argv) > 2 else ''

    cases = fetch_all_functional_cases(project_id, keyword)
    out = []
    for c in cases:
        case_id = c.get('id')
        review_items = fetch_case_reviews(case_id)
        detail = fetch_case_detail(case_id)
        
        # 获取用例的评审状态
        review_status = detail.get('reviewStatus')

        # 新逻辑：review_status in ['PASS', 'UN_PASS']  # 只有评审完成
        is_reviewed = review_status in ['PASS', 'UN_PASS']
        
        out.append({
            'caseId': case_id,
            'num': c.get('num'),
            'name': c.get('name'),
            'caseEditType': c.get('caseEditType'),
            'reviewStatus': review_status,
            'lastExecuteResult': detail.get('lastExecuteResult'),
            'bugCount': detail.get('bugCount', 0),
            'caseReviewCount': detail.get('caseReviewCount', 0),
            'testPlanCount': detail.get('testPlanCount', 0),
            'demandCount': detail.get('demandCount', 0),
            'reviewCount': len(review_items),
            'reviewed': is_reviewed,  # 使用修复后的逻辑
            'reviews': [
                {
                    'reviewId': r.get('reviewId'),
                    'reviewNum': r.get('reviewNum'),
                    'reviewName': r.get('reviewName'),
                    'reviewStatus': r.get('reviewStatus'),
                    'caseReviewStatus': r.get('status'),
                }
                for r in review_items
            ],
        })

    print(json.dumps({
        'projectId': project_id,
        'keyword': keyword,
        'totalCases': len(out),
        'reviewedCases': sum(1 for x in out if x['reviewed']),
        'unreviewedCases': sum(1 for x in out if not x['reviewed']),
        'totalBugLinks': sum(int(x.get('bugCount') or 0) for x in out),
        'list': out,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        die(f'HTTP {e.code}: {detail}')
    except Exception as e:
        die(str(e))
