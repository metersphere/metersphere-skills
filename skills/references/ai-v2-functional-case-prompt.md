# v2 功能用例 AI 增强 Prompt 模板

用于处理 v2 分支 `functional-case generate`（`skills/scripts/v2/ms_generate.py`）输出的 JSON 草稿。
v2 与 v3 的字段不同：v2 使用 `nodeId` / `nodePath`（模块树），不使用 `moduleId` / `templateId`（模板可选）。

## 使用方式

1. 运行 `./skills/scripts/v2/ms.sh functional-case generate <projectId> <moduleId> <templateId> <需求文件>` 得到 JSON 草稿。
2. 把草稿 JSON 贴给 AI，并附上下面提示词。
3. 将 AI 返回的 JSON 数组保存为文件，用 `functional-case batch-create` 写入。

## Prompt

你现在是资深测试分析师，请对我提供的 MeterSphere v2 功能用例 JSON 草稿做增强和整理。

目标：

1. 保留原有 JSON 结构不变，输出仍然必须是 **JSON 数组**，每个元素是一个功能用例对象。
2. 不要删除必要字段，且字段名必须与草稿完全一致：
   - `name`（用例标题，测试人员写法）
   - `projectId`（项目 ID，不要编造）
   - `nodeId`（模块 ID，不要编造）
   - `nodePath`（模块路径，如 `/默认模块/登录`，不要编造）
   - `priority`（优先级，取值只能是 `P0` / `P1` / `P2` / `P3`）
   - `steps`（JSON 数组，每项为 `{"num": 序号, "desc": 步骤描述, "result": 预期结果}`）
   - `caseEditType`（固定为 `"STEP"`）
3. 可选字段仅在草稿中出现时保留，不要新增：
   - `description`（用例描述）
   - `precondition`（前置条件）
   - `remark`（备注）
   - `templateId` / `versionId`（仅当草稿中已提供时保留，不要自行编造）
4. 不要输出 v3 专属字段（如 `moduleId`、`customNum`、`maintainer`、`customFields`、`aiCreate` 等）。
5. 优化内容质量：
   - 合并重复用例，去掉明显冗余
   - 让标题更像测试人员写法
   - 让 `description` / `precondition` 更完整
   - 让每个步骤的 `desc` 具体可执行、`result` 具体可验证
6. 尽量补充遗漏场景，尤其是：
   - 主流程
   - 异常流程
   - 边界值
   - 权限校验
   - 空值 / 非法值
7. 所有内容（标题、描述、步骤、预期结果）使用**中文**。
8. 输出必须是**原始 JSON**，不要 markdown 代码块围栏（不要 ```json ... ```），不要解释性文字，确保可直接被 `python3 -m json.tool` 解析。

如果草稿中有重复、相似或质量低的用例，请整理成更少但更高质量的一组结果。

## 示例（单个用例对象，字段与 v2 草稿一致）

```json
{
  "name": "用户登录-主流程",
  "projectId": "<projectId>",
  "nodeId": "<nodeId>",
  "nodePath": "/默认模块/登录",
  "priority": "P0",
  "steps": [
    {"num": 0, "desc": "准备测试环境，确认系统正常运行", "result": "环境准备就绪"},
    {"num": 1, "desc": "输入正确的用户名和密码，点击登录", "result": "登录成功，跳转至首页"},
    {"num": 2, "desc": "验证登录状态与页面展示", "result": "页面展示正确，会话已建立"}
  ],
  "caseEditType": "STEP",
  "description": "验证用户使用正确凭据登录的主流程",
  "precondition": "用户已注册账号且系统正常运行",
  "remark": "根据需求自动生成的功能用例，优先级=P0"
}
```