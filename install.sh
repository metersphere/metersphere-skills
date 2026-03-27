#!/bin/bash
set -e

TARGET_DIR="$HOME/.openclaw/workspace/skills/metersphere"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)/skills"

mkdir -p "$(dirname "$TARGET_DIR")"
rm -rf "$TARGET_DIR"
cp -R "$SRC_DIR" "$TARGET_DIR"

echo "已安装到: $TARGET_DIR"
echo "下一步: 复制 .env.example 到 $TARGET_DIR/.env 并填写 MeterSphere 地址、认证信息和实际接口路径。"
