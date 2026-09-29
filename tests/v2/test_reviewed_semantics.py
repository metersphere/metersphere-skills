# -*- coding: utf-8 -*-
"""F8a/F8b 评审语义谓词的单元测试（纯本地，无网络依赖）。

表驱动覆盖 (reviews 非空 × reviewStatus) 的四种组合，
断言 v2 报告脚本采用的并集规则（AGENTS.md:56）：
    reviewed = (reviews 非空) OR (reviewStatus ∈ {PASS, UN_PASS})

ms_review_summary.py 在 main() 内联计算该谓词（:130），
ms_case_report.py 在构建报告字段时内联计算（:151）。
本测试以同一表达式为规范来源，锁定两个脚本共享的语义。
"""
import pytest


def union_reviewed(reviews, review_status):
    """规范谓词：与 ms_review_summary.py:130 / ms_case_report.py:151 一致。"""
    return (len(reviews) > 0) or (review_status in ("PASS", "UN_PASS"))


@pytest.mark.parametrize(
    ("reviews", "review_status", "expected"),
    [
        ([], "UN_REVIEWED", False),             # 无评审 + 未评审 → False
        ([], "PASS", True),                     # 无评审 + 已通过 → True（并集）
        ([], "UN_PASS", True),                  # 无评审 + 未通过 → True（并集）
        ([{"id": "r1"}], "UN_REVIEWED", True),  # 有评审记录 → True
    ],
)
def test_reviewed_union_predicate(reviews, review_status, expected):
    assert union_reviewed(reviews, review_status) is expected


def test_reviewed_union_predicate_matches_report_scripts():
    """两个 v2 报告脚本的内联表达式必须与规范谓词逐字一致（防漂移）。"""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    summary = (root / "skills" / "scripts" / "v2" / "ms_review_summary.py").read_text(encoding="utf-8")
    report = (root / "skills" / "scripts" / "v2" / "ms_case_report.py").read_text(encoding="utf-8")

    # ms_review_summary.py:130 的内联谓词
    assert "is_reviewed = (len(reviews) > 0) or (review_status in ('PASS', 'UN_PASS'))" in summary
    # ms_case_report.py:151 的内联谓词
    assert re.search(r"'reviewed': \(len\(reviews\) > 0\) or \(detail\.get\('reviewStatus'\) in \('PASS', 'UN_PASS'\)\)", report)
