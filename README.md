# MeterSphere Skills for OpenClaw

面向 **OpenClaw Agent** 的 MeterSphere 能力封装。

本项目将 **MeterSphere REST API** 与本地脚本能力整合为一套可复用的 Skills，使 Agent 能够以更稳定、更可控的方式完成以下工作：

- 查询组织、项目、模块、模板、功能用例、接口定义、接口用例
- 根据需求生成并写入 **功能用例**
- 根据 Swagger / OpenAPI 生成并写入 **接口定义 + 接口用例**
- 查询 **用例评审**、评审详情、评审状态、评审人
- 回答“哪些功能用例被评审过”“某条用例关联了多少个缺陷”
- 输出单条功能用例的 **详情 + 缺陷 + 评审记录**

---

## 1. 项目定位

MeterSphere 本身提供完整的测试资产管理能力，但在日常使用中，以下场景往往仍存在较多重复劳动：

- 手工整理需求并编写测试用例
- 反复从 Swagger / OpenAPI 提取接口并录入系统
- 查询单条用例的缺陷、评审、测试计划等关联信息
- 统计“哪些用例被评审过”“哪些用例缺陷更多”
- 在 Agent 场景下临时拼装请求、反复摸索 API 参数

本项目的目标，是把这些高频动作沉淀为：

1. **可触发的 Skill 能力**
2. **可复用的 CLI 命令**
3. **可直接用于用户回复的输出格式**

这样 Agent 不必每次从零构造请求，也不必把大段原始 JSON 直接抛给用户。

---

## 2. 核心能力

### 2.1 查询能力

支持查询：

- 组织 / 项目
- 功能模块 / 功能模板
- API 模块
- 功能用例 / 接口定义 / 接口用例
- 评审单 / 评审详情 / 评审模块 / 评审人
- 单条功能用例的详情、缺陷、评审记录

### 2.2 生成功能用例

支持根据一句需求或需求文档生成：

- 主流程
- 异常场景
- 边界场景
- 基础优先级
- 基础标签

并支持批量写入 MeterSphere。

### 2.3 导入接口定义与接口用例

支持基于 Swagger / OpenAPI 自动生成：

- 接口定义
- 成功场景用例
- 必填缺失场景用例
- 边界场景用例

并支持批量写入 MeterSphere。

### 2.4 用例评审与关联分析

支持回答以下典型问题：

- 哪些功能用例被评审过
- 某条功能用例参与过哪些评审
- 某个评审单下有哪些功能用例
- 某条功能用例关联了多少个缺陷
- 某条功能用例的详情、缺陷、评审记录是什么

---

## 3. 推荐设计原则

本项目采用 **“本地生成 + AI 增强 + 系统写入”** 的混合模式：

- **本地脚本**：负责稳定生成结构、调用真实 API、控制输出格式
- **AI 增强**：负责补场景、润色命名、优化描述与断言
- **系统写入**：负责把最终结果落到 MeterSphere

这样做的好处是：

- 比纯自然语言直写更稳定
- 比纯脚本静态模板更灵活
- 比每次重新摸索接口更高效

---

## 4. 项目结构

```text
metersphere-skills/
├── README.md
├── .env.example
├── install.sh
└── skills/
    ├── SKILL.md
    ├── references/
    │   ├── ms-api.md
    │   ├── ai-functional-case-prompt.md
    │   └── ai-api-bundle-prompt.md
    └── scripts/
        ├── ms.sh
        ├── ms.py
        ├── ms_generate.py
        ├── ms_batch.py
        ├── ms_review_summary.py
        ├── ms_case_report.py
        └── ms_case_report_md.py
```

### 目录说明

- `skills/SKILL.md`：Skill 元信息与 Agent 执行指南
- `skills/references/ms-api.md`：MeterSphere API 参考与能力边界说明
- `skills/references/ai-functional-case-prompt.md`：功能用例增强提示词
- `skills/references/ai-api-bundle-prompt.md`：接口定义 / 接口用例增强提示词
- `skills/scripts/ms.sh`：统一 Shell 入口
- `skills/scripts/ms.py`：基础 Python CLI
- `skills/scripts/ms_generate.py`：本地生成草稿 JSON
- `skills/scripts/ms_batch.py`：批量写入 MeterSphere
- `skills/scripts/ms_review_summary.py`：用例评审汇总脚本
- `skills/scripts/ms_case_report.py`：单用例结构化报告
- `skills/scripts/ms_case_report_md.py`：单用例 Markdown 报告

---

## 5. 安装方式

### 5.1 快速开始

```bash
# 通过 Clawdhub 安装（推荐，自动处理依赖和更新）
clawdhub install metersphere

```

### 5.2 手动安装

```bash

mkdir -p ~/.openclaw/workspace/skills
cp -R ./skills ~/.openclaw/workspace/skills/metersphere

```

### 5.3 使用安装脚本

```bash

./install.sh

```

---

## 6. 环境配置

编辑：

```bash
~/.openclaw/workspace/skills/metersphere/.env
```

最小配置如下：

```bash
METERSPHERE_BASE_URL=https://your-metersphere.example.com
METERSPHERE_ACCESS_KEY=your_access_key
METERSPHERE_SECRET_KEY=your_secret_key
```

### 参数说明

- `METERSPHERE_BASE_URL`：MeterSphere 服务地址
- `METERSPHERE_ACCESS_KEY`：AK
- `METERSPHERE_SECRET_KEY`：SK

---

## 7. 安装后验证

```bash
cd ~/.openclaw/workspace/skills/metersphere

./scripts/ms.sh --help
./scripts/ms.sh organization list
./scripts/ms.sh project list
```

如果以上命令可以返回真实数据，说明基础鉴权与接口访问正常。

---

## 8. 常用命令

### 8.1 基础查询

```bash
./scripts/ms.sh organization list
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh api-module list <projectId>
./scripts/ms.sh functional-case list '<JSON>'
./scripts/ms.sh api list '<JSON>'
./scripts/ms.sh api-case list '<JSON>'
```

### 8.2 用例评审查询

```bash
./scripts/ms.sh functional-case-review list '{"caseId":"<功能用例ID>"}'
./scripts/ms.sh case-review list '{"projectId":"<项目ID>"}'
./scripts/ms.sh case-review get <reviewId>
./scripts/ms.sh case-review-detail list '{"projectId":"<项目ID>","reviewId":"<评审ID>","viewStatusFlag":false}'
./scripts/ms.sh case-review-module list <projectId>
./scripts/ms.sh case-review-user list <projectId>
```

### 8.3 功能用例生成与写入

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/ms.sh functional-case batch-create <json-file>
./scripts/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
```

### 8.4 接口定义 / 接口用例生成与写入

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
./scripts/ms.sh api batch-create <json-file>
./scripts/ms.sh api import-create <projectId> <moduleId> <openapi-file-or-url>
```

### 8.5 高层聚合查询

#### 查询哪些用例被评审过

```bash
./scripts/ms.sh reviewed-summary <projectId>
./scripts/ms.sh reviewed-summary <projectId> 登录
```

#### 查询单条功能用例完整画像（JSON）

```bash
./scripts/ms.sh case-report <projectId> <caseId>
```

返回内容包含：

- `summary`
- `detail`
- `bugs`
- `reviews`

#### 查询单条功能用例完整画像（Markdown）

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

该命令更适合直接回复用户，输出结构为：

1. 用例摘要
2. 前置条件
3. 备注
4. 步骤
5. 缺陷
6. 评审记录

---

## 9. 典型使用场景

### 场景 1：根据需求生成功能用例

```bash
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> ./requirement.txt
```

如果需要更高质量内容：

1. 先生成 JSON 草稿
2. 再用 `references/ai-functional-case-prompt.md` 增强
3. 最后 `batch-create` 写入

### 场景 2：根据 OpenAPI 导入接口测试资产

```bash
./scripts/ms.sh project list
./scripts/ms.sh api-module list <projectId>
./scripts/ms.sh api import-generate <projectId> <moduleId> ./openapi.json
```

如需增强：

1. 先生成 bundle
2. 再用 `references/ai-api-bundle-prompt.md` 增强
3. 最后 `api batch-create`

### 场景 3：判断哪些用例被评审过

```bash
./scripts/ms.sh reviewed-summary <projectId>
```

可直接得到：

- 总用例数
- 已评审用例数
- 未评审用例数
- 每条用例的评审情况

### 场景 4：查看某条功能用例的完整情况

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

适合在聊天场景中直接回答：

- 用例详情
- 关联缺陷
- 评审记录

---

## 10. 推荐工作流

### 10.1 功能用例工作流

1. `project list`
2. `functional-module list <projectId>`
3. `functional-template list <projectId>`
4. `functional-case generate`
5. 按 `references/ai-functional-case-prompt.md` 增强
6. `functional-case batch-create`

### 10.2 接口定义 / 接口用例工作流

1. `project list`
2. `api-module list <projectId>`
3. `api import-generate`
4. 按 `references/ai-api-bundle-prompt.md` 增强
5. `api batch-create`

### 10.3 单用例查询工作流

1. 已知 `caseId` 时，优先 `case-report-md`
2. 需要结构化数据时，再用 `case-report`
3. 只关心评审覆盖时，用 `reviewed-summary`

---

## 11. 输出策略

本项目区分两类输出：

### 11.1 结构化输出

适用于：

- Agent 继续加工
- 脚本联动
- 二次分析

推荐命令：

```bash
./scripts/ms.sh case-report <projectId> <caseId>
./scripts/ms.sh reviewed-summary <projectId> [keyword]
```

### 11.2 面向用户的可读输出

适用于：

- 聊天回复
- 汇总说明
- 单用例说明

推荐命令：

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

---

## 12. 已确认能力边界

当前已验证并可稳定使用的能力包括：

- 组织 / 项目 / 模块 / 模板查询
- 功能用例详情查询
- 功能用例评审查询
- 功能用例关联缺陷查询
- 单用例详情 + 缺陷 + 评审记录聚合
- 功能用例草稿生成与批量写入
- OpenAPI 导入草稿生成与批量写入

当前项目定位仍以：

- **稳定查询**
- **稳定生成草稿**
- **稳定写入系统**

为优先目标。

---

## 13. 参考文件

如需查看更细的接口与提示词说明，请参考：

- `skills/SKILL.md`
- `skills/references/ms-api.md`
- `skills/references/ai-functional-case-prompt.md`
- `skills/references/ai-api-bundle-prompt.md`

---

## 14. 总结

如果你希望 Agent 能够在 MeterSphere 中：

- 更稳地查询测试资产
- 更快地生成测试资产
- 更清楚地回答评审与缺陷问题
- 更自然地输出单用例完整报告

那么这套 Skills 的价值就在于：

> 用统一命令与统一输出格式，把零散的 MeterSphere API 操作，收敛为可复用、可触发、可直接交付的 Agent 能力。