#!/usr/bin/env python3
"""Prepare and submit MeterSphere v3 bugs through the supported multipart API."""

import argparse
import hashlib
import html
import json
import mimetypes
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable
from urllib import error, request
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ENV_FILE = SKILL_DIR / ".env"


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()
BASE_URL = os.environ.get("METERSPHERE_BASE_URL", "").rstrip("/")
ACCESS_KEY = os.environ.get("METERSPHERE_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("METERSPHERE_SECRET_KEY", "")
BUG_ADD_PATH = os.environ.get("METERSPHERE_BUG_ADD_PATH", "/bug/add")
BUG_DETAIL_PATH = os.environ.get("METERSPHERE_BUG_DETAIL_PATH", "/bug/get/{id}")
BUG_ATTACHMENT_LIST_PATH = os.environ.get("METERSPHERE_BUG_ATTACHMENT_LIST_PATH", "/bug/attachment/list/{id}")
BUG_TEMPLATE_OPTION_PATH = os.environ.get("METERSPHERE_BUG_TEMPLATE_OPTION_PATH", "/bug/template/option/{projectId}")
BUG_TEMPLATE_DETAIL_PATH = os.environ.get("METERSPHERE_BUG_TEMPLATE_DETAIL_PATH", "/bug/template/detail")
ALLOW_INSECURE_HTTP = os.environ.get("METERSPHERE_ALLOW_INSECURE_HTTP", "").strip().lower() == "true"


def die(message: str) -> None:
    print(f"错误: {message}", file=sys.stderr)
    raise SystemExit(1)


def json_output(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def require_settings() -> None:
    missing = [
        name
        for name, value in (
            ("METERSPHERE_BASE_URL", BASE_URL),
            ("METERSPHERE_ACCESS_KEY", ACCESS_KEY),
            ("METERSPHERE_SECRET_KEY", SECRET_KEY),
        )
        if not value
    ]
    if missing:
        die("未设置 " + " / ".join(missing))


def signature() -> str:
    plain = f"{ACCESS_KEY}|{uuid.uuid4()}|{int(time.time() * 1000)}"
    try:
        process = subprocess.run(
            [
                "openssl",
                "enc",
                "-aes-128-cbc",
                "-K",
                SECRET_KEY.encode("utf-8").hex(),
                "-iv",
                ACCESS_KEY.encode("utf-8").hex(),
                "-base64",
                "-A",
                "-nosalt",
            ],
            input=plain.encode("utf-8"),
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        die("未找到 openssl，无法生成 MeterSphere API 签名")
    except subprocess.CalledProcessError as exc:
        die(exc.stderr.decode("utf-8", errors="replace") or "生成 MeterSphere API 签名失败")
    return process.stdout.decode("utf-8").strip()


def headers(content_type: str = "application/json") -> dict[str, str]:
    require_settings()
    result = {
        "accessKey": ACCESS_KEY,
        "signature": signature(),
        "Content-Type": content_type,
    }
    extra = os.environ.get("METERSPHERE_HEADERS_JSON", "")
    if extra:
        try:
            parsed = json.loads(extra)
            if not isinstance(parsed, dict):
                die("METERSPHERE_HEADERS_JSON 必须是 JSON 对象")
            result.update({str(k): str(v) for k, v in parsed.items()})
        except json.JSONDecodeError as exc:
            die(f"METERSPHERE_HEADERS_JSON 不是有效 JSON: {exc.msg}")
    return result


def api_url(path: str) -> str:
    require_settings()
    parsed = urlparse(BASE_URL)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        die("METERSPHERE_BASE_URL 必须是带主机名的 HTTP(S) URL")
    if parsed.scheme == "http" and not ALLOW_INSECURE_HTTP:
        die("拒绝通过明文 HTTP 发送 API 签名、缺陷内容或附件。内网实例如必须使用 HTTP，请显式设置 METERSPHERE_ALLOW_INSECURE_HTTP=true")
    if not path.startswith("/"):
        die("MeterSphere API 路径必须以 / 开头")
    return BASE_URL + path


def extract_data(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def http_json(method: str, path: str, body: Any | None = None) -> Any:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(api_url(path), data=data, headers=headers(), method=method)
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"HTTP {exc.code} {path}: {detail}")
    except error.URLError as exc:
        die(f"无法请求 {path}: {exc.reason}")
    try:
        return extract_data(json.loads(raw))
    except json.JSONDecodeError:
        die(f"{path} 返回了非 JSON 响应: {raw[:500]}")


def encode_multipart(parts: Iterable[tuple[str, str | None, str | None, bytes]]) -> tuple[bytes, str]:
    boundary = "----MeterSphereSkill" + uuid.uuid4().hex
    buffer = bytearray()
    for field_name, filename, content_type, content in parts:
        buffer.extend(f"--{boundary}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{field_name}"'
        if filename is not None:
            safe_filename = filename.replace('"', "_").replace("\r", "_").replace("\n", "_")
            disposition += f'; filename="{safe_filename}"'
        buffer.extend((disposition + "\r\n").encode("utf-8"))
        if content_type:
            buffer.extend(f"Content-Type: {content_type}\r\n".encode("utf-8"))
        buffer.extend(b"\r\n")
        buffer.extend(content)
        buffer.extend(b"\r\n")
    buffer.extend(f"--{boundary}--\r\n".encode())
    return bytes(buffer), boundary


def http_multipart(path: str, payload: dict[str, Any], files: list[Path]) -> Any:
    parts: list[tuple[str, str | None, str | None, bytes]] = [
        ("request", "request.json", "application/json", json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    ]
    for file_path in files:
        parts.append(
            (
                "files",
                file_path.name,
                mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
                file_path.read_bytes(),
            )
        )
    body, boundary = encode_multipart(parts)
    req = request.Request(
        api_url(path),
        data=body,
        headers=headers(f"multipart/form-data; boundary={boundary}"),
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"HTTP {exc.code} {BUG_ADD_PATH}: {detail}")
    except error.URLError as exc:
        die(f"无法请求 {BUG_ADD_PATH}: {exc.reason}")
    try:
        return extract_data(json.loads(raw))
    except json.JSONDecodeError:
        die(f"{BUG_ADD_PATH} 返回了非 JSON 响应: {raw[:500]}")


def load_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"找不到 JSON 文件: {path}")
    except json.JSONDecodeError as exc:
        die(f"{path} 不是有效 JSON: 第 {exc.lineno} 行，第 {exc.colno} 列")


def as_text(value: Any, field: str, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        die(f"{field} 必须是字符串")
    result = value.strip()
    if required and not result:
        die(f"缺少必填字段: {field}")
    return result


def as_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        die(f"{field} 必须是字符串数组")
    return [item.strip() for item in value if item.strip()]


def select_template(project_id: str, template_id: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    options = http_json("GET", BUG_TEMPLATE_OPTION_PATH.replace("{projectId}", project_id))
    if not isinstance(options, list):
        die("缺陷模板接口没有返回模板数组")
    selected = next((item for item in options if isinstance(item, dict) and item.get("id") == template_id), None)
    if not selected and not template_id:
        selected = next((item for item in options if isinstance(item, dict) and item.get("enableDefault")), None)
    if not selected and len(options) == 1 and isinstance(options[0], dict):
        selected = options[0]
    if not selected:
        die("无法确定缺陷模板。请用 --template 指定模板 ID，或在 MeterSphere 配置默认缺陷模板")
    template_id = selected.get("id")
    if not isinstance(template_id, str) or not template_id:
        die("缺陷模板返回中缺少 id")
    detail = http_json("POST", BUG_TEMPLATE_DETAIL_PATH, {"projectId": project_id, "id": template_id})
    if not isinstance(detail, dict):
        die("缺陷模板详情接口没有返回对象")
    fields = detail.get("customFields") or []
    if not isinstance(fields, list):
        die("缺陷模板详情 customFields 不是数组")
    return selected, [field for field in fields if isinstance(field, dict)]


def field_kind(field: dict[str, Any]) -> str:
    values = " ".join(str(field.get(key, "")) for key in ("fieldId", "fieldName", "fieldKey")).lower()
    if any(token in values for token in ("handler", "handleuser", "assignee", "负责人", "处理人", "指派", "经办")):
        return "assignee"
    if any(token in values for token in ("severity", "priority", "严重", "优先级")):
        return "severity"
    if any(token in values for token in ("prerequisite", "precondition", "前置", "前提")):
        return "prerequisite"
    if any(token in values for token in ("expected", "预期")):
        return "expectedResult"
    if any(token in values for token in ("actual", "实际结果", "现象")):
        return "actualResult"
    if any(token in values for token in ("reproduce", "reproduction", "steps", "复现", "重现", "操作步骤")):
        return "steps"
    if any(token in values for token in ("environment", "环境")):
        return "environment"
    return ""


def field_value_from_options(field: dict[str, Any], desired: str) -> tuple[str, str | None]:
    options = field.get("options")
    if not isinstance(options, list):
        try:
            options = json.loads(field.get("platformOptionJson") or "[]")
        except (TypeError, json.JSONDecodeError):
            options = []
    if not desired:
        return "", None
    matches = []
    for option in options:
        if not isinstance(option, dict):
            continue
        value, text = str(option.get("value", "")), str(option.get("text", option.get("label", "")))
        if desired == value or desired.casefold() == text.casefold():
            matches.append((value, text))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        die(f"字段 {field.get('fieldName')} 的候选值存在重名，请输入唯一 ID")
    die(f"在字段 {field.get('fieldName')} 中找不到选项: {desired}")


def normalized_input(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        die("输入必须是 JSON 对象")
    steps = source.get("steps", [])
    if isinstance(steps, str):
        steps = [line.strip() for line in steps.splitlines() if line.strip()]
    if not isinstance(steps, list) or not all(isinstance(item, str) for item in steps):
        die("steps 必须是字符串或字符串数组")
    return {
        "title": as_text(source.get("title") or source.get("summary"), "title", True),
        "prerequisite": as_text(source.get("prerequisite") or source.get("precondition"), "prerequisite"),
        "steps": [item.strip() for item in steps if item.strip()],
        "actualResult": as_text(source.get("actualResult") or source.get("actual"), "actualResult"),
        "expectedResult": as_text(source.get("expectedResult") or source.get("expected"), "expectedResult"),
        "environment": as_text(source.get("environment"), "environment"),
        "severity": as_text(source.get("severity"), "severity"),
        "assignee": as_text(source.get("assignee") or source.get("handleUser"), "assignee"),
        "tags": as_string_list(source.get("tags"), "tags"),
        "attachments": as_string_list(source.get("attachments") or source.get("images"), "attachments"),
        "attachmentCaptions": as_string_list(source.get("attachmentCaptions"), "attachmentCaptions"),
        "customFields": source.get("customFields") or {},
    }


def make_description(draft: dict[str, Any]) -> str:
    sections = [
        ("前置条件", draft["prerequisite"]),
        ("复现步骤", "\n".join(f"{index}. {step}" for index, step in enumerate(draft["steps"], 1))),
        ("实际结果", draft["actualResult"]),
        ("预期结果", draft["expectedResult"]),
        ("环境信息", draft["environment"]),
        ("附图", "\n".join(draft.get("attachmentCaptions") or [])),
    ]
    html_sections = []
    for heading, content in sections:
        if content:
            html_sections.append(f"<h3>{heading}</h3><p>{html.escape(content).replace(chr(10), '<br>')}</p>")
    return "".join(html_sections)


def format_custom_field(field: dict[str, Any], value: Any, text: str | None = None) -> dict[str, str]:
    field_id = str(field.get("fieldId") or "")
    field_name = str(field.get("fieldName") or field_id)
    field_type = str(field.get("type") or "INPUT")
    if not field_id:
        die("缺陷模板中存在无 fieldId 的自定义字段")
    if isinstance(value, list):
        serialized = json.dumps(value, ensure_ascii=False)
    else:
        serialized = str(value)
    result = {"id": field_id, "name": field_name, "type": field_type, "value": serialized}
    if text is not None:
        result["text"] = text
    return result


def resolve_custom_fields(
    draft: dict[str, Any], fields: list[dict[str, Any]]
) -> tuple[list[dict[str, str]], list[str], list[dict[str, str]]]:
    explicit = draft["customFields"]
    if not isinstance(explicit, dict):
        die("customFields 必须是以模板 fieldId 为键的 JSON 对象")

    member_types = {"MEMBER", "MULTIPLE_MEMBER"}
    member_fields = [field for field in fields if str(field.get("type") or "") in member_types]
    explicit_assignee_fields = [
        field for field in member_fields if field.get("fieldId") in explicit and explicit[field.get("fieldId")]
    ]
    assignment_field_id = None
    if draft["assignee"]:
        if len(explicit_assignee_fields) > 1:
            die("assignee 只能对应一个成员字段；请只在 customFields 中填写一个成员字段")
        if explicit_assignee_fields:
            assignment_field_id = str(explicit_assignee_fields[0].get("fieldId"))
        else:
            inferred = [field for field in member_fields if field_kind(field) == "assignee"]
            if len(inferred) != 1:
                die("无法唯一识别缺陷处理人成员字段。请在 customFields 中以模板成员 fieldId 显式填写处理人")
            assignment_field_id = str(inferred[0].get("fieldId"))

    result: list[dict[str, str]] = []
    unresolved: list[str] = []
    assignment_values: list[dict[str, str]] = []
    for field in fields:
        if field.get("platformSystemField"):
            continue
        field_id = str(field.get("fieldId") or "")
        field_type = str(field.get("type") or "")
        required = bool(field.get("required"))
        value = explicit.get(field_id, None)
        text = None
        if value is None:
            kind = field_kind(field)
            value = draft.get(kind) if kind else None
        if value is None or value == "" or value == []:
            default = field.get("defaultValue")
            value = default if default not in (None, "", []) else None
        if value is not None and field_type in {"MEMBER", "SELECT", "RADIO"}:
            value, text = field_value_from_options(field, str(value))
        elif value is not None and field_type in {"MULTIPLE_MEMBER", "MULTIPLE_SELECT", "CHECKBOX"}:
            values = value if isinstance(value, list) else [value]
            selections = [field_value_from_options(field, str(item)) for item in values]
            value = [item[0] for item in selections]
            text = json.dumps([item[1] for item in selections], ensure_ascii=False)
        if value is None or value == "" or value == []:
            if required:
                unresolved.append(f"{field.get('fieldName') or field_id} ({field_id})")
            continue
        formatted = format_custom_field(field, value, text)
        result.append(formatted)
        if field_id == assignment_field_id:
            assignment_values.append({"fieldId": field_id, "value": formatted["value"], "text": formatted.get("text", "")})
    if draft["assignee"] and not assignment_values:
        die("处理人没有写入缺陷请求，请检查 customFields 和模板成员字段")
    return result, unresolved, assignment_values


def file_paths(file_values: list[str], base_dir: Path) -> list[Path]:
    result = []
    for value in file_values:
        path = Path(value)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        if not path.is_file():
            die(f"附件不存在或不是文件: {path}")
        result.append(path)
    return result


def preview_integrity(request_payload: dict[str, Any], files: list[Path]) -> str:
    manifest = [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in files
    ]
    canonical = json.dumps(
        {"request": request_payload, "files": manifest},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def same_custom_value(actual: Any, expected: str) -> bool:
    if str(actual) == expected:
        return True
    try:
        return json.loads(str(actual)) == json.loads(expected)
    except (TypeError, json.JSONDecodeError):
        return False


def verify_assignments(detail: dict[str, Any], expected: list[dict[str, str]]) -> list[str]:
    errors = []
    detail_fields = detail.get("customFields") or []
    if not isinstance(detail_fields, list):
        return ["缺陷详情未返回 customFields，无法验证处理人"] if expected else []
    for assignment in expected:
        actual = next(
            (
                field
                for field in detail_fields
                if isinstance(field, dict) and str(field.get("id") or field.get("fieldId") or "") == assignment["fieldId"]
            ),
            None,
        )
        if not actual or not same_custom_value(actual.get("value"), assignment["value"]):
            errors.append(f"处理人字段 {assignment['fieldId']} 未按请求值保存")
    return errors


def verify_attachments(attachments: list[Any], files: list[Path]) -> list[str]:
    available = [item for item in attachments if isinstance(item, dict)]
    errors = []
    for file_path in files:
        match = next(
            (
                item
                for item in available
                if item.get("fileName") == file_path.name
                and (item.get("fileSize") is None or int(item["fileSize"]) == file_path.stat().st_size)
            ),
            None,
        )
        if match:
            available.remove(match)
        else:
            errors.append(f"未在回读附件中找到 {file_path.name}（大小 {file_path.stat().st_size}）")
    return errors


def command_prepare(args: argparse.Namespace) -> None:
    source_path = Path(args.input).resolve()
    source = load_json(str(source_path))
    draft = normalized_input(source)
    if len(draft["title"]) > 255:
        die("title 不能超过 255 个字符")
    selected, fields = select_template(args.project_id, args.template or os.environ.get("METERSPHERE_BUG_TEMPLATE_ID"))
    custom_fields, unresolved, assignment_values = resolve_custom_fields(draft, fields)
    if unresolved:
        die("以下必填模板字段无法从输入推导，请在 customFields 中按 fieldId 补充值: " + "；".join(unresolved))
    attachments = file_paths(draft["attachments"], source_path.parent)
    if draft["attachmentCaptions"] and len(draft["attachmentCaptions"]) != len(attachments):
        die("attachmentCaptions 必须与 attachments 一一对应，且顺序一致")
    if not draft["attachmentCaptions"]:
        draft["attachmentCaptions"] = [f"缺陷复现截图：{path.name}" for path in attachments]
    prepared = {
        "schemaVersion": 1,
        "projectId": args.project_id,
        "templateId": selected["id"],
        "draft": draft,
        "request": {
            "projectId": args.project_id,
            "templateId": selected["id"],
            "title": draft["title"],
            "description": make_description(draft),
            "tags": draft["tags"],
            "customFields": custom_fields,
        },
        "files": [str(path) for path in attachments],
        "preflight": {
            "templateName": selected.get("name"),
            "attachmentCount": len(attachments),
            "assignee": draft["assignee"] or None,
            "assigneeAssignments": assignment_values,
            "requiresExplicitConfirmation": True,
        },
    }
    prepared["integrity"] = preview_integrity(prepared["request"], attachments)
    json_output(prepared)


def command_template(args: argparse.Namespace) -> None:
    selected, fields = select_template(args.project_id, args.template or os.environ.get("METERSPHERE_BUG_TEMPLATE_ID"))
    json_output({"template": selected, "customFields": fields})


def command_members(args: argparse.Namespace) -> None:
    _, fields = select_template(args.project_id, args.template or os.environ.get("METERSPHERE_BUG_TEMPLATE_ID"))
    member_fields = []
    for field in fields:
        if str(field.get("type")) not in {"MEMBER", "MULTIPLE_MEMBER"}:
            continue
        options = field.get("options")
        if not isinstance(options, list):
            try:
                options = json.loads(field.get("platformOptionJson") or "[]")
            except (TypeError, json.JSONDecodeError):
                options = []
        member_fields.append(
            {
                "fieldId": field.get("fieldId"),
                "fieldName": field.get("fieldName"),
                "required": bool(field.get("required")),
                "options": options,
            }
        )
    json_output({"projectId": args.project_id, "memberFields": member_fields})


def extract_bug_id(created: Any) -> str:
    if isinstance(created, dict):
        candidate = created.get("id")
        if candidate is not None and str(candidate):
            return str(candidate)
    die("创建接口没有返回缺陷 id，无法执行回读校验")
    return ""  # unreachable, keeps type checkers satisfied


def command_submit(args: argparse.Namespace) -> None:
    if not args.confirm:
        die("提交 Bug 会创建外部记录。请检查 prepare 输出后，追加 --confirm 才能提交")
    prepared_path = Path(args.prepared).resolve()
    prepared = load_json(str(prepared_path))
    if not isinstance(prepared, dict) or prepared.get("schemaVersion") != 1:
        die("提交文件不是本脚本生成的 schemaVersion 1 预览文件")
    payload = prepared.get("request")
    if not isinstance(payload, dict):
        die("预览文件缺少 request 对象")
    for required in ("projectId", "templateId", "title", "description"):
        if not isinstance(payload.get(required), str) or not payload[required].strip():
            die(f"预览文件 request 缺少 {required}")
    files = file_paths(prepared.get("files") or [], prepared_path.parent)
    expected_integrity = prepared.get("integrity")
    actual_integrity = preview_integrity(payload, files)
    if not isinstance(expected_integrity, str) or expected_integrity != actual_integrity:
        die("预览文件或附件已在审核后变化。请重新执行 bug prepare、审核新预览，再提交")

    created = http_multipart(BUG_ADD_PATH, payload, files)
    bug_id = extract_bug_id(created)
    created_summary = {"id": bug_id, "num": created.get("num") if isinstance(created, dict) else None, "title": payload["title"]}
    try:
        detail = http_json("GET", BUG_DETAIL_PATH.replace("{id}", bug_id))
        attachments = http_json("GET", BUG_ATTACHMENT_LIST_PATH.replace("{id}", bug_id))
    except SystemExit as exc:
        json_output(
            {
                "created": created_summary,
                "verification": {"completed": False, "error": str(exc), "nextStep": f"请使用 Bug ID {bug_id} 在 MeterSphere 中回读并核验"},
            }
        )
        raise SystemExit(2)

    verification_errors: list[str] = []
    if not isinstance(detail, dict):
        verification_errors.append("缺陷详情回读没有返回对象")
    elif detail.get("title") != payload["title"]:
        verification_errors.append("回读标题与提交标题不一致")
    if not isinstance(attachments, list):
        verification_errors.append("附件回读没有返回数组")
        attachments = []
    else:
        verification_errors.extend(verify_attachments(attachments, files))
    if isinstance(detail, dict):
        verification_errors.extend(
            verify_assignments(detail, (prepared.get("preflight") or {}).get("assigneeAssignments") or [])
        )

    result = {
        "created": {"id": bug_id, "num": detail.get("num") if isinstance(detail, dict) else created_summary["num"], "title": detail.get("title") if isinstance(detail, dict) else payload["title"]},
        "verification": {
            "completed": not verification_errors,
            "titleMatches": isinstance(detail, dict) and detail.get("title") == payload["title"],
            "expectedAttachmentCount": len(files),
            "actualAttachmentCount": len(attachments),
            "assigneeAssignments": (prepared.get("preflight") or {}).get("assigneeAssignments") or [],
            "errors": verification_errors,
        },
    }
    json_output(result)
    if verification_errors:
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MeterSphere 缺陷草稿与提交工具")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="校验输入并生成待确认的缺陷提交预览")
    prepare.add_argument("project_id", help="MeterSphere 项目 ID")
    prepare.add_argument("input", help="原始缺陷 JSON 文件")
    prepare.add_argument("--template", help="缺陷模板 ID；未指定时使用项目默认模板")
    prepare.set_defaults(handler=command_prepare)

    template = sub.add_parser("template", help="查看项目缺陷模板和字段")
    template.add_argument("project_id", help="MeterSphere 项目 ID")
    template.add_argument("--template", help="缺陷模板 ID；未指定时使用项目默认模板")
    template.set_defaults(handler=command_template)

    members = sub.add_parser("members", help="列出模板中的成员字段及可选人员")
    members.add_argument("project_id", help="MeterSphere 项目 ID")
    members.add_argument("--template", help="缺陷模板 ID；未指定时使用项目默认模板")
    members.set_defaults(handler=command_members)

    submit = sub.add_parser("submit", help="提交 prepare 输出的预览文件")
    submit.add_argument("prepared", help="prepare 命令输出的 JSON 文件")
    submit.add_argument("--confirm", action="store_true", help="确认创建 Bug 和上传附件")
    submit.set_defaults(handler=command_submit)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("操作已取消")
