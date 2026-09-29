#!/usr/bin/env python3
"""v2 导入辅助函数（stdlib-only）：spec 下载/校验、导入响应解析、已有用例名查询。

供 ms.sh 的 api import-create / import-generate 与 ai 增强工作流复用。
本模块不自行签名（签名由 ms.sh generate_signature 完成，调用方传入 headers）。
"""
import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_TIMEOUT = 30
SPEC_SUFFIXES = (".json", ".yaml", ".yml")
MAX_PAGES = 100


def resolve_spec_to_file(spec_source, timeout=DEFAULT_TIMEOUT):
    """把 spec 来源解析为 (本地文件路径, 原始文件名)。

    - http(s):// 或 file:// URL: 下载/读取字节并写入临时文件（路径与原始文件名一起返回）。
    - 本地路径: 校验存在且后缀为 .json/.yaml/.yml，原样返回（不复制）。
    出错抛 ValueError（调用方负责清理返回的临时文件）。
    """
    source = str(spec_source).strip()
    if not source:
        raise ValueError("spec_source 为空")
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https", "file"):
        original_name = os.path.basename(parsed.path) or "spec.json"
        try:
            with urllib.request.urlopen(source, timeout=timeout) as resp:
                data_bytes = resp.read()
        except urllib.error.HTTPError as e:
            raise ValueError(f"下载 spec 失败: HTTP {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise ValueError(f"下载 spec 失败: {e.reason}")
        suffix = os.path.splitext(original_name)[1].lower() or ".json"
        fd, tmp_path = tempfile.mkstemp(prefix="ms-spec-", suffix=suffix)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data_bytes)
        return tmp_path, original_name
    # 本地路径
    p = Path(source).expanduser()
    if not p.exists():
        raise ValueError(f"spec 文件不存在: {source}")
    if p.suffix.lower() not in SPEC_SUFFIXES:
        raise ValueError(f"spec 文件后缀不受支持: {p.suffix or '(无)'}（支持 {', '.join(SPEC_SUFFIXES)}）")
    return str(p.resolve()), p.name


def parse_import_response(response_json):
    """解析 definition/import 响应 → list[{id, name}]。

    接受 dict 或 JSON 字符串。取 data 下的 data 数组（兼容 data 本身为数组）。
    无效 JSON / 结构无法识别 / 条目缺 id 或 name → 抛 ValueError。
    """
    if isinstance(response_json, str):
        try:
            doc = json.loads(response_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"响应不是合法 JSON: {e}")
    else:
        doc = response_json
    if not isinstance(doc, dict):
        raise ValueError("响应结构错误: 顶层不是对象")
    data = doc.get("data")
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("data"), list):
        items = data["data"]
    else:
        raise ValueError("响应结构错误: 找不到导入定义数组（data.data 或 data 应为数组）")
    result = []
    for it in items:
        if not isinstance(it, dict):
            raise ValueError("响应结构错误: 导入定义条目不是对象")
        id_ = it.get("id")
        name_ = it.get("name")
        if id_ is None or name_ is None:
            raise ValueError("响应结构错误: 导入定义条目缺 id 或 name")
        result.append({"id": str(id_), "name": str(name_)})
    return result


def existing_case_names(project_id, api_definition_id, base_url, headers=None,
                        page_size=500, timeout=DEFAULT_TIMEOUT, max_pages=MAX_PAGES):
    """查询某接口定义下已有的用例名集合（去重预检）。

    POST {base}/api/api/testcase/list/{goPage}/{pageSize}
    body {"projectId": X, "apiDefinitionId": Y}
    headers: 已签名请求头 dict（accessKey/signature 等），测试可省略。
    翻页: data 为 list → 单页判断(length < page_size)；data 为 dict →
    按 pageCount / listObject 翻页（与 v2 definition-list 响应形状一致）。
    返回 set[str]（用例名，去重）。查询失败抛 ValueError。
    """
    names = set()
    go_page = 1
    while True:
        url = f"{str(base_url).rstrip('/')}/api/api/testcase/list/{go_page}/{page_size}"
        body = json.dumps(
            {"projectId": str(project_id), "apiDefinitionId": str(api_definition_id)},
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(str(k), str(v))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ValueError(f"查询已有用例失败: HTTP {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise ValueError(f"查询已有用例失败: {e.reason}")
        data = (doc or {}).get("data")
        batch = []
        page_count = None
        if isinstance(data, list):
            batch = data
            page_count = None  # 单页模式
        elif isinstance(data, dict):
            batch = data.get("listObject") or []
            page_count = data.get("pageCount")
        else:
            raise ValueError("查询已有用例失败: 响应 data 结构无法识别")
        for it in batch:
            nm = it.get("name") if isinstance(it, dict) else None
            if nm:
                names.add(str(nm))
        if page_count is None:
            if len(batch) < page_size:
                break
        elif go_page >= int(page_count or 1):
            break
        go_page += 1
        if go_page > max_pages:
            raise ValueError(f"查询已有用例翻页超过 {max_pages} 页，疑似死循环")
    return names


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("用法: python3 ms_import_helper.py <subcommand> <arg>\n"
              "  resolve <spec_source>   -> 打印 <path>|<original_name>\n"
              "  parse <response.json>   -> 打印 [{id,name},...]",
              file=sys.stderr)
        sys.exit(1)
    sub, arg = sys.argv[1], sys.argv[2]
    if sub == "resolve":
        path, name = resolve_spec_to_file(arg)
        # F6: resolve may return a downloaded TEMP file (local paths are returned as-is);
        # this helper's job is only to report the path, so delete the temp copy here.
        if path != str(Path(arg).expanduser().resolve()):
            try:
                os.remove(path)
            except OSError:
                pass
        print(f"{path}|{name}")
    elif sub == "parse":
        with open(arg, encoding="utf-8") as fh:
            print(json.dumps(parse_import_response(fh.read()), ensure_ascii=False))
    else:
        print(f"未知子命令: {sub}", file=sys.stderr)
        sys.exit(1)
