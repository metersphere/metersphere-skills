---
name: metersphere
description: MeterSphere Skills 实现自动从需求生成功能用例，自动解析 Swagger 或其他 API 文档，生成并录入接口测试用例到 MeterSphere 系统，打通需求、测试与开发，全面提升需求到测试的自动化与效率。
---

# MeterSphere Skills

## 何时使用

当用户提到以下任一需求时触发：

- MeterSphere
- 功能用例查询 / 创建
- 根据需求生成测试用例
- Swagger / OpenAPI 导入接口
- 生成接口测试用例
- 批量写入测试资产到 MeterSphere

## 首选工作流

优先使用三段式：

1. **本地生成草稿**
2. **AI 增强草稿**
3. **批量写入系统**

原因：

- 本地生成更稳，结构更可靠
- AI 更适合做补场景、润色、去重、增强断言
- 批量写入更可控

## 可用命令

### 查询辅助

```bash
./scripts/ms.sh organization list
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh api-module list <projectId>
```

### 功能用例

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/ms.sh functional-case batch-create <json-file>
./scripts/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
```

AI 增强模板：

```text
references/ai-functional-case-prompt.md
```

### 接口定义 / 接口用例

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
./scripts/ms.sh api batch-create <json-file>
./scripts/ms.sh api import-create <projectId> <moduleId> <openapi-file-or-url>
```

AI 增强模板：

```text
references/ai-api-bundle-prompt.md
```

## 本地生成能力摘要

### 功能用例草稿

默认生成：

- 主流程
- 异常场景
- 边界场景
- 基础优先级 / 标签

### 接口定义 / 接口用例草稿

默认生成：

- 1 条接口定义
- 3 条接口用例：成功 / 必填缺失 / 边界
- 优先读取 example/schema 带值
- 自动挂基础状态码断言

## 环境变量

只依赖最小三项：

```bash
METERSPHERE_BASE_URL=
METERSPHERE_ACCESS_KEY=
METERSPHERE_SECRET_KEY=
```

## 参考文件

需要补字段、路径、模板时再读：

- `references/ms-api.md`
- `references/ai-functional-case-prompt.md`
- `references/ai-api-bundle-prompt.md`
