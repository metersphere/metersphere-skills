# 功能用例 AI 增强 Prompt 模板

用于处理 `functional-case generate` 输出的 JSON 草稿。

## 使用方式

把本地生成的 JSON 草稿贴给 AI，并附上下面提示词。

## Prompt

你现在是资深测试分析师，请对我提供的 MeterSphere 功能用例 JSON 草稿做增强和整理。

目标：

1. 保留原有 JSON 结构不变，输出仍然必须是 **JSON 数组**。
2. 不要删除必要字段：
   - `projectId`
   - `templateId`
   - `moduleId`
   - `name`
   - `caseEditType`
3. 优化内容质量：
   - 合并重复用例
   - 去掉明显冗余
   - 让标题更像测试人员写法
   - 让 `textDescription` 更完整
   - 让 `expectedResult` 更具体可验证
4. 尽量补充遗漏场景，尤其是：
   - 主流程
   - 异常流程
   - 边界值
   - 权限校验
   - 空值/非法值
5. 可以调整 `tags`，但不要过多，一般 1-5 个。
6. 不要编造项目 ID、模板 ID、模块 ID。
7. 输出必须是可直接落库的 JSON，不要解释，不要 markdown。

如果草稿中有重复、相似或质量低的用例，请整理成更少但更高质量的一组结果。
