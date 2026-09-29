# v2 模块接口用例生成 Prompt 模板（模块枚举 → 接口用例）

用于 v2 分支的接口用例（api-case）生成。工作流：按项目名 + 子模块名解析 ID，枚举模块内全部已有 HTTP 接口定义，先确定性批量生成基础用例，再由 AI 补充增强变体。

## 使用方式

1. 解析项目 ID：`./skills/scripts/v2/ms.sh project list '<workspaceId>'`（v2 用工作空间，无组织概念；按 name 字段匹配项目名，0 个或多个匹配时告警）
2. 解析模块 ID：`./skills/scripts/v2/ms.sh api-module list '<projectId>'`（遍历模块树 JSON，按 name 匹配子模块名，0 个或多个匹配时告警）
3. 枚举模块内接口定义：`./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>","protocols":["HTTP"]}'`
4. 确定性批量生成：`./skills/scripts/v2/ms.sh api-case generate-create '<projectId>' <definitionId>...`（显式列出全部 definitionId）
5. 对覆盖不足的定义，把 `./skills/scripts/v2/ms.sh api get <definitionId>` 的 JSON 贴给 AI，附上下面提示词，生成增强用例
6. 将 AI 返回的 JSON 用 `./skills/scripts/v2/ms.sh api-case create '<json>'` 写入，一次一条

## Prompt

你现在是资深接口测试工程师。请按以下流程，为指定模块的全部已有 HTTP 接口生成接口用例。

**步骤 0：名称 → ID 推导**

1. 用 `./skills/scripts/v2/ms.sh project list '<workspaceId>'` 列出项目，按 `name` 字段匹配目标项目名，得到 `projectId`。0 个匹配说明项目名写错或 workspaceId 不对；多个匹配说明项目名不唯一，需人工确认，不要擅自选一个。
2. 用 `./skills/scripts/v2/ms.sh api-module list '<projectId>'` 列出模块树，遍历 JSON 按 `name` 匹配目标子模块名，得到 `moduleId`。0 个匹配说明模块名写错；多个匹配说明模块名不唯一，需人工确认。

**步骤 1：枚举模块内已有接口定义**

用 `./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>","protocols":["HTTP"]}'` 列出项目内全部 HTTP 接口定义，按模块过滤出目标模块的定义，得到 definitionId 列表。

- 若列表接口支持 `moduleId` / `keyword` 过滤键，可带上缩小范围。
- 若 `moduleId` 键不受支持或过滤结果为空，回退方案：对每个定义执行 `./skills/scripts/v2/ms.sh api get <definitionId>` 读取详情，客户端按模块名 / 路径过滤。

## 用例构建流程（复用）

**确定性基础用例（批量生成写入）**

对已枚举出的每个接口定义，执行：

`./skills/scripts/v2/ms.sh api-case generate-create '<projectId>' <definitionId1> <definitionId2> ...`

- 必须把目标模块的**全部 definitionId 显式列出**，不要省略。省略 definitionId 会对整个项目生成用例，超出目标模块范围。
- 每个定义生成 3 个变体：
  - `*成功场景`：断言 200，优先级 P1
  - `*必填缺失`：首个必填 query/rest 参数置空，断言 400，优先级 P1（仅当存在必填参数）
  - `*边界场景`：首个字符串参数 = 128 个 'x'，断言 200，优先级 P2（仅当存在字符串参数）
- 覆盖说明：v2 将 query 参数存储在 `arguments` 字段（非 `query`），变体扫描 `query` / `rest`。因此参数存于 `arguments` 或仅 body 必填的定义只会生成 `*成功场景`，缺少必填缺失与边界覆盖，这类定义必须交给下面的 AI 增强步骤补偿。

**AI 增强变体（逐条创建）**

对确定性步骤中覆盖不足的定义（只有 `*成功场景`，或需求要求更多场景），执行：

1. 读取定义详情：`./skills/scripts/v2/ms.sh api get <definitionId>`，拿到 method / path / 请求参数 / 响应结构。
2. 把定义 JSON 贴给 AI，附上 `skills/references/ai-v2-api-case-prompt.md` 的字段契约，生成增强用例，覆盖：
   - 非法类型（如字符串字段传数字）
   - 非法取值（如枚举外取值）
   - 资源不存在（如不存在的 ID）
   - 权限不足（仅当接口语义明显涉及权限）
3. 每条用例用 `./skills/scripts/v2/ms.sh api-case create '<json>'` 写入，一次一条。

**去重与重跑**

- 写入前先查：`./skills/scripts/v2/ms.sh api-case list '{"projectId":"<projectId>","apiDefinitionId":"<definitionId>"}'`。
- 若目标用例名已存在，跳过不重复创建；重跑同一流程时同样先查后写，保证幂等。

**写入安全**

- 所有写入命令必须显式传 `<projectId>`，或确保环境变量 `METERSPHERE_PROJECT_ID` 已导出。
- 未设置时脚本会拒绝执行并退出（exit 1），不要绕过。

**输出规则**

- 输出必须是**原始 JSON**，不要 markdown 代码块围栏（不要 json 围栏），不要解释性文字，确保可直接被 `python3 -m json.tool` 解析。
- 用例名称用中文，风格为测试人员写法（如 `获取用户详情-200`）。
- 创建体只包含 `name` / `projectId` / `apiDefinitionId` / `priority`（可选 `description` / `tags` / `versionId`），不要输出服务端自动生成的字段（`id`、`num`、`createTime`、`createUser`、`caseStatus` 等）。

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