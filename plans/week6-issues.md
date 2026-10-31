# 第 6 周 Issue 清单

> 本文是**本地规划清单**，用于看板登记与分工确认。仓库已于 2026-10-31 接入 GitHub 远端 `AI-exam-team/ai-exam-system`；`Issue-101`～`Issue-110` 为规划编号，实际编号见第五节。
> 负责人一律使用**角色名**或“待认领”，真人绑定由小组周会确认，不在此擅自指定。
> 分支命名统一为 `<type>/issue-<规划编号>-<简述>`，`type` 取 `feature` / `docs` / `fix`；仅 `Issue-104` 按演练要求固定为 `feature/issue-104-empty-pr`。
> **本地提交口径**：第 6 周实际本地历史按集成验收脚本建立 `docs/issue-101-context`、`docs/issue-102-rules`、`docs/issue-103-plans`、`feature/issue-104-empty-pr` 四个分支；本表编号为规划编号，两者映射见 `docs/week6-acceptance.md`，接远端后以 GitHub 实际编号为准。

## 一、总览

| 编号 | 标题 | 模块/标签 | 负责人建议 | 分支 |
| --- | --- | --- | --- | --- |
| Issue-101 | 初始化仓库骨架与协作模板 | infra / feature | repo-scaffolder（已完成） | `feature/issue-101-repo-scaffold` |
| Issue-102 | 编写项目上下文文档 | docs / spec | context-writer | `docs/issue-102-context-md` |
| Issue-103 | 编制小组项目基本信息表 | docs / spec | context-writer | `docs/issue-103-project-basic-info` |
| Issue-104 | 执行空 PR 协作演练 | docs / test | pr-rehearsal-owner（待认领） | `feature/issue-104-empty-pr` |
| Issue-105 | 制定 AI 协作规则 | docs / spec | rules-writer | `docs/issue-105-agent-rules` |
| Issue-106 | 搭建 spec 骨架与编写规范 | docs / spec | spec-writer（待认领） | `docs/issue-106-spec-skeleton` |
| Issue-107 | 建立 Projects 看板与标签体系 | infra / feature | board-planner | `docs/issue-107-github-projects` |
| Issue-108 | 明确模块分工与合并规则 | docs / spec | board-planner | `docs/issue-108-module-ownership` |
| Issue-109 | 建立 ADR 模板与记录规范 | docs / spec | integrator | `docs/issue-109-adr-template` |
| Issue-110 | 制定技术探针规范 | docs / spec | board-planner | `docs/issue-110-spike-guideline` |

标签沿用 `plans/github-projects.md` 的核心体系：类型 `spec` / `feature` / `test` / `bug`，模块 `qbank` / `exam` / `grading`；文档与基础设施任务使用扩展标签 `docs` / `infra`。

## 二、Issue 详情

### Issue-101 初始化仓库骨架与协作模板

- **模块/标签**：`infra`、`feature`
- **负责人建议**：repo-scaffolder（已完成，待集成验收）
- **验收标准**：
  - [x] 建立 `README.md`、`context.md` 占位说明、`agent-rules.md` 占位、`spec/`、`adr/`、`plans/`、`src/`、`tests/`、`docs/spike/`、`docs/reference/`
  - [x] `.gitignore` 覆盖 Java / Node / IDE / OS / 密钥 / 日志
  - [x] `.github/` 含 `CODEOWNERS`、PR 模板、Issue 模板（task / bug）
  - [ ] 集成负责人核对目录与 `README.md` 目录地图一致
- **关联 spec 占位**：无（仓库基础设施）
- **分支**：`feature/issue-101-repo-scaffold`

### Issue-102 编写项目上下文文档

- **模块/标签**：`docs`、`spec`
- **负责人建议**：context-writer
- **验收标准**：
  - [ ] `context.md` 覆盖业务目标、2 类角色、3 个模块、2 种题型、核心实体、技术栈
  - [ ] 明确 Non-Goals，且与 `README.md` 锁定决策无冲突
  - [ ] 术语表与 `spec/` 后续文档用词一致
  - [ ] 不包含具体实现代码与个人隐私
- **关联 spec 占位**：`context.md`（本文即源）
- **分支**：`docs/issue-102-context-md`

### Issue-103 编制小组项目基本信息表

- **模块/标签**：`docs`、`spec`
- **负责人建议**：context-writer
- **验收标准**：
  - [ ] 按课程模板填写项目名称、一句话简介、2 种用户角色、3 个核心实体、3 个核心模块
  - [ ] 填写技术栈、唯一外部依赖 DeepSeek，以及与 `context.md` 一致的 4 条 Non-Goals
  - [ ] 不写入学号、手机号等敏感个人信息
  - [ ] 信息表位置与 `context.md` 的引用互相可达
- **关联 spec 占位**：`context.md` §基本信息表（占位）
- **分支**：`docs/issue-103-project-basic-info`

### Issue-104 执行空 PR 协作演练

- **模块/标签**：`docs`、`test`
- **负责人建议**：pr-rehearsal-owner（待认领）
- **验收标准**：
  - [ ] 从 `main` 建立 `feature/issue-104-empty-pr` 分支
  - [ ] 仅修改 `README.md` 一行，不涉及业务代码
  - [x] 本地提交记录清晰，提交信息说明“演练”
  - [x] 按 `docs/pr-rehearsal.md` 填写完整 PR 描述模板
  - [x] 已推送远端并创建 PR #1，PR 描述已绑定本 Issue
  - [ ] 至少 1 名非作者完成评审演练并给出结论
  - [ ] 评审通过后合并
- **关联 spec 占位**：无（流程演练）
- **分支**：`feature/issue-104-empty-pr`

### Issue-105 制定 AI 协作规则

- **模块/标签**：`docs`、`spec`
- **负责人建议**：rules-writer
- **验收标准**：
  - [ ] `agent-rules.md` 说明允许/禁止的 AI 使用场景与提示词约定
  - [ ] 明确 AI 生成内容的复核责任与署名要求
  - [ ] 明确敏感信息（密钥、个人信息）禁止输入外部模型
  - [ ] 与 PR 模板“AI 工具使用说明”字段对应
- **关联 spec 占位**：`agent-rules.md`（本文即源）
- **分支**：`docs/issue-105-agent-rules`

### Issue-106 搭建 spec 骨架与编写规范

- **模块/标签**：`docs`、`spec`
- **负责人建议**：spec-writer（待认领）
- **验收标准**：
  - [ ] 在 `spec/` 建立总览与 3 个模块文档骨架（qbank / exam / grading）
  - [ ] 每份文档含目的、范围、角色、功能需求、验收标准、未决问题
  - [ ] 注明与其他模块的接口/契约占位
  - [ ] 规定 spec 变更必须走 PR 并更新关联 Issue
  - [ ] 不写入业务代码
- **关联 spec 占位**：`spec/spec-v0.1.md`、`spec/qbank-spec-*.md`、`spec/exam-spec-*.md`、`spec/grading-spec-*.md`（待建）
- **分支**：`docs/issue-106-spec-skeleton`

### Issue-107 建立 Projects 看板与标签体系

- **模块/标签**：`infra`、`feature`
- **负责人建议**：board-planner
- **验收标准**：
  - [ ] `plans/github-projects.md` 定义 5 列、5 个字段、标签体系
  - [ ] 明确 Issue 先行、PR 绑定 Issue、仅 Review 列允许提 PR、看板为唯一进度依据
  - [ ] 给出接远端后的 Project 模板、列、标签、自动化创建步骤
  - [ ] 与 `.github/ISSUE_TEMPLATE/` 默认标签的兼容方案写明
- **关联 spec 占位**：无（协作流程）
- **分支**：`docs/issue-107-github-projects`

### Issue-108 明确模块分工与合并规则

- **模块/标签**：`docs`、`spec`
- **负责人建议**：board-planner
- **验收标准**：
  - [ ] `plans/module-ownership.md` 给出 6 人 3 组建议映射，并标注“待小组确认，可调整”
  - [ ] 写明模块目录、CODEOWNERS 路由、跨模块接口变更流程
  - [ ] 写明每周合并节奏、冲突处理与升级路径
  - [ ] 集成与契约负责人职责单独成节
- **关联 spec 占位**：`spec/spec-v0.1.md`（接口边界待补）
- **分支**：`docs/issue-108-module-ownership`

### Issue-109 建立 ADR 模板与记录规范

- **模块/标签**：`docs`、`spec`
- **负责人建议**：integrator
- **验收标准**：
  - [ ] `adr/` 提供编号模板（背景、决策、备选方案、后果、状态）
  - [ ] 规定何时必须写 ADR（架构取舍、跨模块契约、技术栈变更）
  - [ ] 规定 ADR 与 spec、PR 的互相引用方式
  - [ ] 不覆盖已锁定的本周决策，只做记录规范
- **关联 spec 占位**：`adr/0000-template.md`（待建）
- **分支**：`docs/issue-109-adr-template`

### Issue-110 制定技术探针规范

- **模块/标签**：`docs`、`spec`
- **负责人建议**：board-planner
- **验收标准**：
  - [ ] `docs/spike/README.md` 列出允许的探针类型
  - [ ] 规定目录命名 `spike/<topic>`、时间盒、可复现要求
  - [ ] 每个探针必须写验证问题、假设、结论（可行/不可行/有条件可行）
  - [ ] 明确禁止将探针代码合入 `src/`
  - [ ] 提供探针登记表
- **关联 spec 占位**：无（研发流程）
- **分支**：`docs/issue-110-spike-guideline`

## 三、依赖与排期建议

```text
Issue-101（骨架，已完成）
   ├─ Issue-102（context） ─┐
   ├─ Issue-103（基本信息）─┤
   ├─ Issue-105（AI 规则）  ├─→ Issue-109（ADR 规范）
   ├─ Issue-106（spec 骨架）┘
   ├─ Issue-107（看板）
   ├─ Issue-108（分工）
   ├─ Issue-110（探针规范）
   └─ Issue-104（空 PR 演练，依赖 101 + 107）
```

- 本周必须完成：101、102、103、104、105、107、108（课程要求的上下文搭建与演练）。
- 106、109、110 可在本周收尾或顺延到第 7 周，但看板中必须先建 Issue。
- 所有 Issue 建立后统一进入 `Backlog`，周会再移入 `This Week`；负责人以周会确认为准。

## 四、登记与命名说明

1. **先建 Issue 再干活**：接远端后按本清单逐个创建，标题保持“动词 + 对象”，创建后补 GitHub 实际编号到总览表。
2. **规划编号 ≠ GitHub 编号**：分支名中的 `issue-104` 使用规划编号，避免因远端编号变化反复改名；PR 描述使用 GitHub 实际编号（如 `Closes #12`）。
3. **负责人变更**：由 Owner 在 Issue 评论说明，禁止静默改派；看板 Owner 字段同步更新。

## 五、GitHub 实际编号映射（2026-10-31）

仓库：<https://github.com/AI-exam-team/ai-exam-system>

| 规划编号 | GitHub 实际编号 | 标题 | 状态 |
| --- | --- | --- | --- |
| Issue-101 | #2 | 初始化仓库骨架与协作模板 | closed |
| Issue-102 | #3 | 编写项目上下文文档 | closed |
| Issue-103 | #4 | 编制小组项目基本信息表 | closed |
| Issue-104 | #5 | 执行空 PR 协作演练 | open（PR #1 待评审） |
| Issue-105 | #6 | 制定 AI 协作规则 | closed |
| Issue-106 | #7 | 搭建 spec 骨架与编写规范 | closed |
| Issue-107 | #8 | 建立 Projects 看板与标签体系 | open（看板待建） |
| Issue-108 | #9 | 明确模块分工与合并规则 | closed |
| Issue-109 | #10 | 建立 ADR 模板与记录规范 | closed |
| Issue-110 | #11 | 制定技术探针规范 | closed |

已完成项对应提交见 `docs/week6-acceptance.md`；空 PR 为 PR #1，目标分支 `main`，源分支 `feature/issue-104-empty-pr`。

