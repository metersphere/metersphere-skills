#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def die(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(1)


def run_json(project_id: str, case_id: str):
    proc = subprocess.run(
        ['python3', str(SCRIPT_DIR / 'ms_case_report.py'), project_id, case_id],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def md_lines(report: dict):
    s = report['summary']
    d = report['detail']
    bugs = report.get('bugs') or []
    reviews = report.get('reviews') or []
    steps = d.get('steps') or []

    lines = []
    lines.append(f"# 功能用例报告：{s.get('name') or '-'}")
    lines.append('')
    lines.append('## 用例摘要')
    lines.append(f"- 用例ID：`{s.get('caseId')}`")
    lines.append(f"- 编号：`{s.get('num')}`")
    lines.append(f"- 模块：{s.get('moduleName') or s.get('moduleId') or '-'}")
    lines.append(f"- 优先级：{s.get('functionalPriority') or '-'}")
    lines.append(f"- 编辑模式：{s.get('caseEditType') or '-'}")
    lines.append(f"- 评审状态：{s.get('reviewStatus') or '-'}")
    lines.append(f"- 最近执行结果：{s.get('lastExecuteResult') or '-'}")
    lines.append(f"- 是否被评审过：{'是' if s.get('reviewed') else '否'}")
    lines.append(f"- 关联缺陷数：{s.get('bugCount', 0)}")
    lines.append(f"- 关联评审数：{s.get('caseReviewCount', 0)}")
    lines.append(f"- 关联测试计划数：{s.get('testPlanCount', 0)}")
    lines.append(f"- 关联需求数：{s.get('demandCount', 0)}")
    lines.append('')

    if d.get('prerequisite'):
        lines.append('## 前置条件')
        lines.append(d['prerequisite'])
        lines.append('')

    if d.get('description'):
        lines.append('## 备注')
        lines.append(str(d['description']))
        lines.append('')

    if steps:
        lines.append('## 步骤')
        for idx, step in enumerate(steps, 1):
            desc = step.get('desc') or '-'
            result = step.get('result') or '-'
            lines.append(f"### 步骤 {idx}")
            lines.append(f"- 操作：{desc}")
            lines.append(f"- 预期：{result}")
        lines.append('')

    lines.append('## 缺陷')
    if bugs:
        for i, bug in enumerate(bugs, 1):
            lines.append(f"### 缺陷 {i}")
            lines.append(f"- 缺陷ID：`{bug.get('id')}`")
            lines.append(f"- 编号：`{bug.get('num')}`")
            lines.append(f"- 标题：{bug.get('name') or '-'}")
            lines.append(f"- 状态：{bug.get('statusName') or '-'}")
            lines.append(f"- 处理人：{bug.get('handleUserName') or '-'}")
            lines.append(f"- 创建人：{bug.get('createUserName') or '-'}")
    else:
        lines.append('- 暂无已关联缺陷')
    lines.append('')

    lines.append('## 评审记录')
    if reviews:
        for i, review in enumerate(reviews, 1):
            lines.append(f"### 评审 {i}")
            lines.append(f"- 评审ID：`{review.get('reviewId')}`")
            lines.append(f"- 评审编号：`{review.get('reviewNum')}`")
            lines.append(f"- 评审名称：{review.get('reviewName') or '-'}")
            lines.append(f"- 评审单状态：{review.get('reviewStatus') or '-'}")
            lines.append(f"- 该用例评审状态：{review.get('caseReviewStatus') or '-'}")
    else:
        lines.append('- 暂无评审记录')
    lines.append('')

    return '\n'.join(lines).strip() + '\n'


def main():
    if len(sys.argv) != 3:
        die('用法: ms_case_report_md.py <projectId> <caseId>')
    project_id = sys.argv[1]
    case_id = sys.argv[2]
    report = run_json(project_id, case_id)
    print(md_lines(report))


if __name__ == '__main__':
    main()
