#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${SKILL_DIR}/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

METERSPHERE_BASE_URL="${METERSPHERE_BASE_URL:-}"
METERSPHERE_ACCESS_KEY="${METERSPHERE_ACCESS_KEY:-${CORDYS_ACCESS_KEY:-}}"
METERSPHERE_SECRET_KEY="${METERSPHERE_SECRET_KEY:-${CORDYS_SECRET_KEY:-}}"
METERSPHERE_PROJECT_ID="${METERSPHERE_PROJECT_ID:-}"
METERSPHERE_ORGANIZATION_ID="${METERSPHERE_ORGANIZATION_ID:-100001}"
METERSPHERE_HEADERS_JSON="${METERSPHERE_HEADERS_JSON:-}"
METERSPHERE_PROTOCOLS_JSON="${METERSPHERE_PROTOCOLS_JSON:-[\"HTTP\"]}"

[[ -n "${METERSPHERE_ORGANIZATION_LIST_PATH:-}" ]] || METERSPHERE_ORGANIZATION_LIST_PATH='/system/organization/list'
[[ -n "${METERSPHERE_PROJECT_LIST_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_PATH='/project/list/options/{organizationId}'
[[ -n "${METERSPHERE_PROJECT_LIST_SYSTEM_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_SYSTEM_PATH='/system/project/list'
[[ -n "${METERSPHERE_PROJECT_LIST_BY_ORG_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_BY_ORG_PATH='/organization/project/list/{organizationId}'
[[ -n "${METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH='/functional/case/module/tree/{projectId}'
[[ -n "${METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH='/functional/case/default/template/field/{projectId}'
[[ -n "${METERSPHERE_API_MODULE_TREE_PATH:-}" ]] || METERSPHERE_API_MODULE_TREE_PATH='/api/definition/module/tree'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_LIST_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_LIST_PATH='/functional/case/page'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_GET_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_GET_PATH='/functional/case/detail/{id}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH='/functional/case/add'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH='/functional/case/review/page'
[[ -n "${METERSPHERE_CASE_REVIEW_LIST_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_LIST_PATH='/case/review/page'
[[ -n "${METERSPHERE_CASE_REVIEW_GET_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_GET_PATH='/case/review/detail/{id}'
[[ -n "${METERSPHERE_CASE_REVIEW_CREATE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_CREATE_PATH='/case/review/add'
[[ -n "${METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH='/case/review/detail/page'
[[ -n "${METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH='/case/review/module/tree/{projectId}'
[[ -n "${METERSPHERE_CASE_REVIEW_USER_OPTION_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_USER_OPTION_PATH='/case/review/user-option/{projectId}'
[[ -n "${METERSPHERE_API_DEFINITION_LIST_PATH:-}" ]] || METERSPHERE_API_DEFINITION_LIST_PATH='/api/definition/page'
[[ -n "${METERSPHERE_API_DEFINITION_GET_PATH:-}" ]] || METERSPHERE_API_DEFINITION_GET_PATH='/api/definition/get-detail/{id}'
[[ -n "${METERSPHERE_API_DEFINITION_CREATE_PATH:-}" ]] || METERSPHERE_API_DEFINITION_CREATE_PATH='/api/definition/add'
[[ -n "${METERSPHERE_API_CASE_LIST_PATH:-}" ]] || METERSPHERE_API_CASE_LIST_PATH='/api/case/page'
[[ -n "${METERSPHERE_API_CASE_GET_PATH:-}" ]] || METERSPHERE_API_CASE_GET_PATH='/api/case/get-detail/{id}'
[[ -n "${METERSPHERE_API_CASE_CREATE_PATH:-}" ]] || METERSPHERE_API_CASE_CREATE_PATH='/api/case/add'

die() { echo "错误: $*" >&2; exit 1; }

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
  python3 - <<'PY' "$resource" "$keyword" "$METERSPHERE_PROJECT_ID" "$METERSPHERE_ORGANIZATION_ID" "$METERSPHERE_PROTOCOLS_JSON"
import json,sys
resource, keyword, project_id, org_id, protocols_json = sys.argv[1:6]
payload = {
  "current": 1,
  "pageSize": 20,
}
if keyword:
    payload["keyword"] = keyword
if project_id:
    payload["projectId"] = project_id
if org_id:
    payload["organizationId"] = org_id
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
  python3 - <<'PY' "$resource" "$body" "$METERSPHERE_PROJECT_ID" "$METERSPHERE_ORGANIZATION_ID" "$METERSPHERE_PROTOCOLS_JSON"
import json,sys
resource, body, project_id, org_id, protocols_json = sys.argv[1:6]
data = json.loads(body)
if isinstance(data, dict):
    if project_id and not data.get("projectId"):
        data["projectId"] = project_id
    if org_id and not data.get("organizationId"):
        data["organizationId"] = org_id
    if resource in ("api", "api-case") and not data.get("protocols"):
        try:
            data["protocols"] = json.loads(protocols_json)
        except Exception:
            pass
print(json.dumps(data, ensure_ascii=False))
PY
}

request() {
  local method="$1" path="$2" body="${3:-}"
  need_base_url
  need_keys
  local url="${METERSPHERE_BASE_URL%/}${path}"
  local header_file
  header_file="$(mktemp)"
  build_header_args "$header_file"
  local -a header_args=()
  while IFS= read -r line; do
    header_args+=("$line")
  done < "$header_file"
  if [[ -n "$body" ]]; then
    curl -sS -X "$method" "$url" "${header_args[@]}" -d "$body"
  else
    curl -sS -X "$method" "$url" "${header_args[@]}"
  fi
  rm -f "$header_file"
}

path_fill() {
  local template="$1" value="$2"
  template="${template/\{id\}/$value}"
  template="${template/\{organizationId\}/$value}"
  template="${template/\{projectId\}/$value}"
  echo "$template"
}

resource_paths() {
  case "$1" in
    organization)
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
      echo "$METERSPHERE_API_DEFINITION_LIST_PATH|$METERSPHERE_API_DEFINITION_GET_PATH|$METERSPHERE_API_DEFINITION_CREATE_PATH"
      ;;
    api-case)
      echo "$METERSPHERE_API_CASE_LIST_PATH|$METERSPHERE_API_CASE_GET_PATH|$METERSPHERE_API_CASE_CREATE_PATH"
      ;;
    *)
      die "不支持的资源: $1"
      ;;
  esac
}

usage() {
  cat <<'EOF'
ms — MeterSphere CLI

用法:
  ms <resource> <action> [args...]
  ms raw <METHOD> <PATH> [JSON]
  ms functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
  ms functional-case batch-create <json-file>
  ms functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
  ms api import-generate <projectId> <moduleId> <openapi-file-or-url>
  ms api batch-create <json-file>
  ms api import-create <projectId> <moduleId> <openapi-file-or-url>
  ms reviewed-summary <projectId> [keyword]

资源:
  organization
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

动作:
  list [关键词|JSON]
  get <id>
  create <JSON>
  generate <...>
  batch-create <json-file>
  generate-create <...>
  import-generate <...>
  import-create <...>

示例:
  ms organization list
  ms organization list "默认"
  ms project list
  ms project list all
  ms project list org-123
  ms functional-module list 100001100001
  ms functional-template list 100001100001
  ms api-module list 100001100001
  ms functional-case list "登录"
  ms functional-case-review list '{"caseId":"922301316472832"}'
  ms case-review list '{"projectId":"1163437937827840"}'
  ms case-review get 922833892417536
  ms case-review-detail list '{"projectId":"1163437937827840","reviewId":"922833892417536","viewStatusFlag":false}'
  ms case-review-module list 1163437937827840
  ms case-review-user list 1163437937827840
  ms functional-case get fc-123
  ms functional-case create '{"name":"登录用例"}'
  ms api list '{"keyword":"用户"}'
  ms api-case create '{"name":"获取用户详情-200","apiDefinitionId":"api-1"}'
  ms functional-case generate 100001100001 733374274027520 100844458962059505 ./requirement.txt
  ms functional-case batch-create ./functional-cases.json
  ms functional-case generate-create 100001100001 733374274027520 100844458962059505 ./requirement.txt
  ms api import-generate 100001100001 root ./openapi.json
  ms api batch-create ./api-bundle.json
  ms api import-create 100001100001 root ./openapi.json
  ms raw GET /api/project/list
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

resource="$cmd"
action="${1:-}"
[[ -n "$action" ]] || die "缺少 action"
shift || true
IFS='|' read -r list_path get_path create_path <<< "$(resource_paths "$resource")"

case "$action" in
  list)
    arg="${1:-}"
    if [[ "$resource" == "organization" ]]; then
      if [[ -n "$arg" && "$arg" == \{* ]]; then
        body="$arg"
      elif [[ -n "$arg" ]]; then
        body="{\"current\":1,\"pageSize\":20,\"keyword\":\"$arg\"}"
      else
        body='{"current":1,"pageSize":20}'
      fi
      request POST "$list_path" "$body"
    elif [[ "$resource" == "project" ]]; then
      if [[ "$arg" == "all" ]]; then
        request GET "$METERSPHERE_PROJECT_LIST_SYSTEM_PATH"
      elif [[ -n "$arg" ]]; then
        request GET "$(path_fill "$METERSPHERE_PROJECT_LIST_BY_ORG_PATH" "$arg")"
      else
        request GET "$(path_fill "$METERSPHERE_PROJECT_LIST_PATH" "$METERSPHERE_ORGANIZATION_ID")"
      fi
    elif [[ "$resource" == "functional-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "functional-module list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH" "$project_id")"
    elif [[ "$resource" == "functional-template" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "functional-template list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH" "$project_id")"
    elif [[ "$resource" == "api-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "api-module list 需要 projectId"
      body="{\"projectId\":\"$project_id\",\"protocols\":$(printf '%s' "$METERSPHERE_PROTOCOLS_JSON")}"
      request POST "$METERSPHERE_API_MODULE_TREE_PATH" "$body"
    elif [[ "$resource" == "case-review-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "case-review-module list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH" "$project_id")"
    elif [[ "$resource" == "case-review-user" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "case-review-user list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_CASE_REVIEW_USER_OPTION_PATH" "$project_id")"
    else
      if [[ -n "$arg" && "$arg" == \{* ]]; then
        body="$(normalize_json_with_defaults "$resource" "$arg")"
      else
        body="$(default_list_payload "$resource" "$arg")"
      fi
      request POST "$list_path" "$body"
    fi
    ;;
  get)
    id="${1:-}"
    [[ -n "$id" ]] || die "get 需要 id"
    request GET "$(path_fill "$get_path" "$id")"
    ;;
  create)
    body="${1:-}"
    [[ -n "$body" ]] || die "create 需要 JSON body"
    body="$(normalize_json_with_defaults "$resource" "$body")"
    request POST "$create_path" "$body"
    ;;
  generate)
    [[ "$resource" == "functional-case" ]] || die "generate 目前仅支持 functional-case"
    project_id="${1:-}"; module_id="${2:-}"; template_id="${3:-}"; requirement_file="${4:-}"
    [[ -n "$project_id" && -n "$module_id" && -n "$template_id" && -n "$requirement_file" ]] || die "用法: ms functional-case generate <projectId> <moduleId> <templateId> <requirement-file>"
    python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$project_id" "$module_id" "$template_id" "$requirement_file"
    ;;
  batch-create)
    json_file="${1:-}"
    [[ -n "$json_file" ]] || die "batch-create 需要 json 文件路径"
    if [[ "$resource" == "functional-case" ]]; then
      python3 "$SCRIPT_DIR/ms_batch.py" functional-cases "$json_file"
    elif [[ "$resource" == "api" ]]; then
      python3 "$SCRIPT_DIR/ms_batch.py" api-import "$json_file"
    else
      die "batch-create 目前仅支持 functional-case / api"
    fi
    ;;
  generate-create)
    [[ "$resource" == "functional-case" ]] || die "generate-create 目前仅支持 functional-case"
    project_id="${1:-}"; module_id="${2:-}"; template_id="${3:-}"; requirement_file="${4:-}"
    [[ -n "$project_id" && -n "$module_id" && -n "$template_id" && -n "$requirement_file" ]] || die "用法: ms functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>"
    tmp_json="$(mktemp)"
    python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$project_id" "$module_id" "$template_id" "$requirement_file" > "$tmp_json"
    python3 "$SCRIPT_DIR/ms_batch.py" functional-cases "$tmp_json"
    rm -f "$tmp_json"
    ;;
  import-generate)
    [[ "$resource" == "api" ]] || die "import-generate 目前仅支持 api"
    project_id="${1:-}"; module_id="${2:-}"; openapi_src="${3:-}"
    [[ -n "$project_id" && -n "$module_id" && -n "$openapi_src" ]] || die "用法: ms api import-generate <projectId> <moduleId> <openapi-file-or-url>"
    python3 "$SCRIPT_DIR/ms_generate.py" api-import "$project_id" "$module_id" "$openapi_src"
    ;;
  import-create)
    [[ "$resource" == "api" ]] || die "import-create 目前仅支持 api"
    project_id="${1:-}"; module_id="${2:-}"; openapi_src="${3:-}"
    [[ -n "$project_id" && -n "$module_id" && -n "$openapi_src" ]] || die "用法: ms api import-create <projectId> <moduleId> <openapi-file-or-url>"
    tmp_json="$(mktemp)"
    python3 "$SCRIPT_DIR/ms_generate.py" api-import "$project_id" "$module_id" "$openapi_src" > "$tmp_json"
    python3 "$SCRIPT_DIR/ms_batch.py" api-import "$tmp_json"
    rm -f "$tmp_json"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    die "不支持的 action: $action"
    ;;
esac
