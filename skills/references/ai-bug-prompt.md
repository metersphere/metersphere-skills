# 缺陷提交 AI 优化 Prompt 模板

用于处理用户提供的原始缺陷信息。在调用 `bug prepare` 前，把原始内容整理成下面的 JSON；之后必须用 `bug prepare` 取得项目模板、校验必填字段，并生成待确认预览。

## 目标

将零散的缺陷描述整理成可复现、可验证、可分派的缺陷草稿。优化对象包括：标题、前置条件、复现步骤、实际结果、预期结果，以及每张截图的说明。

## 输入 JSON

```json
{
  "title": "原始标题或问题描述",
  "prerequisite": "前置条件",
  "steps": ["步骤一", "步骤二"],
  "actualResult": "实际观察到的结果",
  "expectedResult": "预期应出现的结果",
  "environment": "版本、浏览器、设备、账号权限等环境信息",
  "severity": "可选。填写目标模板中的严重程度选项文本或 ID",
  "assignee": "可选。填写目标模板成员字段中的处理人显示名或用户 ID",
  "tags": ["可选标签"],
  "attachments": ["./screenshots/bug.png"],
  "attachmentCaptions": ["登录后点击保存时，页面显示服务端错误提示"],
  "customFields": {
    "模板中无法自动识别的必填 fieldId": "对应值"
  }
}
```

## Prompt

你是一名资深测试工程师。请将用户提供的原始缺陷信息整理成一个**严格符合输入 JSON 结构的 JSON 对象**，不要输出 Markdown 或解释。

要求：

1. `title` 使用“功能/场景 + 操作/条件 + 可观察异常”的形式，简洁、唯一，不超过 255 个字符。
2. `prerequisite` 只写复现所需的账号、权限、数据、配置和环境。未知信息留空，不得虚构。
3. `steps` 按实际执行顺序拆分，每一步只有一个动作。不能确认的步骤不要补写。
4. `actualResult` 只写已经发生的页面表现、接口返回、日志或数据结果。
5. `expectedResult` 写出可检查的正确行为。不要使用“正常”“符合预期”等不可验证表述。
6. `environment` 保留用户给出的版本、浏览器、系统、设备、账号权限和网络信息。缺失时留空。
7. `severity` 与 `assignee` 只有在用户明确提供，或已经从 MeterSphere 模板选项中确认其合法值时才填写。不要臆测人员、优先级或严重程度。
8. `attachments` 必须保留用户提供的每个文件路径，顺序不变。不要伪造附件路径。
9. `attachmentCaptions` 可选；提供时必须与 `attachments` 一一对应、顺序一致。每项只描述对应截图能证明的异常，不得杜撰截图中没有的信息。
10. `customFields` 仅保留用户提供的模板字段值。不要编造字段 ID。
11. 不要改变 `projectId`、`templateId` 等系统标识。如果输入没有这些字段，不要添加。
12. 不要把密码、令牌、Cookie、身份证号、手机号等敏感信息写入标题、正文或截图说明。用 `[已脱敏]` 标记已知敏感数据。

## 创建前的强制流程

1. 先执行 `./scripts/ms.sh bug members <projectId>`，确认可分派人员和其稳定 ID。
2. 让 AI 按上述 Prompt 生成 `raw-bug.json`。
3. 执行 `./scripts/ms.sh bug prepare <projectId> ./raw-bug.json > ./prepared-bug.json`。
4. 展示 `prepared-bug.json` 中的标题、前置条件、步骤、实际/预期结果、附件说明和指派对象。
5. 只有用户明确确认后，才执行 `./scripts/ms.sh bug submit ./prepared-bug.json --confirm`。

`submit --confirm` 会向 MeterSphere 创建缺陷并上传附件。脚本会回读缺陷详情及附件列表，验证标题和附件数量。
