#!/usr/bin/env python3
"""v2 功能用例草稿生成器（纯本地，无网络）。

用法:
  ms_generate.py functional-cases <projectId> <moduleId> <requirement-file> [--templateId <id>] [--versionId <id>]

仅支持 functional-cases 动作；api-import 模式未移植（v2 不支持 OpenAPI 导入）。
输出为 JSON 数组（每个元素为一个 v2 EditTestCaseRequest 草稿），写入 stdout。
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

USAGE = '''用法:
  ms_generate.py functional-cases <projectId> <moduleId> <requirement-file> [--templateId <id>] [--versionId <id>]
仅支持 functional-cases；api-import 未移植。'''


def die(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(1)


def load_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f'需求文件不存在: {path}')
    return p.read_text(encoding='utf-8')


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


def build_test_steps(requirement: str, case_type: int) -> list:
    """根据需求构建测试步骤（与 v3 一致）。"""
    if case_type == 1:  # 主流程
        steps = [
            {"num": 0, "desc": "准备测试环境", "result": "环境准备就绪"},
            {"num": 1, "desc": f"执行{requirement}操作", "result": "操作执行成功"},
            {"num": 2, "desc": "验证操作结果", "result": "结果符合预期"}
        ]
    elif case_type == 2:  # 异常场景
        steps = [
            {"num": 0, "desc": "准备测试环境", "result": "环境准备就绪"},
            {"num": 1, "desc": f"输入异常数据执行{requirement}", "result": "系统正确拦截异常输入"},
            {"num": 2, "desc": "验证错误提示", "result": "错误提示清晰明确"}
        ]
    else:  # 边界场景
        steps = [
            {"num": 0, "desc": "准备测试环境", "result": "环境准备就绪"},
            {"num": 1, "desc": f"输入边界值执行{requirement}", "result": "系统正确处理边界值"},
            {"num": 2, "desc": "验证边界条件结果", "result": "边界条件下系统行为稳定"}
        ]
    return steps


def build_case_variants(item: str):
    return [
        (f'{item}-主流程', '系统按需求正确处理主流程，结果符合预期'),
        (f'{item}-异常场景', f'{item}，并覆盖异常输入、非法输入、缺少必要信息等情况'),
        (f'{item}-边界场景', f'{item}，并覆盖长度边界、空值边界、数量边界、状态切换边界'),
    ]


def build_functional_cases(project_id: str, module_id: str, text: str,
                           template_id: str = None, version_id: str = None):
    items = split_requirement_items(text)
    out = []
    for item in items:
        priority = infer_priority(item)
        for idx, (name, _desc) in enumerate(build_case_variants(item), 1):
            case = {
                'name': name[:255],
                'projectId': project_id,
                'nodeId': module_id,
                # 本地脚本无法解析模块名，nodePath 采用 "/" + moduleId 占位，
                # 与真实格式（"/" + 模块名，如 "/未规划用例"）保持一致；
                # 批量写入前需按模块树确认真实 nodePath（见 Gap-resolution #6）。
                'nodePath': '/' + module_id,
                'priority': priority,
                'steps': json.dumps(build_test_steps(item, idx), ensure_ascii=False),
                'caseEditType': 'STEP',
            }
            if template_id:
                case['templateId'] = template_id
            if version_id:
                case['versionId'] = version_id
            out.append(case)
    return out[:120]


def main():
    parser = argparse.ArgumentParser(
        prog='ms_generate.py',
        description='v2 功能用例草稿生成器（纯本地，无网络）',
    )
    parser.add_argument('action', help='仅支持 functional-cases')
    parser.add_argument('project_id', nargs='?', help='项目 ID')
    parser.add_argument('module_id', nargs='?', help='模块 ID（nodeId）')
    parser.add_argument('requirement_file', nargs='?', help='需求文件路径')
    parser.add_argument('--templateId', dest='template_id', default=None, help='模板 ID（可选）')
    parser.add_argument('--versionId', dest='version_id', default=None,
                        help='版本 ID（可选，缺省时读取 METERSPHERE_DEFAULT_VERSION_ID）')
    args = parser.parse_args()

    if args.action != 'functional-cases':
        die(f'不支持的 action: {args.action}（仅支持 functional-cases；api-import 未移植）')
    if not (args.project_id and args.module_id and args.requirement_file):
        die(USAGE)

    try:
        text = load_text(args.requirement_file)
    except FileNotFoundError as e:
        die(str(e))

    version_id = args.version_id or os.environ.get('METERSPHERE_DEFAULT_VERSION_ID') or None
    cases = build_functional_cases(args.project_id, args.module_id, text,
                                   args.template_id, version_id)
    print(json.dumps(cases, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()