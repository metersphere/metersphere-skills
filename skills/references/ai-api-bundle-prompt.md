# 接口定义 / 接口用例 AI 增强 Prompt 模板

用于处理 `api import-generate` 输出的 bundle JSON 草稿。

## 使用方式

把本地生成的 bundle JSON 草稿贴给 AI，并附上下面提示词。

## Prompt

你现在是资深接口测试工程师，请对我提供的 MeterSphere 接口定义 / 接口用例 bundle JSON 做增强。

目标：

1. 保持原始 JSON 结构不变：
   - 顶层仍为对象
   - 保留 `definitions`
   - 保留 `cases`
2. 不删除必要字段：
   - 接口定义中的 `projectId` / `moduleId` / `name` / `protocol` / `status` / `request` / `response`
   - 接口用例中的 `name` / `priority` / `status` / `request`
3. 允许增强：
   - 优化接口定义名称
   - 优化接口用例名称
   - 增加更合理的反例
   - 增强边界场景
   - 删除明显重复的 case
4. 优先补充这些测试思路：
   - 成功场景
   - 必填缺失
   - 非法类型
   - 超长 / 边界值
   - 资源不存在
   - 权限不足（如果接口语义明显涉及权限）
5. 可以增强断言：
   - 保留已有状态码断言
   - 如果响应结构明确，可补 JSONPath 断言
6. 不要破坏 MeterSphere request 结构。
7. 输出必须是可直接用于批量写入的 JSON，不要解释，不要 markdown。

请在保证 JSON 可落库的前提下，尽可能提升测试覆盖质量。
