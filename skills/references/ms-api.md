# MeterSphere API 参考（混合模式版）

## 1. 推荐策略

推荐采用三段式：

1. **本地生成 JSON 草稿**
2. **AI 模型增强草稿**
3. **批量写入 MeterSphere**

## 2. 真实鉴权

请求头：

```http
accessKey: <AK>
signature: <动态签名>
```

## 3. 功能用例混合流程

### 生成草稿

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
```

### AI 增强模板

```text
references/ai-functional-case-prompt.md
```

### 批量写入

```bash
./scripts/ms.sh functional-case batch-create <json-file>
```

## 4. 接口定义 / 接口用例混合流程

### 生成草稿 bundle

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
```

### AI 增强模板

```text
references/ai-api-bundle-prompt.md
```

### 批量写入

```bash
./scripts/ms.sh api batch-create <json-file>
```

## 5. 当前本地生成能力

### 功能用例
- 主流程
- 异常场景
- 边界场景
- 基础优先级 / 标签

### 接口用例
- 成功场景（200）
- 必填缺失（400）
- 边界场景（200）
- example/schema 自动带值
- 基础状态码断言自动挂载

## 6. 查询辅助接口

- `POST /system/organization/list`
- `GET /project/list/options/{organizationId}`
- `GET /functional/case/module/tree/{projectId}`
- `GET /functional/case/default/template/field/{projectId}`
- `POST /api/definition/module/tree`

## 7. 功能用例评审相关接口

已确认可用的 case-management 评审相关接口包括：

- `POST /functional/case/review/page`
  - 从**功能用例视角**查询它参与过哪些评审
  - 适合回答：某条用例有没有被评审过
- `POST /case/review/page`
  - 查询项目下评审单列表
  - 返回 `reviewedCount / unReviewCount / underReviewedCount / passCount / unPassCount`
- `GET /case/review/detail/{id}`
  - 查询单个评审单详情
- `POST /case/review/detail/page`
  - 查询某评审单下已关联的功能用例列表
  - 每条记录包含 `status / myStatus / reviewers / reviewNames`
- `GET /case/review/module/tree/{projectId}`
  - 查询评审模块树
- `GET /case/review/user-option/{projectId}`
  - 查询具备评审权限的用户列表
- `GET /case/review/detail/reviewer/status/{reviewId}/{caseId}`
- `GET /case/review/detail/reviewer/status/total/{reviewId}/{caseId}`
  - 查询单条用例在评审中的人和状态汇总
- `GET /review/functional/case/get/list/{reviewId}/{caseId}`
  - 查询单条用例在某次评审中的评审历史

## 8. 如何判断“哪些用例被评审过”

推荐两种口径：

### 口径 A：功能用例维度（最适合用户问答）

对项目下每条功能用例调用：

- `POST /functional/case/review/page`

若返回列表非空，则该用例**被评审过**；否则可视为**未被评审过**。

### 口径 B：评审单维度

先查：

- `POST /case/review/page`

再对每个评审单查：

- `POST /case/review/detail/page`

可以得到“某个评审单里有哪些用例、每条用例当前评审状态”。

## 9. 当前限制

- 更细粒度 JSONPath 断言仍建议由 AI 增强阶段补充
- 当前本地生成仍以稳定、可落库为优先
