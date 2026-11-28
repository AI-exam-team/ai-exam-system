# AI 智能考试系统（AI Exam System）

上海师范大学软件工程课程项目。面向高校课程场景的 AI 辅助主观题考试系统：教师建题组卷并发布考试，学生在线上作答，系统调用大模型完成主观题初评，教师进行最终复核。

## 当前项目状态（2026-11-28）

需求、模块规格、架构决策、技术探针与 MVP1 任务计划已归档；项目尚未进入业务实现阶段。`src/` 与 `tests/` 目前只有占位文件，MVP1 计划中的 12 项任务仍为 Backlog，因此当前仓库还不能构建或演示可运行的考试系统。

接口和阅卷方案仍有待评审：grading 契约 v0.2 是草案，ADR-003 仍为提议，OpenAPI 文件尚未建立。SP-01 实测资料在 PR #52 中等待评审；SP-02、SP-03、SP-04 的探针结论已记录在各自 README 与 `docs/spike/plan.md`。

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
├── src/                          # 业务实现尚未开始；目前只有占位文件
├── tests/                        # 自动化测试实现尚未开始；目前只有占位文件
├── docs/
│   ├── spike/                    # 技术探针（技术预研）记录
│   ├── reference/                # 原始资料归档（课程资料、外部参考）
│   ├── pr-rehearsal.md           # 空 PR 演练步骤
│   ├── team-guide.md             # 团队协作指南（仓库架构 + GitHub 流程）
│   └── week6-acceptance.md       # 第 6 周验收报告
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
| [docs/team-guide.md](./docs/team-guide.md) | **团队协作指南：仓库架构、分支/PR/评审/看板流程** |
| [docs/spike/](./docs/spike/) | 技术探针规则与记录 |
| [docs/reference/](./docs/reference/) | 原始资料归档说明 |
| [docs/week6-acceptance.md](./docs/week6-acceptance.md) | 第 6 周集成验收报告 |
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
5. **代码边界**：实现范围与任务顺序以当前评审通过的 spec、ADR 和 MVP1 计划为准；AI 协作遵守 `agent-rules.md`。
6. **评审**：至少 1 名非作者评审通过后方可合并；目录负责人见 `.github/CODEOWNERS`。

## 远端与协作入口

- 仓库：<https://github.com/AI-exam-team/ai-exam-system>
- 看板：<https://github.com/orgs/AI-exam-team/projects/2>
- 空 PR：<https://github.com/AI-exam-team/ai-exam-system/pull/1>

当前待办与决策入口：

- MVP1 任务及状态：[`plans/mvp1-plan.md`](./plans/mvp1-plan.md)；当前 12 项任务均为 Backlog。
- AI 阅卷实测与决策：[`PR #52`](https://github.com/AI-exam-team/ai-exam-system/pull/52) 和 [`ADR-003`](./adr/ADR-003-grading-ai-invocation-and-idempotency.md)。
- 协作配置：`.github/CODEOWNERS` 的前端 owner 仍待小组确认；分支保护与 CI 门禁需要在 GitHub 仓库设置中核实并落实。
- 第 6 周验收与空 PR 演练文档是历史记录，不代表当前阶段或远端状态。

团队协作细节见 [`docs/team-guide.md`](./docs/team-guide.md)。
 main
