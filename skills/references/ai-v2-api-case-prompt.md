# v2 接口用例 AI 生成 Prompt 模板（Agent 侧流程）

用于 v2 分支的接口用例（api-case）生成。v2 的 api-case 走 **Agent 侧流程**：
先读取接口定义，再按本模板生成接口用例创建体，最后用现有 `api-case create` 分支写入。

## 使用方式

1. 先查接口定义 ID：`./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>"}'`
2. 读取接口定义：`./skills/scripts/v2/ms.sh api get <apiId>`（拿到 method / path / 请求参数 / 响应结构）
3. 把接口定义 JSON 贴给 AI，并附上下面提示词。
4. 将 AI 返回的 JSON 保存为文件，用 `./skills/scripts/v2/ms.sh api-case create '<json>'` 写入。

## Prompt

你现在是资深接口测试工程师。请根据我提供的 MeterSphere v2 接口定义，生成接口用例创建体。

目标：

1. 输出必须是**单个 JSON 对象**（一条接口用例），字段语义对齐 v2 `/api/testcase/create`：
   - `name`（用例标题，如 `获取用户详情-200`）
   - `projectId`（项目 ID，从接口定义中取，不要编造）
   - `apiDefinitionId`（接口定义 ID，从接口定义中取，不要编造）
   - `priority`（优先级，取值只能是 `P0` / `P1` / `P2` / `P3`）
   - 可选：`description`（用例描述）、`tags`（标签数组）、`versionId`（仅当已知时提供）
2. 不要输出服务端自动生成的字段（`id`、`num`、`createTime`、`createUser`、`caseStatus` 等）——创建时由服务端填充。
3. 基于接口定义生成用例，优先覆盖：
   - 成功场景（200）
   - 必填参数缺失
   - 非法类型 / 非法取值
   - 超长 / 边界值
   - 资源不存在
   - 权限不足（如果接口语义明显涉及权限）
4. 用例名称用中文，风格为测试人员写法。
5. 输出必须是**原始 JSON**，不要 markdown 代码块围栏（不要 ```json ... ```），不要解释性文字，确保可直接被 `python3 -m json.tool` 解析。

## 参考：真实 api-case 字段树（来自 `ms.sh api-case get` 实测响应，仅作字段参考，创建体只需 name/projectId/apiDefinitionId/priority）

```json
{
  "id": "<id>",
  "projectId": "<projectId>",
  "name": "<caseName>",
  "priority": "P0",
  "apiDefinitionId": "<apiDefinitionId>",
  "createUserId": "<userId>",
  "updateUserId": "<userId>",
  "createTime": <timestamp>,
  "updateTime": <timestamp>,
  "num": <num>,
  "tags": null,
  "caseStatus": "Underway",
  "versionId": "<versionId>",
  "description": null,
  "request": "null",
  "createUser": "<userName>",
  "updateUser": "<userName>",
  "apiMethod": "GET",
  "active": false,
  "responseActive": false
}
```

## 示例（创建体）

```json
{
  "name": "获取用户详情-200",
  "projectId": "<projectId>",
  "apiDefinitionId": "<apiDefinitionId>",
  "priority": "P1",
  "description": "验证使用有效用户 ID 获取用户详情的成功场景"
}
```