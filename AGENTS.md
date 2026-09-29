# metersphere-skills
> 给 AI 编码代理（OpenCode 等）的仓库指引。命令与约定均基于仓库现状核对。

## 这是什么
metersphere-skills 是一个可分发、可安装的 Agent Skill 包：用本地 bash/Python 脚本封装 MeterSphere REST API，让代理能查询/生成/批量写入功能用例、接口定义、接口用例等测试资产。安装目标包括 OpenCode、OpenClaw、Claude Code、Codex、Cursor 等任意支持 Agent Skills 的工具（npx skills add）。

## 目录结构
- README.md — 完整命令参考（zh-CN）
- .gitignore — 忽略 *.env、.token_cache、.idea/
- skills/ — Skill 本体
  - SKILL.md — 代理技能说明书（frontmatter: name=metersphere、environment.required、security 标志）
  - skill-metadata.json — Skill 元数据（name/version/requiredEnvVars/requiredBinaries；npx skills 不读取）
  - references/ — ms-api.md（API 端点参考）+ ai-*-prompt.md（AI 增强提示模板）
  - scripts/ — ms.sh + ms.py + ms_*.py（见下）

## 运行时入口
- **ms.sh 是唯一规范入口**：./scripts/ms.sh <resource> <action> [args]（相对 skills/ 目录）。
- ms.py 是独立 Python CLI（仅 list/get/create/raw），不被 ms.sh 调用；两者并存，勿假设功能一致。
- 辅助脚本：ms_generate.py（本地草稿生成）、ms_batch.py（批量写入）、ms_review_summary.py（评审覆盖统计）、ms_case_report.py（结构化 JSON 报告）、ms_case_report_md.py（Markdown 报告，包装 ms_case_report.py）。

## CLI 语法
- 资源: organization, project, functional-module, functional-template, api-module, functional-case, functional-case-review, case-review, case-review-detail, case-review-module, case-review-user, api, api-case
- 动作: list, get, create, raw GET|POST <path> [json], generate, batch-create, generate-create, import-generate, import-create
- 顶层: reviewed-summary <projectId> [keyword]; case-report <projectId> <caseId>; case-report-md <projectId> <caseId>

## 认证（勿改动签名机制）
- 每请求签名：明文 "{ACCESS_KEY}|{uuid4}|{毫秒时间戳}"，AES-128-CBC 加密，key=hex(SECRET_KEY)，iv=hex(ACCESS_KEY)，命令：openssl enc -aes-128-cbc -K <keyhex> -iv <ivhex> -base64 -A -nosalt。
- 请求头：Content-Type: application/json、accessKey: <ACCESS_KEY>、signature: <加密串>。
- SECRET_KEY 永不出本机。依赖二进制：python3、openssl、curl。

## 环境变量与 .env
- 脚本自动从自身父目录加载 .env（即 skills/.env 或安装后的技能目录）。
- 必填：METERSPHERE_BASE_URL、METERSPHERE_ACCESS_KEY、METERSPHERE_SECRET_KEY。
- 默认值：organizationId=100001、pageSize=20、protocols=["HTTP"]；部分 API 路径可用 METERSPHERE_*_PATH 覆盖（ms.sh 与 ms.py 均支持）。

## ⚠️ 硬编码 ID 陷阱（写入前务必覆盖）
- 脚本含硬编码 projectId=1163437937827840、templateId=1163437937827890、versionId=1163437937827887（属于某个特定项目）。
- ms_batch.py 在环境变量未设置时回退到这些值并告警——数据可能写进错误的项目。
- 写入操作前必须设置 METERSPHERE_PROJECT_ID、METERSPHERE_DEFAULT_TEMPLATE_ID、METERSPHERE_DEFAULT_VERSION_ID 覆盖。

## 标准工作流
1. 先查 ID：project list → functional-module/api-module list → functional-template list
2. 本地生成草稿：functional-case generate <projectId> <moduleId> <templateId> <需求文件>；或 api import-generate <projectId> <moduleId> <openapi 文件或 URL>（JSON/YAML 均可）
3. 用 references/ai-*-prompt.md 模板让模型增强草稿（保持 JSON 结构合法、可直接导入）
4. 批量写入 batch-create；一步到位可用 generate-create / import-create（跳过 AI 增强）

## 输出约定
- 所有文档/帮助/报错为 zh-CN；回复用户用中文。
- 只回关键 ID/名称/状态/计数（如 bugCount、caseReviewCount），不要倾倒原始 JSON（除非用户明确要求）。
- functional-case 创建用 multipart/form-data（curl -F request=@file），不是普通 JSON POST。
- 报告：case-report-md 面向用户、case-report 结构化、reviewed-summary 覆盖率。

## 评审语义
- 用例"已评审" = /functional/case/review/page 返回非空 或 detail.reviewStatus ∈ {PASS, UN_PASS}（ms_review_summary.py 采用后者）。
- 状态枚举: UN_REVIEWED / UNDER_REVIEWED / PASS / UN_PASS。

## 反模式（禁止）
- 不要绕过 ms.sh 手写 curl（签名易错）。
- 不要假设 ms.py 与 ms.sh 功能等价。
- 不要不设 METERSPHERE_PROJECT_ID 就执行写入类命令。