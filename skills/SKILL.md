---
name: metersphere
description: 通过 MeterSphere API 查询项目、模块、模板、功能用例、接口定义、接口用例、用例评审，并支持根据需求生成并写入功能用例、根据 Swagger/OpenAPI 生成并写入接口定义与接口用例。用户提到 MeterSphere、测试用例、功能用例、接口用例、Swagger/OpenAPI 导入、批量写入测试资产、用例评审、评审单、哪些用例被评审过、我的待评审、评审状态统计时使用。
---

# MeterSphere Skills

优先用本 skill 自带脚本，不要临时手写 curl。

## 选择工作流

按任务类型选最短路径：

### 1. 查询类

用于：

- 查组织 / 项目 / 模块 / 模板
- 查功能用例 / 接口定义 / 接口用例
- 查评审单 / 评审详情 / 评审人 / 评审模块
- 回答“哪些用例被评审过”
- 回答“这条用例关联了多少个缺陷 / 哪些用例缺陷最多”

优先命令：

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
```

### 2. 需求 → 功能用例

用于：

- 根据一句需求生成测试用例
- 根据需求文档批量生成功能用例
- 先出草稿，再让 AI 补场景
- 最终写入 MeterSphere

默认流程：

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/ms.sh functional-case batch-create <json-file>
```

需要一步直写时：

```bash
./scripts/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
```

### 3. Swagger / OpenAPI → 接口定义 + 接口用例

用于：

- 根据 Swagger / OpenAPI 导入接口定义
- 自动生成成功 / 必填缺失 / 边界场景接口用例
- 先本地生成，再批量写入

默认流程：

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
./scripts/ms.sh api batch-create <json-file>
```

需要一步直写时：

```bash
./scripts/ms.sh api import-create <projectId> <moduleId> <openapi-file-or-url>
```

## 处理“哪些用例被评审过”

优先用：

```bash
./scripts/ms.sh reviewed-summary <projectId> [keyword]
```

这是最高层入口，直接输出：

- 项目内总用例数
- 已被评审的用例数
- 未被评审的用例数
- 项目内总缺陷关联数 `totalBugLinks`
- 每条功能用例的 `reviewed: true/false`
- 每条功能用例参与过哪些评审单
- 每条功能用例关联了多少个缺陷 `bugCount`

如果用户追问某条用例的评审来源，再补：

```bash
./scripts/ms.sh functional-case-review list '{"caseId":"<功能用例ID>"}'
```

如果用户要看某个评审单里的全部用例状态，再补：

```bash
./scripts/ms.sh case-review-detail list '{"projectId":"<项目ID>","reviewId":"<评审ID>","viewStatusFlag":false}'
```

判断口径：

- `functional-case-review list` 返回非空：该功能用例可视为**被评审过**
- `case-review-detail list` 中每条记录的 `status` 代表该用例在该评审单中的当前状态，如：`UN_REVIEWED` / `UNDER_REVIEWED` / `PASS` / `UN_PASS`

## 默认执行顺序

### 查询项目或模块前

先确认：

1. `project list`
2. 需要时再查 `functional-module list` / `api-module list`

### 生成功能用例前

先确认：

1. 项目 ID
2. 功能模块 ID
3. 模板 ID

命令顺序：

```bash
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
```

### 生成功能用例后

如需提质，再读：

- `references/ai-functional-case-prompt.md`

### 导入 OpenAPI 后

如需补断言、补异常场景、补命名，再读：

- `references/ai-api-bundle-prompt.md`

### 需要确认接口字段 / 路径 / 评审 API 时

再读：

- `references/ms-api.md`

## 本地生成能力边界

### 功能用例草稿

默认能稳定生成：

- 主流程
- 异常场景
- 边界场景
- 基础优先级
- 基础标签

### 接口定义 / 接口用例草稿

默认能稳定生成：

- 1 条接口定义
- 3 条接口用例：成功 / 必填缺失 / 边界
- 基于 example/schema 自动带值
- 基础状态码断言

### 评审与关联查询

默认能稳定回答：

- 有哪些评审单
- 某条功能用例是否参与过评审
- 某个评审单下有哪些功能用例
- 当前评审状态统计
- 哪些用例已评审 / 未评审
- 某条功能用例关联了多少个缺陷
- 哪些功能用例的缺陷关联数更多

## 环境变量

只依赖最小三项：

```bash
METERSPHERE_BASE_URL=
METERSPHERE_ACCESS_KEY=
METERSPHERE_SECRET_KEY=
```

## 输出要求

回答 MeterSphere 查询结果时，优先输出：

- 关键 ID
- 名称
- 状态
- 下一步可执行命令

不要把大段原始 JSON 一股脑全贴给用户，除非用户明确要原始返回。