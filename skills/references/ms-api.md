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
- `GET /functional/case/detail/{id}`

其中：

- `functional/case/review/page` 用于判断该用例是否参与过评审
- `functional/case/detail/{id}` 返回详情字段，可直接读取：
  - `bugCount`：该用例关联的缺陷数量
  - `caseReviewCount`：该用例关联的评审数量
  - `testPlanCount`：该用例关联的测试计划数量

若 `functional/case/review/page` 返回列表非空，则该用例**被评审过**；否则可视为**未被评审过**。

### 口径 B：评审单维度

先查：

- `POST /case/review/page`

再对每个评审单查：

- `POST /case/review/detail/page`

可以得到“某个评审单里有哪些用例、每条用例当前评审状态”。

## 9. 当前限制

- 更细粒度 JSONPath 断言仍建议由 AI 增强阶段补充
- 当前本地生成仍以稳定、可落库为优先

## 10. 接口定义导入（fullCoverage）幂等语义与陷阱

> 以下均为现场实测证实的事实（v2.10.26-lts），适用于 `api import-generate` / `api import-create`。

### 双份前缀的来源与覆盖方式

- 接口定义端点实际走 `{BASE}/api/api/definition/...`：路径常量 `METERSPHERE_API_DEFINITION_LIST_PATH` / `_GET_PATH` / `_CREATE_PATH` / `_IMPORT_PATH`（`ms.sh` 内默认值）已包含首段 `/api`，`service_prefix()` 再拼上网关段 `/api`——双份前缀是这两个常量共同产生的结果，不是需要手工拼接的额外规则。
- **单份前缀** `{BASE}/api/definition/get/{id}` 会得到 Spring 404（`{"status":404,"error":"Not Found"}`，无 `success` 键）——不是数据不存在，是路径打错。
- 部署形态不同的环境可用现有 `METERSPHERE_*_PATH` 环境变量覆盖路径常量（`ms.sh` 的 `request()` 第 4 参默认 `api`，传空串 `""` 仍回退为 `api`）。

### fullCoverage 重复导入的幂等语义

- fullCoverage 模式**按 path 去重**：重复导入同一 spec 不会落新定义行，但导入响应 `data.data[]` 返回的是**解析阶段新生成的不可查询 id**（GET 该 id 得 `{"success":true,"data":null}`），不是持久化 id。
- 因此**不能直接消费导入响应里的 id** 去 detail GET / 关联用例——首次导入成功仅因响应 id 恰为持久化 id，重复导入必失败。
- **正确做法（v2 已内置）**：按 name 从 `POST /api/api/definition/list/{goPage}/{pageSize}`（body `{"projectId":...,"protocols":[...]}`）解析持久化 id，再用持久化 id 做 detail GET 与已存在用例预检。同名定义多个时取首个并输出中文警告。
- **勿消费导入响应内联 request**：`apiDefinitionId` 必须来自持久化 id 的 detail，否则用例归属错误。

### name 漂移语义

- spec 中端点 name 变更（path 不变）再导入：fullCoverage 按 path 去重不落新行，但会**更新既有定义的 name**（id/createTime 不变）。
- 此时按 name 解析仍能命中（改名后的定义在列表中），旧用例变体名不匹配新变体名 → 生成新变体用例（EXIT 0）→ 重跑跳过，幂等成立。
- 若 name 在定义列表中完全不存在（如跨项目、列表拉取失败），回退响应 id → detail GET 得 `data:null` → 输出中文诊断并跳过该定义。
