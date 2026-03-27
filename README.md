# MeterSphere Skill for OpenClaw

像与同事沟通一样，通过自然语言与你的 **MeterSphere 测试系统**交互。

功能需求、功能用例、Swagger/OpenAPI、接口定义、接口测试用例 —— 都可以通过这套 Skill 配合 AI 助理完成。

这个项目把 **MeterSphere REST API** 包装进 **OpenClaw Skill**：

1. 你用自然语言描述需求，或提供需求文档 / Swagger 文档
2. AI 识别意图并生成结构化草稿
3. 本地脚本补齐稳定的请求结构
4. 再批量写入 MeterSphere

这套 Skill 当前推荐使用 **本地生成 + AI 增强 + 批量写入** 的混合模式：

- 本地生成负责稳定、可落库
- AI 增强负责补场景、润色、去重、优化断言
- 批量写入负责把最终 JSON 写入 MeterSphere

---

# 为什么这个 Skill 有用

| 系统视角 | 用户意图 | 输出 |
|---|---|---|
| 👂 接收自然语言 / 文档 | 给需求、给 Swagger、给接口说明 | ⚙️ 转成结构化草稿 |
| 🧩 降低重复劳动 | 生成功能用例 / 接口定义 / 接口用例 | ✅ 自动写入 MeterSphere |
| 🤖 本地规则 + AI 协同 | 稳定生成 + 智能提质 | 📈 提高测试资产生产效率 |

---

# 项目结构

```text
metersphere-skills/
├── README.md                  
├── .env.example               # 环境变量示例
├── install.sh                 # 安装脚本
└── skills/
    ├── SKILL.md               # Skill 元数据与 Agent 指南（给 Agent 看）
    ├── references/
    │   ├── ms-api.md                  # MeterSphere API 参考
    │   ├── ai-functional-case-prompt.md
    │   └── ai-api-bundle-prompt.md
    └── scripts/
        ├── ms.sh              # Shell 入口
        ├── ms.py              # Python CLI
        ├── ms_generate.py     # 本地生成草稿 JSON
        └── ms_batch.py        # 批量写入 MeterSphere
```

---

# 快速开始

## 手动安装

```bash
# 进入 OpenClaw 的 skills 目录
mkdir -p ~/.openclaw/workspace/skills

# 将 skills 目录复制进去，目标目录建议命名为 metersphere
cp -R ./skills ~/.openclaw/workspace/skills/metersphere
```

或者直接使用当前仓库中的安装脚本：

```bash
./install.sh
```

---

# 环境配置

编辑：

```bash
~/.openclaw/workspace/skills/metersphere/.env
```

最小配置：

```bash
METERSPHERE_BASE_URL=你的 MeterSphere 实例地址，形如 https://your-metersphere.com
METERSPHERE_ACCESS_KEY=你的AK
METERSPHERE_SECRET_KEY=你的SK
```

---

# 验证

```bash
cd ~/.openclaw/workspace/skills/metersphere

# 查看帮助
./scripts/ms.sh --help

# 查询组织
./scripts/ms.sh organization list

# 查询项目
./scripts/ms.sh project list
```

---

# 主要能力

## 1) 查询组织 / 项目 / 模块 / 模板

```bash
./scripts/ms.sh organization list
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh api-module list <projectId>
```

## 2) 需求 → 功能用例

### 先生成草稿

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
```

### 再批量写入

```bash
./scripts/ms.sh functional-case batch-create <json-file>
```

### 一步直写

```bash
./scripts/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
```

## 3) Swagger/OpenAPI → 接口定义 + 接口用例

### 先生成草稿

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
```

### 再批量写入

```bash
./scripts/ms.sh api batch-create <json-file>
```

### 一步直写

```bash
./scripts/ms.sh api import-create <projectId> <moduleId> <openapi-file-or-url>
```

---

# 推荐工作流

## 功能用例

1. `project list`
2. `functional-module list <projectId>`
3. `functional-template list <projectId>`
4. `functional-case generate`
5. 用 AI 按 `references/ai-functional-case-prompt.md` 增强 JSON
6. `functional-case batch-create`

## 接口定义 / 接口用例

1. `project list`
2. `api-module list <projectId>`
3. `api import-generate`
4. 用 AI 按 `references/ai-api-bundle-prompt.md` 增强 JSON
5. `api batch-create`

---

# 当前实现特点

- 默认支持组织、项目、模块、模板查询
- 功能用例支持主流程 / 异常 / 边界三类草稿生成
- 接口用例支持成功 / 必填缺失 / 边界三类草稿生成
- OpenAPI example/schema 会优先用于填充值
- 基础状态码断言会自动挂载
