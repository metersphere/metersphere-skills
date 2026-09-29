#!/usr/bin/env python3
"""ms_chat_log.py — 本地 Markdown 对话记录格式化器（纯本地，无网络）。

将对话 JSON（{"title": str, "exchanges": [{"user": str, "assistant": str}]}）
格式化为 Markdown 对话记录文件，供后续通过 v2/ms.sh 的 attachment 资源上传为
用例附件。本脚本不做任何网络请求、不做签名——传输由 ms.sh 的 curl 完成。

用法: ms_chat_log.py <conversation-json-file> [--creator <label>] [--title <title>] [--out <file>]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUT = 'conversation-log.md'
DEFAULT_CREATOR = 'agent'
DEFAULT_TITLE = '对话记录'


def die(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(2)


def load_conversation(path: Path) -> dict:
    try:
        raw = path.read_text(encoding='utf-8')
    except OSError as e:
        die(f'无法读取对话文件 {path}: {e}')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f'对话文件不是合法 JSON: {e}')
    if not isinstance(data, dict):
        die('对话 JSON 顶层必须是对象 {"title": str, "exchanges": [...]}')
    exchanges = data.get('exchanges')
    if not isinstance(exchanges, list):
        die('对话 JSON 缺少 exchanges 数组（应为 [{"user": str, "assistant": str}, ...]）')
    for i, item in enumerate(exchanges):
        if not isinstance(item, dict):
            die(f'exchanges[{i}] 必须是对象 {{"user": str, "assistant": str}}')
        if not isinstance(item.get('user'), str) or not isinstance(item.get('assistant'), str):
            die(f'exchanges[{i}] 的 user/assistant 必须是字符串')
    return data


def render(data: dict, creator: str, title: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    exchanges = data.get('exchanges') or []
    lines = []
    lines.append(f'# {title}')
    lines.append('')
    lines.append(f'- 创建者 (creator): {creator}')
    lines.append(f'- 创建时间 (createTime): {now}')
    lines.append(f'- 对话轮次 (exchangeCount): {len(exchanges)}')
    lines.append('')
    for item in exchanges:
        lines.append(f'## [USER] {now}')
        lines.append('')
        lines.append(item.get('user', ''))
        lines.append('')
        lines.append(f'## [ASSISTANT] {now}')
        lines.append('')
        lines.append(item.get('assistant', ''))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(
        prog='ms_chat_log.py',
        description='将对话 JSON 格式化为 Markdown 对话记录（纯本地，无网络）。',
    )
    parser.add_argument('conversation_json_file', help='对话 JSON 文件路径')
    parser.add_argument('--creator', default=DEFAULT_CREATOR, help=f'创建者标签（默认 {DEFAULT_CREATOR}）')
    parser.add_argument('--title', default=None, help='覆盖标题（默认取 JSON 的 title）')
    parser.add_argument('--out', default=DEFAULT_OUT, help=f'输出文件（默认 {DEFAULT_OUT}）')
    args = parser.parse_args()

    src = Path(args.conversation_json_file)
    if not src.is_file():
        die(f'对话文件不存在: {src}')

    data = load_conversation(src)
    title = args.title or data.get('title') or DEFAULT_TITLE
    if not isinstance(title, str):
        die('对话 JSON 的 title 必须是字符串')

    out = Path(args.out)
    try:
        out.write_text(render(data, args.creator, title), encoding='utf-8')
    except OSError as e:
        die(f'无法写入输出文件 {out}: {e}')
    print(f'已写入 {out}')


if __name__ == '__main__':
    main()