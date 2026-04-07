---
name: metersphere
description: 本项目将 MeterSphere REST API 与本地脚本能力整合,为 OpenClaw Agent 提供了一套高效、可复用的 Skills,支持自动生成功能用例、接口定义及接口用例,查询组织、项目、模块、用例评审与缺陷关联等信息,简化了测试资产管理流程,提升了团队的自动化效率。
environment:
  required:
    - METERSPHERE_BASE_URL
    - METERSPHERE_ACCESS_KEY
    - METERSPHERE_SECRET_KEY
  optional: []
security:
  requiresSecrets: true
  sensitiveEnvironment: true
  externalNetworkAccess: true
  notes: 此技能需要访问 MeterSphere API，使用 ACCESS_KEY 和 SECRET_KEY 进行身份验证。请确保只向可信的 METERSPHERE_BASE_URL 发送请求。

---

# MeterSphere Skills

优先用本 skill 自带脚本,不要临时手写 curl。

## 选择工作流

按任务类型选最短路径:

### 1. 查询类

用于:

- 查组织 / 项目 / 模块 / 模板
- 查功能用例 / 接口定义 / 接口用例
- 查评审单 / 评审详情 / 评审人 / 评审模块
- 回答"哪些用例被评审过"
- 回答"这条用例关联了多少个缺陷 / 哪些用例缺陷最多"
- 当用户查询某个功能用例时,返回:用例详情 + 缺陷 + 评审记录

优先命令:

```bash
./scripts/ms.sh organization list
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh api-module list <projectId>
./scripts/ms.sh functional-case list '<JSON>'
./scripts/ms.sh api list '<JSON>'
./scripts/ms.sh api-case list '<JSON>'
./scripts/ms.sh functional-case-review list '{"caseId":"<功能用例ID>"}'
./scripts/ms.sh case-review list '{"projectId":"<项目ID>"}'
./scripts/ms.sh case-review get <reviewId>
./scripts/ms.sh case-review-detail list '{"projectId":"<项目ID>","reviewId":"<评审ID>","viewStatusFlag":false}'
./scripts/ms.sh case-review-module list <projectId>
./scripts/ms.sh case-review-user list <projectId>
./scripts/ms.sh reviewed-summary <projectId> [keyword]
./scripts/ms.sh case-report <projectId> <caseId>
./scripts/ms.sh case-report-md <projectId> <caseId>
```

### 2. 需求 → 功能用例

用于:

- 根据一句需求生成测试用例
- 根据需求文档批量生成功能用例
- 先出草稿,再让 AI 补场景
- 最终写入 MeterSphere

默认流程:

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/ms.sh functional-case batch-create <json-file>
```

需要一步直写时:

```bash
./scripts/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
```

### 3. Swagger / OpenAPI → 接口定义 + 接口用例

用于:

- 根据 Swagger / OpenAPI 导入接口定义
- 自动生成成功 / 必填缺失 / 边界场景接口用例
- 先本地生成,再批量写入

默认流程:

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
./scripts/ms.sh api batch-create <json-file>
```

需要一步直写时:

```bash
./scripts/ms.sh api import-create <projectId> <moduleId> <openapi-file-or-url>
```

## 处理"哪些用例被评审过"

优先用:

```bash
./scripts/ms.sh reviewed-summary <projectId> [keyword]
```

这是最高层入口,直接输出:

- 项目内总用例数
- 已被评审的用例数
- 未被评审的用例数
- 项目内总缺陷关联数 `totalBugLinks`
- 每条功能用例的 `reviewed: true/false`
- 每条功能用例参与过哪些评审单
- 每条功能用例关联了多少个缺陷 `bugCount`

如果用户直接问某条功能用例,优先用:

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

如果需要结构化 JSON 再用:

```bash
./scripts/ms.sh case-report <projectId> <caseId>
```

其中 Markdown 版更适合直接回复用户;JSON 版更适合继续加工。

`case-report` 返回四块:

- `summary`:用例基础信息、缺陷数、评审数、测试计划数、需求数
- `detail`:前置条件、备注、步骤、标签、附件
- `bugs`:已关联缺陷列表
- `reviews`:评审记录列表

如果用户追问某条用例的评审来源,再补:

```bash
./scripts/ms.sh functional-case-review list '{"caseId":"<功能用例ID>"}'
```

如果用户要看某个评审单里的全部用例状态,再补:

```bash
./scripts/ms.sh case-review-detail list '{"projectId":"<项目ID>","reviewId":"<评审ID>","viewStatusFlag":false}'
```

判断口径:

- `functional-case-review list` 返回非空:该功能用例可视为**被评审过**
- `case-review-detail list` 中每条记录的 `status` 代表该用例在该评审单中的当前状态,如:`UN_REVIEWED` / `UNDER_REVIEWED` / `PASS` / `UN_PASS`
- `functional/case/detail/{id}` 中的 `bugCount` 代表该用例当前关联缺陷数

## 默认执行顺序

### 查询项目或模块前

先确认:

1. `project list`
2. 需要时再查 `functional-module list` / `api-module list`

### 生成功能用例前

先确认:

1. 项目 ID
2. 功能模块 ID
3. 模板 ID

命令顺序:

```bash
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
```

### 生成功能用例后

如需提质,再读:

- `references/ai-functional-case-prompt.md`

### 导入 OpenAPI 后

如需补断言、补异常场景、补命名,再读:

- `references/ai-api-bundle-prompt.md`

### 需要确认接口字段 / 路径 / 评审 API 时

再读:

- `references/ms-api.md`

## 本地生成能力边界

### 功能用例草稿

默认能稳定生成:

- 主流程
- 异常场景
- 边界场景
- 基础优先级
- 基础标签

### 接口定义 / 接口用例草稿

默认能稳定生成:

- 1 条接口定义
- 3 条接口用例:成功 / 必填缺失 / 边界
- 基于 example/schema 自动带值
- 基础状态码断言

### 评审与关联查询

默认能稳定回答:

- 有哪些评审单
- 某条功能用例是否参与过评审
- 某个评审单下有哪些功能用例
- 当前评审状态统计
- 哪些用例已评审 / 未评审
- 某条功能用例关联了多少个缺陷
- 某个功能用例的详情、缺陷、评审记录
- 哪些功能用例的缺陷关联数更多

## 环境变量

### 必需环境变量
```bash
METERSPHERE_BASE_URL=          # MeterSphere 实例地址(如:http://172.16.200.18:8081)
METERSPHERE_ACCESS_KEY=        # API 访问密钥
METERSPHERE_SECRET_KEY=        # API 密钥(用于本地签名,不传输)
```

### 可选环境变量
```bash
METERSPHERE_PROJECT_ID=        # 默认项目 ID
METERSPHERE_ORGANIZATION_ID=100001  # 默认组织 ID
METERSPHERE_HEADERS_JSON=      # 额外的 HTTP 头(JSON 格式,谨慎使用)
METERSPHERE_PROTOCOLS_JSON='["HTTP"]'  # 支持的协议
METERSPHERE_DEFAULT_TEMPLATE_ID= # 默认模板 ID (避免使用硬编码值)
METERSPHERE_DEFAULT_VERSION_ID=  # 默认版本 ID (避免使用硬编码值)
```

### 依赖要求
- `python3`:运行辅助脚本和数据处理
- `openssl`:本地生成请求签名(不传输密钥)
- `curl`:发送 HTTP 请求到 MeterSphere API

## 输出要求

回答 MeterSphere 查询结果时，优先输出：

- 关键 ID
- 名称
- 状态
- 计数信息（如 `bugCount` / `caseReviewCount`）
- 下一步可执行命令

如果是"单条功能用例查询"，优先按这个顺序整理：

1. 用例摘要
2. 前置条件 / 描述 / 步骤
3. 缺陷列表
4. 评审记录

不要把大段原始 JSON 一股脑全贴给用户，除非用户明确要原始返回。

## 安全注意事项

### 1. 凭证范围
- 仅提供具有最小必要权限的 MeterSphere 测试账户凭证
- 建议使用只读 API 密钥进行查询操作
- 为创建操作使用单独的、有限权限的密钥

### 2. 环境变量安全
- `.env` 文件应仅包含必要的环境变量
- 避免在 `.env` 中存放额外敏感信息
- `METERSPHERE_HEADERS_JSON` 可注入任意 HTTP 头，请谨慎使用

### 3. 外部二进制文件
- 脚本会调用 `openssl`、`curl` 和 `python3`
- 确保这些二进制文件来自受信任的来源
- 签名逻辑在本地使用 `SECRET_KEY`，不传输密钥

### 4. 硬编码 ID 警告
- 脚本中包含硬编码的项目 ID（`1163437937827840`）、模板 ID（`1163437937827890`）和版本 ID（`1163437937827887`）
- 这些值对应特定项目，如果未正确配置环境变量，数据可能被错误归属到错误的项目
- 强烈建议设置以下环境变量来覆盖硬编码值：
  - `METERSPHERE_DEFAULT_TEMPLATE_ID`
  - `METERSPHERE_DEFAULT_VERSION_ID`
- 在使用前检查并替换为正确的项目 ID

### 5. 首次使用建议
1. 复制 `.env.example` 为 `.env` 并填写实际值
2. 在非生产环境或沙箱中测试
3. 使用最小权限的凭证
4. 检查网络流量，确认只连接到预期的 `BASE_URL`
5. 验证硬编码的 ID 值是否符合你的项目
6. 设置 `METERSPHERE_DEFAULT_TEMPLATE_ID` 和 `METERSPHERE_DEFAULT_VERSION_ID` 环境变量来覆盖硬编码值
7. 注意脚本中的警告信息，确保数据被正确归属到目标项目