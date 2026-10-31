# AI 智能考试系统（AI Exam System）

上海师范大学软件工程课程项目。面向高校课程场景的 AI 辅助主观题考试系统：教师建题组卷并发布考试，学生在线上作答，系统调用大模型完成主观题初评，教师进行最终复核。

## 第 6 周状态：上下文搭建（不写业务代码）

本周为项目启动周，红线要求：**禁止编写任何正式业务代码**。仓库当前处于“上下文搭建”阶段，本周产出限定为：

- 独立 Git 仓库与标准目录骨架
- 项目上下文文档（`context.md`）
- AI 协作规则（`agent-rules.md`）
- 规格说明与 ADR
- 看板与分支协作方案
- 空 PR 协作演练

`src/` 与 `tests/` 目前仅保留 `.gitkeep` 占位，不包含任何业务代码。

## 目录地图

```
.
├── README.md                     # 本文件：项目总览与协作入口
├── context.md                    # 项目上下文（业务、角色、实体、技术栈、范围）
├── agent-rules.md                # AI 协作规则（提示词、边界、约定）
├── .gitignore                    # Java / Node / IDE / OS / 密钥 / 日志忽略规则
├── spec/                         # 需求与规格说明（SRS、各模块 spec）
├── adr/                          # 架构决策记录（Architecture Decision Records）
├── plans/                        # 迭代计划、技术方案与实施计划
├── src/                          # 源码目录（第 6 周仅 .gitkeep 占位，禁止业务代码）
├── tests/                        # 测试目录（第 6 周仅 .gitkeep 占位）
├── docs/
│   ├── spike/                    # 技术探针（技术预研）记录
│   └── reference/                # 原始资料归档（课程资料、外部参考）
└── .github/
    ├── CODEOWNERS                # 目录 → 负责人路由（占位，接远端后替换）
    ├── pull_request_template.md  # PR 模板
    └── ISSUE_TEMPLATE/
        ├── task.md               # 任务 Issue 模板
        └── bug.md                # 缺陷 Issue 模板
```

## 关键文档

| 文档 | 说明 |
| --- | --- |
| [context.md](./context.md) | 项目上下文：业务目标、角色、实体、技术栈与范围边界 |
| [agent-rules.md](./agent-rules.md) | AI 协作规则与提示词约定 |
| [spec/](./spec/) | 需求规格说明（SRS、模块 spec） |
| [adr/](./adr/) | 架构决策记录 |
| [plans/](./plans/) | 迭代计划与技术方案 |
| [docs/spike/](./docs/spike/) | 技术探针规则与记录 |
| [docs/reference/](./docs/reference/) | 原始资料归档说明 |
| [.github/pull_request_template.md](./.github/pull_request_template.md) | PR 提交模板 |
| [.github/ISSUE_TEMPLATE/](./.github/ISSUE_TEMPLATE/) | Issue 模板（task / bug） |

## 范围摘要

### 业务角色（仅 2 种）

- **学生**：参加考试、查看考试与答卷结果（以需求为准）。
- **教师**：建题、组卷、发布考试、查看答卷、对 AI 初评结果进行复核与定分。

> 不设“管理员”业务角色。账号管理、试卷发布等原管理员职能并入教师。教师组卷后直接发布，无需二次审批。

### MVP 模块（3 个）

1. **题库与组卷**：题目维护（含评分点）、试卷组卷（含组卷明细与分值）。
2. **在线考试与答卷**：考试发布、学生作答、答卷保存与提交。
3. **AI 主观题阅卷与教师复核**：调用 DeepSeek 对主观题初评，教师复核并最终定分。

### 题型（仅 2 种）

- **简答题**
- **论述题**

不做客观题，不做自动判分。

### 核心业务实体

- **题目**：题干、参考答案、评分点（rubric）。
- **试卷**：组卷明细（题目列表与顺序）、每题分值、总分。
- **答卷**：学生作答内容、AI 评分（含评分点命中情况）、教师复核结果。

### 技术栈

- **前端**：Vue 3
- **后端**：Java 21 / Spring Boot 4.1
- **数据库**：MySQL 8
- **AI**：DeepSeek OpenAI 兼容接口
- **鉴权**：JWT
- **部署**：Docker

### Non-Goals（明确不做）

- 不做客观题自动判分
- 不做管理员角色、自助注册、密码找回、支付、排名、监考
- 不做 AI 出题、错题讲解、自动定分
- 不做多租户、移动端、第二家模型接入

## 贡献方式

1. **一任务一分支**：每个任务从 `main` 拉出独立分支，分支名遵循 `agent-rules.md` AR-3.2：`feature/<module>-<issue>-<short-name>` 或 `docs/<issue>-<name>`。
2. **PR 绑定 Issue**：每个 PR 必须在描述中关联至少一个 Issue（`Closes #<编号>`），并在模板中填写关联 spec、变更摘要、AI 工具使用说明、测试证据与评审清单。
3. **Issue 先行**：任务使用 `task` 模板，缺陷使用 `bug` 模板；明确业务背景、验收标准、负责人与模块标签。
4. **规格对齐**：涉及需求变更的 PR 必须同步更新 `spec/`；架构层面的取舍需新增或更新 `adr/`。
5. **代码边界**：第 6 周不得提交业务代码；后续实现须遵守 `agent-rules.md` 中的 AI 协作约定。
6. **评审**：至少 1 名非作者评审通过后方可合并；目录负责人见 `.github/CODEOWNERS`。

## 远端说明（待接入）

本周**暂不连接远端**：

- 不执行 `git push`
- 不创建 GitHub 远端仓库
- 仓库仅在本地 `D:/AI智能考试系统` 独立初始化，与个人主页仓库 `D:/Vibe coding` 完全隔离

接入 GitHub 后需完成以下替换：

1. 将 `.github/CODEOWNERS` 中的 `@TODO-replace-*` 占位符替换为真实 GitHub 用户名 / 团队名。
2. 配置 `main` 分支保护：要求 PR、至少 1 名评审、CI 通过。
3. 按 `.github/ISSUE_TEMPLATE/` 与看板方案创建标签与看板列。
第 6 周空 PR 演练：仅文档变更，无业务代码。
