#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# v2 脚本位于 scripts/v2/，比主包深一层：技能根目录（.env 所在）为上两级。
SKILL_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
ENV_FILE="${SKILL_DIR}/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

METERSPHERE_BASE_URL="${METERSPHERE_BASE_URL:-}"
METERSPHERE_ACCESS_KEY="${METERSPHERE_ACCESS_KEY:-}"
METERSPHERE_SECRET_KEY="${METERSPHERE_SECRET_KEY:-}"
METERSPHERE_PROJECT_ID="${METERSPHERE_PROJECT_ID:-}"
METERSPHERE_ORGANIZATION_ID="${METERSPHERE_ORGANIZATION_ID:-100001}"
METERSPHERE_WORKSPACE_ID="${METERSPHERE_WORKSPACE_ID:-}"
METERSPHERE_VERSION="${METERSPHERE_VERSION:-}"
METERSPHERE_HEADERS_JSON="${METERSPHERE_HEADERS_JSON:-}"
METERSPHERE_TIMEOUT="${METERSPHERE_TIMEOUT:-60}"  # F5: 所有 curl 的统一超时（秒），可被环境变量覆盖
METERSPHERE_PROTOCOLS_JSON="${METERSPHERE_PROTOCOLS_JSON:-[\"HTTP\"]}"

[[ -n "${METERSPHERE_ORGANIZATION_LIST_PATH:-}" ]] || METERSPHERE_ORGANIZATION_LIST_PATH='/workspace/list/userworkspace'
[[ -n "${METERSPHERE_PROJECT_LIST_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_PATH='/project/list/related'
[[ -n "${METERSPHERE_PROJECT_LIST_SYSTEM_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_SYSTEM_PATH='/project/list/related'
[[ -n "${METERSPHERE_PROJECT_LIST_BY_ORG_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_BY_ORG_PATH='/project/list/related'
[[ -n "${METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH='/case/node/list/{projectId}'
[[ -n "${METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH='/field/template/case/option/{projectId}'
[[ -n "${METERSPHERE_API_MODULE_TREE_PATH:-}" ]] || METERSPHERE_API_MODULE_TREE_PATH='/api/module/list/{projectId}/{protocol}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_LIST_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_LIST_PATH='/test/case/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_GET_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_GET_PATH='/test/case/get/{id}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH='/test/case/add'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_DELETE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_DELETE_PATH='/test/case/delete/{id}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH='/test/review/case/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_CASE_REVIEW_LIST_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_LIST_PATH='/test/case/review/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_CASE_REVIEW_GET_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_GET_PATH='/test/case/review/get/{id}'
[[ -n "${METERSPHERE_CASE_REVIEW_CREATE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_CREATE_PATH='/test/case/review/save'
[[ -n "${METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH='/test/review/case/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH='/case/review/node/list/{projectId}'
[[ -n "${METERSPHERE_CASE_REVIEW_USER_OPTION_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_USER_OPTION_PATH='/test/case/review/reviewer'
[[ -n "${METERSPHERE_API_DEFINITION_LIST_PATH:-}" ]] || METERSPHERE_API_DEFINITION_LIST_PATH='/api/definition/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_API_DEFINITION_GET_PATH:-}" ]] || METERSPHERE_API_DEFINITION_GET_PATH='/api/definition/get/{id}'
[[ -n "${METERSPHERE_API_DEFINITION_CREATE_PATH:-}" ]] || METERSPHERE_API_DEFINITION_CREATE_PATH='/api/definition/create'
[[ -n "${METERSPHERE_API_DEFINITION_IMPORT_PATH:-}" ]] || METERSPHERE_API_DEFINITION_IMPORT_PATH='/api/definition/import'
[[ -n "${METERSPHERE_API_CASE_LIST_PATH:-}" ]] || METERSPHERE_API_CASE_LIST_PATH='/api/testcase/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_API_CASE_GET_PATH:-}" ]] || METERSPHERE_API_CASE_GET_PATH='/api/testcase/get-details/{id}'
[[ -n "${METERSPHERE_API_CASE_CREATE_PATH:-}" ]] || METERSPHERE_API_CASE_CREATE_PATH='/api/testcase/create'
[[ -n "${METERSPHERE_COMMENT_LIST_PATH:-}" ]] || METERSPHERE_COMMENT_LIST_PATH='/test/case/comment/list'
[[ -n "${METERSPHERE_COMMENT_GET_PATH:-}" ]] || METERSPHERE_COMMENT_GET_PATH=''
[[ -n "${METERSPHERE_COMMENT_CREATE_PATH:-}" ]] || METERSPHERE_COMMENT_CREATE_PATH='/test/case/comment/save'
[[ -n "${METERSPHERE_COMMENT_EDIT_PATH:-}" ]] || METERSPHERE_COMMENT_EDIT_PATH='/test/case/comment/edit'
[[ -n "${METERSPHERE_COMMENT_DELETE_PATH:-}" ]] || METERSPHERE_COMMENT_DELETE_PATH='/test/case/comment/delete'
[[ -n "${METERSPHERE_ATTACHMENT_UPLOAD_PATH:-}" ]] || METERSPHERE_ATTACHMENT_UPLOAD_PATH='/attachment/testcase/upload'
[[ -n "${METERSPHERE_ATTACHMENT_LIST_PATH:-}" ]] || METERSPHERE_ATTACHMENT_LIST_PATH='/attachment/metadata/list'
[[ -n "${METERSPHERE_ATTACHMENT_DOWNLOAD_PATH:-}" ]] || METERSPHERE_ATTACHMENT_DOWNLOAD_PATH='/attachment/download'
[[ -n "${METERSPHERE_ATTACHMENT_DELETE_PATH:-}" ]] || METERSPHERE_ATTACHMENT_DELETE_PATH='/attachment/delete/testcase'

die() { echo "错误: $*" >&2; exit 1; }

require_project_id() {
  # 写入安全：拒绝在未显式设置 METERSPHERE_PROJECT_ID 时写入（防止误写硬编码项目）。
  [[ -n "$METERSPHERE_PROJECT_ID" ]] || die "未设置 METERSPHERE_PROJECT_ID，拒绝写入（防止误写硬编码项目）"
}

detect_version() {
  # 返回 v2 或 v3。METERSPHERE_VERSION 环境变量可强制指定。
  if [[ -n "$METERSPHERE_VERSION" ]]; then
    echo "$METERSPHERE_VERSION"
    return 0
  fi
  need_base_url
  # v3 有 /system/version/current；v2 只有 /system/version
  local v3_status
  v3_status="$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$METERSPHERE_TIMEOUT" "${METERSPHERE_BASE_URL%/}/system/version/current" 2>/dev/null || true)"
  if [[ "$v3_status" == "200" ]]; then
    echo "v3"
  else
    echo "v2"
  fi
}

need_base_url() {
  [[ -n "$METERSPHERE_BASE_URL" ]] || die "未设置 METERSPHERE_BASE_URL"
}

need_keys() {
  [[ -n "$METERSPHERE_ACCESS_KEY" ]] || die "未设置 METERSPHERE_ACCESS_KEY"
  [[ -n "$METERSPHERE_SECRET_KEY" ]] || die "未设置 METERSPHERE_SECRET_KEY"
}

generate_signature() {
  python3 - <<'PY' "$METERSPHERE_ACCESS_KEY" "$METERSPHERE_SECRET_KEY"
import sys, uuid, time, base64
from subprocess import run, PIPE
access_key, secret_key = sys.argv[1], sys.argv[2]
plain = f"{access_key}|{uuid.uuid4()}|{int(time.time()*1000)}"
key_hex = secret_key.encode('utf-8').hex()
iv_hex = access_key.encode('utf-8').hex()
proc = run([
    'openssl', 'enc', '-aes-128-cbc', '-K', key_hex, '-iv', iv_hex,
    '-base64', '-A', '-nosalt'
], input=plain.encode('utf-8'), stdout=PIPE, stderr=PIPE, check=True)
print(proc.stdout.decode('utf-8').strip())
PY
}

build_header_args() {
  local tmp_file="$1"
  local signature
  signature="$(generate_signature)"
  {
    printf '%s\n' '-H' 'Content-Type: application/json'
    printf '%s\n' '-H' "accessKey: $METERSPHERE_ACCESS_KEY"
    printf '%s\n' '-H' "signature: $signature"
    if [[ -n "$METERSPHERE_HEADERS_JSON" ]]; then
      python3 - <<'PY' "$METERSPHERE_HEADERS_JSON"
import json,sys
headers=json.loads(sys.argv[1])
for k,v in headers.items():
    print('-H')
    print(f'{k}: {v}')
PY
    fi
  } > "$tmp_file"
}

default_list_payload() {
  local resource="${1:-}"
  local keyword="${2:-}"
  python3 - <<'PY' "$resource" "$keyword" "$METERSPHERE_PROJECT_ID" "$METERSPHERE_WORKSPACE_ID" "$METERSPHERE_PROTOCOLS_JSON"
import json,sys
resource, keyword, project_id, workspace_id, protocols_json = sys.argv[1:6]
payload = {}
if keyword:
    payload["keyword"] = keyword
if project_id:
    payload["projectId"] = project_id
if workspace_id:
    payload["workspaceId"] = workspace_id
if resource in ("api", "api-case"):
    try:
        payload["protocols"] = json.loads(protocols_json)
    except Exception:
        payload["protocols"] = ["HTTP"]
print(json.dumps(payload, ensure_ascii=False))
PY
}

normalize_json_with_defaults() {
  local resource="$1"
  local body="$2"
  python3 - <<'PY' "$resource" "$body" "$METERSPHERE_PROJECT_ID" "$METERSPHERE_WORKSPACE_ID" "$METERSPHERE_PROTOCOLS_JSON"
import json,sys
resource, body, project_id, workspace_id, protocols_json = sys.argv[1:6]
data = json.loads(body)
if isinstance(data, dict):
    if project_id and not data.get("projectId"):
        data["projectId"] = project_id
    if workspace_id and not data.get("workspaceId"):
        data["workspaceId"] = workspace_id
    if resource in ("api", "api-case") and not data.get("protocols"):
        try:
            data["protocols"] = json.loads(protocols_json)
        except Exception:
            pass
print(json.dumps(data, ensure_ascii=False))
PY
}

service_prefix() {
  # v2 网关 discovery locator：/{serviceId}/** 剥掉首段 serviceId 后转发到对应微服务。
  # track：功能模块/功能用例/评审系；project：功能模板；其余（含 raw）走 api。
  case "$1" in
    functional-module|functional-case|functional-case-review|case-review|case-review-detail|case-review-module|case-review-user|comment|attachment)
      echo "track"
      ;;
    functional-template)
      echo "project"
      ;;
    *)
      echo "api"
      ;;
  esac
}

request() {
  local method="$1" path="$2" body="${3:-}" prefix="${4:-api}"
  need_base_url
  need_keys
  local url="${METERSPHERE_BASE_URL%/}/${prefix}${path}"
  local header_file
  header_file="$(mktemp)"
  # F6: trap-based cleanup — header_file is removed on EVERY exit path (curl failure included)
  trap 'rm -f "$header_file"' EXIT
  build_header_args "$header_file"
  local -a header_args=()
  while IFS= read -r line; do
    header_args+=("$line")
  done < "$header_file"
  if [[ -n "$body" ]]; then
    curl -sS -X "$method" "$url" "${header_args[@]}" -d "$body" --max-time "$METERSPHERE_TIMEOUT"  # F5
  else
    curl -sS -X "$method" "$url" "${header_args[@]}" --max-time "$METERSPHERE_TIMEOUT"  # F5
  fi
  rm -f "$header_file"
  trap - EXIT  # F6: restore the caller's EXIT trap after successful cleanup
}

path_fill() {
  local template="$1" value="$2"
  template="${template/\{id\}/$value}"
  template="${template/\{organizationId\}/$value}"
  template="${template/\{projectId\}/$value}"
  template="${template/\{workspaceId\}/$value}"
  template="${template/\{goPage\}/1}"
  template="${template/\{pageSize\}/20}"
  echo "$template"
}

resource_paths() {
  case "$1" in
    organization|workspace)
      echo "$METERSPHERE_ORGANIZATION_LIST_PATH||"
      ;;
    project)
      echo "$METERSPHERE_PROJECT_LIST_PATH||"
      ;;
    functional-module)
      echo "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH||"
      ;;
    functional-template)
      echo "$METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH||"
      ;;
    api-module)
      echo "$METERSPHERE_API_MODULE_TREE_PATH||"
      ;;
    functional-case)
      echo "$METERSPHERE_FUNCTIONAL_CASE_LIST_PATH|$METERSPHERE_FUNCTIONAL_CASE_GET_PATH|$METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH"
      ;;
    functional-case-review)
      echo "$METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH||"
      ;;
    case-review)
      echo "$METERSPHERE_CASE_REVIEW_LIST_PATH|$METERSPHERE_CASE_REVIEW_GET_PATH|$METERSPHERE_CASE_REVIEW_CREATE_PATH"
      ;;
    case-review-detail)
      echo "$METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH||"
      ;;
    case-review-module)
      echo "$METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH||"
      ;;
    case-review-user)
      echo "$METERSPHERE_CASE_REVIEW_USER_OPTION_PATH||"
      ;;
    api)
      echo "$METERSPHERE_API_DEFINITION_LIST_PATH|$METERSPHERE_API_DEFINITION_GET_PATH|$METERSPHERE_API_DEFINITION_CREATE_PATH|$METERSPHERE_API_DEFINITION_IMPORT_PATH"
      ;;
    api-case)
      echo "$METERSPHERE_API_CASE_LIST_PATH|$METERSPHERE_API_CASE_GET_PATH|$METERSPHERE_API_CASE_CREATE_PATH"
      ;;
    comment)
      echo "$METERSPHERE_COMMENT_LIST_PATH|$METERSPHERE_COMMENT_GET_PATH|$METERSPHERE_COMMENT_CREATE_PATH"
      ;;
    attachment)
      echo "$METERSPHERE_ATTACHMENT_LIST_PATH|$METERSPHERE_ATTACHMENT_DOWNLOAD_PATH|$METERSPHERE_ATTACHMENT_UPLOAD_PATH"
      ;;
    *)
      die "不支持的资源: $1"
      ;;
  esac
}

usage() {
  cat <<'EOF'
ms — MeterSphere CLI (v2 模式)

本脚本面向 MeterSphere v2 分支（可用 METERSPHERE_VERSION=v2 显式指定）。
v2 使用 workspace 而非 organization；分页为路径参数 {goPage}/{pageSize}。

用法:
  ms <resource> <action> [args...]
  ms raw <METHOD> <PATH> [JSON]
  ms reviewed-summary <projectId> [keyword]
  ms case-report <projectId> <caseId>
  ms case-report-md <projectId> <caseId>

资源:
  organization (v2 中为 workspace 列表)
  project
  functional-module
  functional-template
  api-module
  functional-case
  functional-case-review
  case-review
  case-review-detail
  case-review-module
  case-review-user
  api
  api-case
  comment
  attachment

动作:
  list [关键词|JSON]
  get <id>
  create <JSON>
  save <caseId> <JSON>  (comment: 用例评论写入)
  delete <caseId> [评论ID|附件ID]  (comment/attachment/functional-case: 删除)
  edit <caseId> <评论ID> <JSON>  (comment: 用例评论编辑)
  generate <projectId> <moduleId> <templateId> <需求文件>  (functional-case: 本地生成草稿)
  batch-create <JSON文件>  (functional-case: 批量写入)
  generate-create <projectId> [<definitionId>...]  (api-case: 定义 → 接口用例批量生成写入)
  upload <caseId> <文件>  (attachment: 附件上传)
  download <caseId> <isLocal> <outfile>  (attachment: 附件下载)
  import-generate <projectId> <spec> [moduleId] (api: 导入 spec 生成定义+用例计划，不写入用例)
  import-create <projectId> <spec> [moduleId] (api: 导入 spec → 定义 → 用例，幂等去重)
  help

示例:
  ms organization list
  ms project list
  ms project list all
  ms project list <workspaceId>
  ms functional-module list <projectId>
  ms functional-template list <projectId>
  ms api-module list <projectId>
  ms functional-case list "登录"
  ms functional-case get <caseId>
  ms functional-case create '{"name":"登录用例","nodeId":"<moduleId>","projectId":"<projectId>"}'
  ms functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
  ms functional-case batch-create <json-array-file>
  ms functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
  ms functional-case delete <caseId>
  ms case-review list '{"projectId":"<your-project-id>"}'
  ms case-review get <review-id>
  ms case-review-user list <review-id>
  ms api list '{"keyword":"用户"}'
  ms api-case create '{"name":"获取用户详情-200","apiDefinitionId":"api-1"}'
  ms api-case generate-create <projectId>
  ms api-case generate-create <projectId> <definitionId> [<definitionId>...]
  ms api import-create <projectId> /path/to/openapi.json
  ms api import-generate <projectId> https://example.com/api-docs
  ms comment save <caseId> <description> [type] [belongId]
  ms comment list <caseId> [type [belongId]]
  ms comment delete <commentId>
  ms comment edit <commentId> <caseId> <description> [type] [belongId]
  ms attachment upload <caseId> <file>
  ms attachment list <caseId>
  ms attachment download <attachmentId> <isLocal> <outfile>
  ms attachment delete <attachmentId>
  ms raw GET /system/version
EOF
}

cmd="${1:-}"
[[ -n "$cmd" ]] || { usage; exit 1; }
shift || true

if [[ "$cmd" == "help" || "$cmd" == "-h" || "$cmd" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$cmd" == "raw" ]]; then
  method="${1:-}"; shift || die "raw 需要 METHOD"
  path="${1:-}"; shift || die "raw 需要 PATH"
  body="${1:-}"
  request "$method" "$path" "$body"
  exit 0
fi

if [[ "$cmd" == "reviewed-summary" ]]; then
  project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
  keyword="${2:-}"
  [[ -n "$project_id" ]] || die "reviewed-summary 需要 projectId"
  python3 "$SCRIPT_DIR/ms_review_summary.py" "$project_id" "$keyword"
  exit 0
fi

if [[ "$cmd" == "case-report" ]]; then
  project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
  case_id="${2:-}"
  [[ -n "$project_id" ]] || die "case-report 需要 projectId"
  [[ -n "$case_id" ]] || die "case-report 需要 caseId"
  python3 "$SCRIPT_DIR/ms_case_report.py" "$project_id" "$case_id"
  exit 0
fi

if [[ "$cmd" == "case-report-md" ]]; then
  project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
  case_id="${2:-}"
  [[ -n "$project_id" ]] || die "case-report-md 需要 projectId"
  [[ -n "$case_id" ]] || die "case-report-md 需要 caseId"
  python3 "$SCRIPT_DIR/ms_case_report_md.py" "$project_id" "$case_id"
  exit 0
fi

resource="$cmd"
action="${1:-}"
[[ -n "$action" ]] || die "缺少 action"
shift || true
paths_out="$(resource_paths "$resource")" || exit 1  # F1: die in subshell only exits the subshell; parent must exit non-zero too
IFS='|' read -r list_path get_path create_path <<< "$paths_out"
service_prefix="$(service_prefix "$resource")"

# 批量创建功能用例：读取 JSON 数组文件，逐元素 POST /track/test/case/add（multipart）。
# nodePath 占位符（"/"+nodeId，来自 ms_generate.py）会按模块树解析为真实路径；
# 解析失败则透传，由服务端校验。
batch_create_functional_cases() {
  local json_file="$1"
  local project_id="$METERSPHERE_PROJECT_ID"
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  python3 - "$json_file" "$tmp_dir/elements.jsonl" <<'PY'
import json, sys
path, out = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path, encoding='utf-8'))
except Exception as e:
    print(f'错误: 无法解析 JSON 数组文件: {e}', file=sys.stderr)
    sys.exit(1)
if not isinstance(data, list):
    print('错误: batch-create 需要 JSON 数组文件', file=sys.stderr)
    sys.exit(1)
with open(out, 'w', encoding='utf-8') as f:
    for i, el in enumerate(data):
        if not isinstance(el, dict):
            print(f'错误: 第 {i+1} 个元素不是 JSON 对象', file=sys.stderr)
            sys.exit(1)
        f.write(json.dumps(el, ensure_ascii=False) + '\n')
PY
  local need_resolve
  need_resolve="$(python3 - "$tmp_dir/elements.jsonl" <<'PY'
import json, sys
for line in open(sys.argv[1], encoding='utf-8'):
    el = json.loads(line)
    if (el.get('nodePath') or '') == '/' + (el.get('nodeId') or ''):
        print('1')
        sys.exit(0)
print('0')
PY
)"
  local module_tree=""
  if [[ "$need_resolve" == "1" ]]; then
    module_tree="$(request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH" "$project_id")" "" "track")"
  fi
  local count=0 created=0
  while IFS= read -r element; do
    count=$((count + 1))
    if [[ "$need_resolve" == "1" ]]; then
      element="$(python3 - "$element" "$module_tree" <<'PY'
import json, sys
el = json.loads(sys.argv[1])
node_id = el.get('nodeId') or ''
if (el.get('nodePath') or '') == '/' + node_id and sys.argv[2]:
    try:
        resp = json.loads(sys.argv[2])
        tree = resp.get('data') if isinstance(resp, dict) else resp
        if not isinstance(tree, list):
            tree = [tree]
        nodes = {}
        def walk(items):
            for n in items or []:
                if not isinstance(n, dict):
                    continue
                nodes[n.get('id')] = n
                walk(n.get('children'))
        walk(tree)
        parts = []
        cur = nodes.get(node_id)
        seen = set()
        while cur and cur.get('id') not in seen:
            seen.add(cur.get('id'))
            name = cur.get('name')
            if name:
                parts.insert(0, name)
            pid = cur.get('parentId')
            cur = nodes.get(pid) if pid else None
        if parts:
            el['nodePath'] = '/' + '/'.join(parts)
    except Exception:
        pass
print(json.dumps(el, ensure_ascii=False))
PY
)"
    fi
    local tmp_json
    tmp_json="$(mktemp)"
    printf '%s' "$element" > "$tmp_json"
    need_base_url
    need_keys
    local signature
    signature="$(generate_signature)"
    local resp
    resp="$(curl -sS -X POST \
    --max-time "$METERSPHERE_TIMEOUT" \  # F5
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -F "request=@${tmp_json};type=application/json" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH}")"
    rm -f "$tmp_json"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "batch-create 第 $count 个用例创建失败: $resp"
    local case_id
    case_id="$(printf '%s' "$resp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
data=d.get("data")
if isinstance(data, str) and data:
    print(data)
elif isinstance(data, dict) and data.get("id"):
    print(data["id"])
' 2>/dev/null || true)"
    if [[ -n "$case_id" ]]; then
      echo "已创建用例: $case_id"
      created=$((created + 1))
    fi
  done < "$tmp_dir/elements.jsonl"
  echo "batch-create 完成: 共 $count 个元素，成功创建 $created 个用例"
  rm -rf "$tmp_dir"
  trap - EXIT
}

# 批量生成并创建接口用例：读取接口定义详情 → ms_generate_case.py 生成变体 →
# 逐条 multipart POST /api/testcase/create。
# 与 batch_create_functional_cases 不同：单条失败继续处理，仅当 0 条创建成功时非零退出。
# 关键（T1 实测 wire proof）：create 载荷的 request 字段必须是嵌套对象——
# 服务端对 request-as-JSON-string 返回 HTTP 400（@RequestPart("request") 绑定拒绝）。
# 因此生成器输出的紧凑 JSON 字符串 request 在此 json.loads 回对象后再写入载荷文件。
generate_create_api_cases() {
  local project_id="$1"
  shift || true
  local -a def_ids=("$@")

  need_base_url
  need_keys

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT

  # 1) 无显式定义 id → 分页列出项目全部 HTTP 定义
  #    实测响应（POST /api/api/definition/list/{goPage}/{pageSize}）：
  #    data.listObject（数组）/ data.itemCount（总数）/ data.pageCount（总页数）。
  #    分页检测：有 pageCount 时按 page >= pageCount 停止；否则 listObject 长度 < pageSize 即末页。
  if [[ ${#def_ids[@]} -eq 0 ]]; then
    local page=1 page_size=500
    local list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
    list_path="${list_path/\{pageSize\}/$page_size}"
    local body
    body="$(python3 - "$project_id" "$METERSPHERE_PROTOCOLS_JSON" <<'PY'
import json, sys
project_id, protocols_json = sys.argv[1], sys.argv[2]
try:
    protocols = json.loads(protocols_json)
except Exception:
    protocols = ["HTTP"]
print(json.dumps({"projectId": project_id, "protocols": protocols}, ensure_ascii=False))
PY
)"
    while :; do
      local resp
      resp="$(request POST "$list_path" "$body" "api")"
      local ids
      ids="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
data = d.get("data") or {}
items = data.get("listObject") or []
for it in items:
    if isinstance(it, dict) and it.get("id"):
        print(it["id"])
')" || die "定义列表解析失败: $resp"
      while IFS= read -r id; do
        [[ -n "$id" ]] && def_ids+=("$id")
      done <<< "$ids"
      local page_count item_count got
      page_count="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
pc = data.get("pageCount")
print(pc if isinstance(pc, int) else "")
')"
      item_count="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
ic = data.get("itemCount")
print(ic if isinstance(ic, int) else "")
')"
      got="$(printf '%s' "$ids" | grep -c . || true)"
      if [[ -n "$page_count" ]] && (( page >= page_count )); then
        break
      fi
      if [[ -z "$page_count" ]] && (( got < page_size )); then
        break
      fi
      page=$((page + 1))
      list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
      list_path="${list_path/\{pageSize\}/$page_size}"
    done
    echo "共发现 ${#def_ids[@]} 个接口定义（项目 $project_id）"
  fi

  local total=0 created=0
  local def_id
  for def_id in "${def_ids[@]}"; do
    local detail_file="$tmp_dir/detail.json"
    local resp
    resp="$(request GET "$(path_fill "$METERSPHERE_API_DEFINITION_GET_PATH" "$def_id")" "" "api")"
    printf '%s' "$resp" > "$detail_file"
    local variants_file="$tmp_dir/variants.json"
    if ! python3 "$SCRIPT_DIR/ms_generate_case.py" "$detail_file" > "$variants_file" 2> "$tmp_dir/gen.err"; then
      echo "定义 $def_id 生成用例失败: $(cat "$tmp_dir/gen.err")"
      continue
    fi
    # 变体 request（紧凑 JSON 字符串）→ 嵌套对象，逐行输出完整 create 载荷
    # 服务端实测（error.log）：不传 id 报 Column 'id' cannot be null——每条用例必须显式携带 uuid4 id。
    local payloads_file="$tmp_dir/payloads.jsonl"
    if ! python3 - "$variants_file" "$payloads_file" <<'PY'
import json, sys, uuid
variants = json.load(open(sys.argv[1], encoding='utf-8'))
if not isinstance(variants, list):
    print('错误: 生成器输出不是 JSON 数组', file=sys.stderr)
    sys.exit(1)
with open(sys.argv[2], 'w', encoding='utf-8') as f:
    for v in variants:
        if not isinstance(v, dict):
            print('错误: 变体不是 JSON 对象', file=sys.stderr)
            sys.exit(1)
        req = v.get('request')
        if isinstance(req, str):
            try:
                v['request'] = json.loads(req)
            except ValueError as exc:
                print(f'错误: 变体 request 不是合法 JSON: {exc}', file=sys.stderr)
                sys.exit(1)
        if not v.get('id'):
            v['id'] = str(uuid.uuid4())
        if not v.get('priority'):
            v['priority'] = 'P1'
        f.write(json.dumps(v, ensure_ascii=False) + '\n')
PY
    then
      echo "定义 $def_id 载荷转换失败: $(cat "$tmp_dir/gen.err" 2>/dev/null || true)"
      continue
    fi
    # 逐条 multipart 创建：复用 generate_signature，绝不手写签名
    local line
    while IFS= read -r line; do
      total=$((total + 1))
      local tmp_json="$tmp_dir/payload.json"
      printf '%s' "$line" > "$tmp_json"
      local signature
      signature="$(generate_signature)"
      local cresp
      cresp="$(curl -sS -X POST \
      --max-time "$METERSPHERE_TIMEOUT" \  # F5
        -H "accessKey: $METERSPHERE_ACCESS_KEY" \
        -H "signature: $signature" \
        -F "request=@${tmp_json};type=application/json" \
        "${METERSPHERE_BASE_URL%/}/api${METERSPHERE_API_CASE_CREATE_PATH}")"
      local case_id case_name
      case_name="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name") or "")' 2>/dev/null || true)"
      case_id="$(printf '%s' "$cresp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
data=d.get("data")
if isinstance(data, str) and data:
    print(data)
elif isinstance(data, dict) and data.get("id"):
    print(data["id"])
' 2>/dev/null || true)"
      if [[ -n "$case_id" ]]; then
        echo "已创建用例: $case_id ($case_name)"
        created=$((created + 1))
      else
        echo "用例创建失败: $case_name — $cresp"
      fi
    done < "$payloads_file"
  done

  echo "generate-create 完成: 共 $total 个用例，成功创建 $created 个"
  rm -rf "$tmp_dir"
  trap - EXIT
  if (( created == 0 )); then
    return 1
  fi
  return 0
}

# ===== import 相关（M2: spec → 定义 → 用例，含去重）=====

# 导入 spec 文件到定义；回显原始 import 响应 JSON（definitions 数组在 data.data）
# 参数: project_id spec_path module_id(可空)
import_definitions() {
  local project_id="$1" spec_path="$2" module_id="${3:-}"
  need_base_url
  need_keys
  require_project_id
  local import_body tmp_json signature resp
  # 构建 ApiTestImportRequest（moduleId 为空时省略键）
  import_body="$(python3 - "$project_id" "$module_id" <<'PY'
import json, sys
project_id, module_id = sys.argv[1], sys.argv[2]
body = {"projectId": project_id, "platform": "Swagger2", "modeId": "fullCoverage", "protocol": "HTTP", "origin": "skill"}
if module_id:
    body["moduleId"] = module_id
print(json.dumps(body, ensure_ascii=False))
PY
)"
  tmp_json="$(mktemp)"
  printf '%s' "$import_body" > "$tmp_json"
  signature="$(generate_signature)"
  resp="$(curl -sS -X POST \
  --max-time "$METERSPHERE_TIMEOUT" \  # F5
    -H "accessKey: ${METERSPHERE_ACCESS_KEY}" \
    -H "signature: ${signature}" \
    -F "file=@${spec_path};type=application/json" \
    -F "request=@${tmp_json};type=application/json" \
    "${METERSPHERE_BASE_URL%/}/api${METERSPHERE_API_DEFINITION_IMPORT_PATH}")"
  rm -f "$tmp_json"
  echo "$resp"
}

# definition_ids_by_name: 分页拉取项目持久化定义列表，输出 "id|name|method" 行
# 参数: project_id
# 背景: fullCoverage 重复导入按 path 去重不落新行，但导入响应 data.data[] 返回
#       解析阶段新生成、不可查询的 id（GET → data:null）。须按 name 从持久化
#       列表解析真实 id（详见 references/ms-api.md「接口定义导入幂等语义」）。
definition_ids_by_name () {
  local project_id="$1"
  local page=1 page_size=500
  local list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
  list_path="${list_path/\{pageSize\}/$page_size}"
  local body
  body="$(python3 - "$project_id" "$METERSPHERE_PROTOCOLS_JSON" <<'PY'
import json, sys
project_id, protocols_json = sys.argv[1], sys.argv[2]
try:
    protocols = json.loads(protocols_json)
except Exception:
    protocols = ["HTTP"]
print(json.dumps({"projectId": project_id, "protocols": protocols}, ensure_ascii=False))
PY
)"
  while :; do
    local resp
    resp="$(request POST "$list_path" "$body" "api")" || return 1
    printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
data = d.get("data") or {}
items = data.get("listObject") or []
for it in items:
    if isinstance(it, dict) and it.get("id"):
        print("%s|%s|%s" % (it["id"], it.get("name") or "", it.get("method") or ""))
' || return 1
    local page_count got
    page_count="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
pc = data.get("pageCount")
print(pc if isinstance(pc, int) else "")
')"
    got="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
print(len(data.get("listObject") or []))
')"
    if [[ -n "$page_count" ]] && (( page >= page_count )); then
      break
    fi
    # 无 pageCount 时：本页行数 < page_size 即末页（与 generate_create_api_cases 一致）
    if [[ -z "$page_count" ]] && (( got < page_size )); then
      break
    fi
    page=$((page + 1))
    list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
    list_path="${list_path/\{pageSize\}/$page_size}"
  done
  return 0
}

# import-generate: 只导入定义 + 生成用例计划（不写入用例）
# 参数: project_id spec_source module_id(可空)
import_generate () {
  local project_id="$1" spec_source="$2" module_id="${3:-}"
  local resolved name spec_path resp defs_json
  resolved="$(python3 "$SCRIPT_DIR/ms_import_helper.py" resolve "$spec_source")"
  spec_path="${resolved%%|*}"
  name="${resolved##*|}"
  echo "已解析 spec: $name" >&2
  resp="$(import_definitions "$project_id" "$spec_path" "$module_id")"
  # 解析 data.data -> [{id,name}]
  defs_json="$(printf '%s' "$resp" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps((d.get("data") or {}).get("data", []), ensure_ascii=False))')"
  local tmp_dir def_lines def_id def_name def_method resolved_def_id name_map detail_file variants_file variants
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  def_lines="$(printf '%s' "$defs_json" | python3 -c 'import json,sys; print("\n".join("%s|%s|%s" % (x.get("id",""), x.get("name") or "", x.get("method") or "") for x in json.load(sys.stdin)))')"
  echo '{"definitions":' > "$tmp_dir/out.json"
  printf '%s' "$defs_json" >> "$tmp_dir/out.json"
  echo ',"cases_plan":[' >> "$tmp_dir/out.json"
  # 拉取持久化定义列表（一次/运行，dry-run 容错）：重复导入时响应 id 可能未持久化
  name_map="$(definition_ids_by_name "$project_id")" || true
  local first=1
  while IFS= read -r def_line; do
    [[ -n "$def_line" ]] || continue
    def_id="${def_line%%|*}"
    local rest="${def_line#*|}"
    def_name="${rest%|*}"
    def_method="${rest##*|}"
    resolved_def_id="$def_id"
    if [[ -n "$def_name" && -n "$name_map" ]]; then
      resolved_def_id="$(python3 -c '
import sys
name_map, def_name, def_method, resp_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
rows = [l.split("|", 2) for l in name_map.splitlines() if l.strip()]
cands = [r for r in rows if len(r) >= 2 and r[1] == def_name]
if len(cands) == 1:
    print(cands[0][0])
elif len(cands) > 1:
    pick = cands[0][0]
    if def_method:
        m = [r for r in cands if len(r) >= 3 and r[2] == def_method]
        if len(m) == 1:
            pick = m[0][0]
    print("WARN|" + pick)
else:
    print(resp_id)
' "$name_map" "$def_name" "$def_method" "$def_id")" || resolved_def_id="$def_id"
      if [[ "$resolved_def_id" == "WARN|"* ]]; then
        echo "警告: 同名定义多个，取首个（${resolved_def_id#WARN|}）" >&2
        resolved_def_id="${resolved_def_id#WARN|}"
      fi
    fi
    detail_file="$tmp_dir/detail_${resolved_def_id}.json"
    if ! request GET "$(path_fill "$METERSPHERE_API_DEFINITION_GET_PATH" "$resolved_def_id")" "" "api" > "$detail_file"; then
      echo "定义 $def_name：导入响应 id $def_id 未持久化（解析 id $resolved_def_id，GET data:null），跳过" >&2
      continue
    fi
    variants_file="$tmp_dir/variants_${resolved_def_id}.json"
    if ! python3 "$SCRIPT_DIR/ms_generate_case.py" "$detail_file" > "$variants_file" 2> "$tmp_dir/gen.err"; then
      echo "定义 $def_id 生成用例失败: $(cat "$tmp_dir/gen.err")" >&2
      continue
    fi
    variants="$(python3 -c 'import json,sys; print(",".join('"'"'\"%s\"'"'"' % v["name"] for v in json.load(open(sys.argv[1]))))' "$variants_file")"
    if (( first )); then first=0; else printf ',' >> "$tmp_dir/out.json"; fi
    printf '{"definitionId":"%s","variants":[%s]}' "$resolved_def_id" "$variants" >> "$tmp_dir/out.json"
  done <<< "$def_lines"
  echo ']}' >> "$tmp_dir/out.json"
  cat "$tmp_dir/out.json"
  rm -rf "$tmp_dir"
  trap - EXIT
}

# import-create: 导入定义 + 写入用例（幂等：已存在同名变体则跳过）
# 参数: project_id spec_source module_id(可空)
import_create () {
  local project_id="$1" spec_source="$2" module_id="${3:-}"
  need_base_url
  need_keys
  require_project_id
  local resolved spec_path
  resolved="$(python3 "$SCRIPT_DIR/ms_import_helper.py" resolve "$spec_source")"
  spec_path="${resolved%%|*}"
  local resp defs_json tmp_dir def_lines def_id def_name def_method resolved_def_id existing detail_file variants_file payloads_file
  resp="$(import_definitions "$project_id" "$spec_path" "$module_id")"
  if ! printf '%s' "$resp" | grep -q '"success":true'; then
    die "导入定义失败: $resp"
  fi
  defs_json="$(printf '%s' "$resp" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps((d.get("data") or {}).get("data", []), ensure_ascii=False))')"
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  def_lines="$(printf '%s' "$defs_json" | python3 -c 'import json,sys; print("\n".join("%s|%s|%s" % (x.get("id",""), x.get("name") or "", x.get("method") or "") for x in json.load(sys.stdin)))')"
  local total=0 created=0 skipped=0 failed=0
  local headers signature existing_names name_map
  # existing_case_names 需要 {header:value} dict；复用 generate_signature，绝不手写签名
  signature="$(generate_signature)"
  headers="$(python3 -c 'import json,sys; print(json.dumps({"accessKey": sys.argv[1], "signature": sys.argv[2]}))' "$METERSPHERE_ACCESS_KEY" "$signature")"
  # 拉取持久化定义列表（一次/运行）：重复导入时响应 id 可能未持久化，按 name 解析真实 id
  name_map="$(definition_ids_by_name "$project_id")" || die "定义列表拉取失败（无法解析持久化 id）"
  local case_name case_id cresp
  while IFS= read -r def_line; do
    [[ -n "$def_line" ]] || continue
    def_id="${def_line%%|*}"
    local rest="${def_line#*|}"
    def_name="${rest%|*}"
    def_method="${rest##*|}"
    resolved_def_id="$def_id"
    if [[ -n "$def_name" && -n "$name_map" ]]; then
      resolved_def_id="$(python3 -c '
import sys
name_map, def_name, def_method, resp_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
rows = [l.split("|", 2) for l in name_map.splitlines() if l.strip()]
cands = [r for r in rows if len(r) >= 2 and r[1] == def_name]
if len(cands) == 1:
    print(cands[0][0])
elif len(cands) > 1:
    pick = cands[0][0]
    if def_method:
        m = [r for r in cands if len(r) >= 3 and r[2] == def_method]
        if len(m) == 1:
            pick = m[0][0]
    print("WARN|" + pick)
else:
    print(resp_id)
' "$name_map" "$def_name" "$def_method" "$def_id")" || resolved_def_id="$def_id"
      if [[ "$resolved_def_id" == "WARN|"* ]]; then
        echo "警告: 同名定义多个，取首个（${resolved_def_id#WARN|}）" >&2
        resolved_def_id="${resolved_def_id#WARN|}"
      fi
    fi
    # 去重预检：取该定义下已有用例名集合（ms_import_helper 未暴露 CLI 子命令，经模块导入调用）
    existing="$(python3 -c '
import sys, json
sys.path.insert(0, sys.argv[1])
from ms_import_helper import existing_case_names
names = existing_case_names(sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5]))
print("\n".join(sorted(names)))
' "$SCRIPT_DIR" "$project_id" "$resolved_def_id" "$METERSPHERE_BASE_URL" "$headers")" || die "已存在用例预检失败（定义 $def_name / $resolved_def_id）"
    existing_names="|$(printf '%s\n' "$existing" | tr '\n' '|')"
    detail_file="$tmp_dir/detail_${resolved_def_id}.json"
    if ! request GET "$(path_fill "$METERSPHERE_API_DEFINITION_GET_PATH" "$resolved_def_id")" "" "api" > "$detail_file"; then
      echo "定义 $def_name：detail GET 失败（id $resolved_def_id），跳过" >&2
      failed=$(( failed + 1 ))
      continue
    fi
    if ! python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
data = d.get("data")
raise SystemExit(0 if isinstance(data, dict) else 1)
' "$detail_file"; then
      echo "定义 $def_name：导入响应 id $def_id 未持久化（解析 id $resolved_def_id，GET data:null），跳过" >&2
      failed=$(( failed + 1 ))
      continue
    fi
    variants_file="$tmp_dir/variants_${resolved_def_id}.json"
    if ! python3 "$SCRIPT_DIR/ms_generate_case.py" "$detail_file" > "$variants_file" 2> "$tmp_dir/gen.err"; then
      echo "定义 $def_id 生成用例失败: $(cat "$tmp_dir/gen.err")" >&2
      continue
    fi
    payloads_file="$tmp_dir/payloads_${def_id}.jsonl"
    if ! python3 - "$variants_file" "$payloads_file" <<'PY'
import json, sys, uuid
variants = json.load(open(sys.argv[1]))
with open(sys.argv[2], "w") as f:
    for v in variants:
        if isinstance(v.get("request"), str):
            v["request"] = json.loads(v["request"])
        if not v.get("id"):
            v["id"] = str(uuid.uuid4())
        if not v.get("priority"):
            v["priority"] = "P1"
        f.write(json.dumps(v, ensure_ascii=False) + "\n")
PY
    then
      echo "定义 $def_id 载荷转换失败" >&2
      continue
    fi
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      total=$(( total + 1 ))
      case_name="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["name"])')"
      if [[ -n "$existing_names" ]] && [[ "$existing_names" == *"|${case_name}|"* ]]; then
        echo "跳过(已存在): $case_name"
        skipped=$(( skipped + 1 ))
        continue
      fi
      tmp_json="$tmp_dir/payload_$$.json"
      printf '%s' "$line" > "$tmp_json"
      signature="$(generate_signature)"
      cresp="$(curl -sS -X POST \
      --max-time "$METERSPHERE_TIMEOUT" \  # F5
        -H "accessKey: ${METERSPHERE_ACCESS_KEY}" \
        -H "signature: ${signature}" \
        -F "request=@${tmp_json};type=application/json" \
        "${METERSPHERE_BASE_URL%/}/api${METERSPHERE_API_CASE_CREATE_PATH}")"
      rm -f "$tmp_json"
      case_id="$(printf '%s' "$cresp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit
data=d.get("data")
if isinstance(data, str) and data:
    print(data)
elif isinstance(data, dict):
    print(data.get("id") or "")
else:
    print("")')"
      if [[ -n "$case_id" ]]; then
        echo "已创建用例: $case_id ($case_name)"
        created=$(( created + 1 ))
      else
        echo "用例创建失败: $case_name — $cresp"
      fi
    done < "$payloads_file"
  done <<< "$def_lines"
  if (( failed > 0 )); then
    echo "import-create 完成: 共 $total 个用例，新增 $created 个，跳过 $skipped 个，失败 $failed 个（详见上方诊断）"
  else
    echo "import-create 完成: 共 $total 个用例，新增 $created 个，跳过 $skipped 个"
  fi
  rm -rf "$tmp_dir"
  trap - EXIT
  if (( created == 0 && skipped == 0 )); then
    return 1
  fi
  return 0
}

case "$action" in
  list)
    arg="${1:-}"
    if [[ "$resource" == "organization" ]]; then
      # v2: workspace list 是 GET，无 body
      request GET "$METERSPHERE_ORGANIZATION_LIST_PATH" "" "$service_prefix"
    elif [[ "$resource" == "project" ]]; then
      # v2: /project/list/related 是 POST，body 传 workspaceId（BaseProjectController）
      if [[ -n "$arg" && "$arg" != "all" ]]; then
        request POST "$METERSPHERE_PROJECT_LIST_BY_ORG_PATH" "{\"workspaceId\":\"$arg\"}" "$service_prefix"
      elif [[ -n "$METERSPHERE_WORKSPACE_ID" ]]; then
        request POST "$METERSPHERE_PROJECT_LIST_PATH" "{\"workspaceId\":\"$METERSPHERE_WORKSPACE_ID\"}" "$service_prefix"
      else
        request POST "$METERSPHERE_PROJECT_LIST_SYSTEM_PATH" "{}" "$service_prefix"
      fi
    elif [[ "$resource" == "functional-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "functional-module list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "functional-template" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "functional-template list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "api-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "api-module list 需要 projectId"
      # v2: /api/module/list/{projectId}/{protocol} 是 GET 路径参数
      protocol="$(printf '%s' "$METERSPHERE_PROTOCOLS_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0])' 2>/dev/null || echo HTTP)"
      api_module_path="${METERSPHERE_API_MODULE_TREE_PATH/\{protocol\}/$protocol}"
      request GET "$(path_fill "$api_module_path" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "case-review-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "case-review-module list 需要 projectId"
      request POST "$(path_fill "$METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "case-review-user" ]]; then
      review_id="${arg:-}"
      [[ -n "$review_id" ]] || die "case-review-user list 需要 reviewId"
      request POST "$METERSPHERE_CASE_REVIEW_USER_OPTION_PATH" "{\"id\":\"$review_id\"}" "$service_prefix"
    elif [[ "$resource" == "comment" ]]; then
      # v2: GET /test/case/comment/list/{caseId}[/{type}[/{belongId}]]
      case_id="${1:-}"
      [[ -n "$case_id" ]] || die "comment list 需要 caseId"
      type="${2:-}"
      belong_id="${3:-}"
      if [[ -n "$belong_id" ]]; then
        resp="$(request GET "${METERSPHERE_COMMENT_LIST_PATH}/${case_id}/${type}/${belong_id}" "" "$service_prefix")"
      elif [[ -n "$type" ]]; then
        resp="$(request GET "${METERSPHERE_COMMENT_LIST_PATH}/${case_id}/${type}" "" "$service_prefix")"
      else
        resp="$(request GET "${METERSPHERE_COMMENT_LIST_PATH}/${case_id}" "" "$service_prefix")"
      fi
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "comment list 失败: $resp"
    elif [[ "$resource" == "attachment" ]]; then
      case_id="${1:-}"
      [[ -n "$case_id" ]] || die "attachment list 需要 caseId"
      resp="$(request POST "$METERSPHERE_ATTACHMENT_LIST_PATH" "{\"belongId\":\"$case_id\",\"belongType\":\"testcase\"}" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "attachment list 失败: $resp"
    else
      if [[ -n "$arg" && "$arg" == \{* ]]; then
        body="$(normalize_json_with_defaults "$resource" "$arg")"
      else
        body="$(default_list_payload "$resource" "$arg")"
      fi
      request POST "$(path_fill "$list_path" "")" "$body" "$service_prefix"
    fi
    ;;
  get)
    id="${1:-}"
    [[ -n "$id" ]] || die "get 需要 id"
  [[ -n "$get_path" ]] || die "资源 $resource 的 GET 路径未配置（对应 METERSPHERE_*_GET_PATH 环境变量为空，拒绝猜测路径）"  # F2
    request GET "$(path_fill "$get_path" "$id")" "" "$service_prefix"
    ;;
  create)
    body="${1:-}"
    [[ -n "$body" ]] || die "create 需要 JSON body"
  [[ -n "$create_path" ]] || die "资源 $resource 的创建路径未配置（对应 METERSPHERE_*_CREATE_PATH 环境变量为空，拒绝 POST 到服务根）"  # F4
    require_project_id
    body="$(normalize_json_with_defaults "$resource" "$body")"
    if [[ "$resource" == "case-review" ]]; then
      # v2: case-review 创建端点为 @RequestBody 纯 JSON（POST /test/case/review/save）
      request POST "$create_path" "$body" "$service_prefix"
    else
      # v2: 其余创建端点为 multipart/form-data（request=JSON 文件字段）
      tmp_json="$(mktemp)"
      printf '%s' "$body" > "$tmp_json"
      need_base_url
      need_keys
      signature="$(generate_signature)"
      curl -sS -X POST \
      --max-time "$METERSPHERE_TIMEOUT" \  # F5
        -H "accessKey: $METERSPHERE_ACCESS_KEY" \
        -H "signature: $signature" \
        -F "request=@${tmp_json};type=application/json" \
        "${METERSPHERE_BASE_URL%/}/${service_prefix}${create_path}"
      rm -f "$tmp_json"
    fi
    ;;
  save)
    [[ "$resource" == "comment" ]] || die "save 仅支持 comment 资源"
    require_project_id  # F3: 写入类动作必须显式设置 METERSPHERE_PROJECT_ID
    case_id="${1:-}"
    description="${2:-}"
    [[ -n "$case_id" ]] || die "comment save 需要 caseId"
    [[ -n "$description" ]] || die "comment save 需要 description"
    type="${3:-CASE}"
    belong_id="${4:-}"
    body="$(python3 - <<'PY' "$case_id" "$description" "$type" "$belong_id"
import json,sys
case_id, description, ctype, belong_id = sys.argv[1:5]
print(json.dumps({"caseId": case_id, "description": description, "type": ctype, "belongId": belong_id}, ensure_ascii=False))
PY
)"
    resp="$(request POST "$METERSPHERE_COMMENT_CREATE_PATH" "$body" "$service_prefix")"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "comment save 失败: $resp"
    ;;
  delete)
    require_project_id  # F3: 写入类动作必须显式设置 METERSPHERE_PROJECT_ID
    if [[ "$resource" == "comment" ]]; then
      comment_id="${1:-}"
      [[ -n "$comment_id" ]] || die "comment delete 需要 commentId"
      resp="$(request GET "${METERSPHERE_COMMENT_DELETE_PATH}/${comment_id}" "" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "comment delete 失败: $resp"
    elif [[ "$resource" == "attachment" ]]; then
      attachment_id="${1:-}"
      [[ -n "$attachment_id" ]] || die "attachment delete 需要 attachmentId"
      resp="$(request GET "${METERSPHERE_ATTACHMENT_DELETE_PATH}/${attachment_id}" "" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "attachment delete 失败: $resp"
    elif [[ "$resource" == "functional-case" ]]; then
      case_id="${1:-}"
      [[ -n "$case_id" ]] || die "functional-case delete 需要 caseId"
      require_project_id
      resp="$(request POST "$(path_fill "$METERSPHERE_FUNCTIONAL_CASE_DELETE_PATH" "$case_id")" "" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "functional-case delete 失败: $resp"
    else
      die "delete 仅支持 comment / attachment / functional-case 资源"
    fi
    ;;
  edit)
    [[ "$resource" == "comment" ]] || die "edit 仅支持 comment 资源"
    require_project_id  # F3: 写入类动作必须显式设置 METERSPHERE_PROJECT_ID
    comment_id="${1:-}"
    case_id="${2:-}"
    description="${3:-}"
    [[ -n "$comment_id" ]] || die "comment edit 需要 commentId"
    [[ -n "$case_id" ]] || die "comment edit 需要 caseId"
    [[ -n "$description" ]] || die "comment edit 需要 description"
    type="${4:-CASE}"
    belong_id="${5:-}"
    body="$(python3 - <<'PY' "$comment_id" "$case_id" "$description" "$type" "$belong_id"
import json,sys
comment_id, case_id, description, ctype, belong_id = sys.argv[1:6]
print(json.dumps({"id": comment_id, "caseId": case_id, "description": description, "type": ctype, "belongId": belong_id}, ensure_ascii=False))
PY
)"
    resp="$(request POST "$METERSPHERE_COMMENT_EDIT_PATH" "$body" "$service_prefix")"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "comment edit 失败: $resp"
    ;;
  generate)
    [[ "$resource" == "functional-case" ]] || die "generate 仅支持 functional-case 资源"
    project_id="${1:-}"
    module_id="${2:-}"
    template_id="${3:-}"
    req_file="${4:-}"
    [[ -n "$project_id" ]] || die "generate 需要 projectId"
    [[ -n "$module_id" ]] || die "generate 需要 moduleId"
    [[ -n "$template_id" ]] || die "generate 需要 templateId"
    [[ -n "$req_file" ]] || die "generate 需要 requirement-file"
    python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$project_id" "$module_id" "$req_file" --templateId "$template_id"
    ;;
  batch-create)
    [[ "$resource" == "functional-case" ]] || die "batch-create 仅支持 functional-case 资源"
    json_file="${1:-}"
    [[ -n "$json_file" ]] || die "batch-create 需要 JSON 数组文件"
    [[ -f "$json_file" ]] || die "batch-create 文件不存在: $json_file"
    require_project_id
    batch_create_functional_cases "$json_file"
    ;;
  generate-create)
    if [[ "$resource" == "functional-case" ]]; then
      project_id="${1:-}"
      module_id="${2:-}"
      template_id="${3:-}"
      req_file="${4:-}"
      [[ -n "$project_id" ]] || die "generate-create 需要 projectId"
      [[ -n "$module_id" ]] || die "generate-create 需要 moduleId"
      [[ -n "$template_id" ]] || die "generate-create 需要 templateId"
      [[ -n "$req_file" ]] || die "generate-create 需要 requirement-file"
      require_project_id
      tmp_json="$(mktemp)"
      python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$project_id" "$module_id" "$req_file" --templateId "$template_id" > "$tmp_json"
      batch_create_functional_cases "$tmp_json"
      rm -f "$tmp_json"
    elif [[ "$resource" == "api-case" ]]; then
      if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || "${1:-}" == "help" ]]; then
        usage
        exit 0
      fi
      project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
      [[ -n "$project_id" ]] || die "api-case generate-create 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
      shift || true
      generate_create_api_cases "$project_id" "$@"
      exit $?
    else
      die "generate-create 仅支持 functional-case / api-case 资源"
    fi
    ;;
  upload)
    [[ "$resource" == "attachment" ]] || die "upload 仅支持 attachment 资源"
    case_id="${1:-}"
    file="${2:-}"
    [[ -n "$case_id" ]] || die "attachment upload 需要 caseId"
    [[ -n "$file" ]] || die "attachment upload 需要 file"
    [[ -f "$file" ]] || die "attachment upload 文件不存在: $file"
    require_project_id
    need_base_url
    need_keys
    signature="$(generate_signature)"
    resp="$(curl -sS -X POST \
    --max-time "$METERSPHERE_TIMEOUT" \  # F5
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -F "sourceId=$case_id" \
      -F "file=@$file" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_ATTACHMENT_UPLOAD_PATH}")"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "attachment upload 失败: $resp"
    ;;
  download)
    [[ "$resource" == "attachment" ]] || die "download 仅支持 attachment 资源"
    attachment_id="${1:-}"
    is_local="${2:-}"
    outfile="${3:-}"
    [[ -n "$attachment_id" ]] || die "attachment download 需要 attachmentId"
    [[ -n "$is_local" ]] || die "attachment download 需要 isLocal (true/false)"
    [[ -n "$outfile" ]] || die "attachment download 需要 outfile"
    need_base_url
    need_keys
    signature="$(generate_signature)"
    # F7: write to a .part file first, verify, then move — a pre-existing outfile is
    # never overwritten by a failed download and never deleted on a false positive.
    part_file="${outfile}.part"
    curl -sS -o "$part_file" -X GET --max-time "$METERSPHERE_TIMEOUT" \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_ATTACHMENT_DOWNLOAD_PATH}/${attachment_id}/${is_local}"
    if grep -q '"success":false' "$part_file" 2>/dev/null; then
      cat "$part_file" >&2
      rm -f "$part_file"
      die "attachment download 失败（原 $outfile 未被改动）"
    fi
    mv -f "$part_file" "$outfile"
    bytes="$(wc -c < "$outfile")"
    echo "已下载 $bytes 字节到 $outfile"
    ;;
  import-generate)
    [[ "$resource" == "api" ]] || die "import-generate 仅支持 api 资源"
    project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "import-generate 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
    spec_source="${2:-}"
    [[ -n "$spec_source" ]] || die "import-generate 需要 spec 文件路径或 URL"
    import_generate "$project_id" "$spec_source" "${3:-}"
    exit $?
    ;;
  import-create)
    [[ "$resource" == "api" ]] || die "import-create 仅支持 api 资源"
    project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "import-create 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
    spec_source="${2:-}"
    [[ -n "$spec_source" ]] || die "import-create 需要 spec 文件路径或 URL"
    import_create "$project_id" "$spec_source" "${3:-}"
    exit $?
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    die "不支持的 action: $action"
    ;;
esac
