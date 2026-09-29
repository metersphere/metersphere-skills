# -*- coding: utf-8 -*-
"""pytest 共享配置：把 skills/scripts/v2 加入 sys.path（T5 item 2）。

conftest.py 位于 tests/v2/，parents[2] 解析为仓库根，
因此插入的是 <repo>/skills/scripts/v2 —— 与运行目录无关。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "scripts" / "v2"))
