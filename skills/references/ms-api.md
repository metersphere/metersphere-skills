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

## 10. 缺陷提交 API（MeterSphere v3.x 已核对）

本节以 MeterSphere v3.x 源码为准。路由定义见 [前端请求常量](https://github.com/metersphere/metersphere/blob/v3.x/frontend/src/api/requrls/bug-management.ts)，控制器和字段校验见 [BugController](https://github.com/metersphere/metersphere/blob/v3.x/backend/services/bug-management/src/main/java/io/metersphere/bug/controller/BugController.java) 与 [BugEditRequest](https://github.com/metersphere/metersphere/blob/v3.x/backend/services/bug-management/src/main/java/io/metersphere/bug/dto/request/BugEditRequest.java)。内容根据源码整理和改写。

### 获取模板和可指派人员

```http
GET /bug/template/option/{projectId}
POST /bug/template/detail
Content-Type: application/json

{"projectId":"<projectId>","id":"<templateId>"}
```

`/bug/template/option` 返回项目可用模板，脚本选择 `enableDefault: true` 的项；如果没有默认项，调用者必须提供模板 ID。`/bug/template/detail` 返回 `customFields`。其中 `type` 为 `MEMBER` 或 `MULTIPLE_MEMBER` 的字段包含可用成员 `options`，应使用其稳定 `value` 作为处理人值，而不是按姓名猜测。

### 创建缺陷并上传附件

```http
POST /bug/add
Content-Type: multipart/form-data

request: application/json
files: <file>     # 可重复，附件字段名必须为 files
```

`request` 至少包含：

```json
{
  "projectId": "<projectId>",
  "templateId": "<templateId>",
  "title": "优化后的缺陷标题",
  "description": "<h3>前置条件</h3><p>...</p>",
  "tags": ["可选标签"],
  "customFields": [
    {
      "id": "<fieldId>",
      "name": "<fieldName>",
      "type": "MEMBER",
      "value": "<处理人 userId>",
      "text": "<处理人显示名>"
    }
  ]
}
```

`projectId` 和 `templateId` 是创建必填字段。项目模板声明为必填的自定义字段也必须传递。前端创建流程将 `request` 作为 JSON Blob，同时用重复的 `files` 表单字段传递本地附件，参见 [前端 uploadFile 实现](https://github.com/metersphere/metersphere/blob/v3.x/frontend/src/api/http/Axios.ts)。返回对象中包含新缺陷 `id`。每张图片的优化说明不是独立附件字段，应写入 `description` 的“附图”段落，并与 `files` 的顺序一一对应。

### 回读验证

```http
GET /bug/get/{id}
GET /bug/attachment/list/{id}
```

创建后应回读详情的 `title`，以及附件列表数量。若标题或附件数不符合提交内容，调用方必须报告部分失败，不能宣称提交成功。

### 指派边界

MeterSphere v3.x 的缺陷创建接口没有独立的“assign”端点；处理人由缺陷模板的成员类型自定义字段写入。不同项目的字段 ID、字段名称、必填规则和候选成员都可能不同，因此 Skill 先读取模板再匹配输入。若模板不存在成员字段，Skill 不会伪造处理人字段或调用未确认的接口。

### CLI 工作流

```bash
./scripts/ms.sh bug members <projectId>
# 用 references/ai-bug-prompt.md 将原始描述整理为 raw-bug.json
./scripts/ms.sh bug prepare <projectId> ./raw-bug.json > ./prepared-bug.json
# 审核预览并获取明确确认后：
./scripts/ms.sh bug submit ./prepared-bug.json --confirm
```

创建接口需具备 `PROJECT_BUG_ADD` 权限；模板读取和回读接口需具备 `PROJECT_BUG_READ` 权限。附件由创建请求一次上传，不需要预先调用 `/bug/attachment/upload`。

### 传输安全与预览完整性

Skill 默认拒绝 `http://` 的 `METERSPHERE_BASE_URL`。可信内网实例如必须使用 HTTP，必须显式设置 `METERSPHERE_ALLOW_INSECURE_HTTP=true`；这会以明文传输动态签名、缺陷内容和附件。`prepare` 会为请求 JSON 与每个附件计算 SHA-256 完整性摘要；`submit` 在发起写操作前会重新计算，预览文件或附件变化时拒绝提交，要求重新生成并审核。
