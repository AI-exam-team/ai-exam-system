# 分支规划表（第 9 周）

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.8（ADR-004 已接受，T5/T7 解除闸门） |
| 状态 | 草稿 |
| 日期 | 2026-11-25 |
| 负责人 | 李昕彤（组长 / 集成与契约） |
| 依据 | `plans/mvp1-plan.md` v0.8；课程第 9 周分支策略 |

> 一任务一分支，全部从 `main` 切出；合并方式 squash，合并后删除任务分支。

## 1. 命名规范

| 前缀 | 用途 | 示例 |
| --- | --- | --- |
| `feature/` | 新功能 | `feature/issue-43-exam-publish` |
| `fix/` | 缺陷修复 | `fix/issue-44-submit-idempotency` |
| `spike/` | 技术探针 | `spike/issue-45-ai-timeout` |
| `test/` | 测试与验收 | `test/issue-46-e2e-demo` |
| `docs/` | 文档与契约 | `docs/issue-47-week9-plan` |

## 2. MVP1 任务分支

| 任务ID | 分支名 | 类型 | 基础分支 | 关联 Issue | 负责人 | 合并要求 |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | `feature/issue-39-qbank-db-schema` | feature | `main` | #39 | 周裔（qbank） | PR 准入 8 条 + 孙宇萱评审 |
| T2 | `feature/issue-42-auth-jwt` | feature | `main` | #42 | 李昕彤（集成） | 同上；作者不自审，评审人钱斓轩 |
| T3 | `feature/issue-40-question-rubric` | feature | `main` | #40 | 周裔（qbank） | 同上，孙宇萱评审 |
| T4 | `feature/issue-41-paper-draft` | feature | `main` | #41 | 周裔（qbank） | 同上，孙宇萱评审 |
| T5 | `feature/issue-43-exam-publish` | feature | `main` | #43 | 钱斓轩（exam） | 同上；`ADR-004` 已接受（PR #55 已合入），可开发 |
| T6 | `feature/issue-44-answer-draft` | feature | `main` | #44 | 钱斓轩（exam） | 同上，李昕彤评审；`ADR-002` 已接受，可开发 |
| T7 | `feature/issue-45-submit` | feature | `main` | #45 | 钱斓轩（exam） | 同上，李昕彤评审；`ADR-002`、`ADR-004` 均已接受，可开发 |
| T8 | `feature/issue-46-ai-grade` | feature | `main` | #46 | 王麒博（grading） | 同上；涉及 `ADR-003` 需组长评审 |
| T9 | `feature/issue-47-ai-fallback` | feature | `main` | #47 | 王麒博（grading） | 同上，左恩东评审 |
| T10 | `feature/issue-48-review` | feature | `main` | #48 | 王麒博（grading） | 同上，左恩东评审 |
| T11 | `feature/issue-49-score-publish` | feature | `main` | #49 | 王麒博（grading） | 同上，左恩东评审 |
| T12 | `feature/issue-50-score-view` | feature | `main` | #50 | 王麒博（grading） | 同上，左恩东评审 |

## 3. 第 9 周文档分支

> 文档交付不占 12 个 MVP1 任务名额。若不为文档单建 Issue，使用 `docs/week9-<主题>`；建了 Issue 则按 `docs/issue-{N}-...` 命名。

| 交付 | 分支名 | 类型 | 基础分支 | 合并要求 |
| --- | --- | --- | --- | --- |
| D1 计划 + D2 分支表 | `docs/week9-plan` | docs | `main` | 非作者评审 + 组长终审 |
| D3 PR 门禁 | `docs/week9-pr-gate` | docs | `main` | 同上 |
| D4 看板 | 无需代码分支，按 Issue 与 Projects 操作 | — | — | 卡片留痕 |
| D5 角色表 | `docs/week9-roles` | docs | `main` | 同上 |

## 4. 合并与清理

- 一个分支只对应一个 Issue、一个 PR；不夹带无关修改。
- 合并前 rebase 到最新 `main`，禁止 `push --force` 覆盖他人提交。
- 建议 squash merge，保持 `main` 线性；合并后删除任务分支。
- PR 超过 400 行有效变更时拆分或先写 ADR。
- 合并窗口：周四 18:00 首次，周五 12:00 只收修复与文档。

## 5. 规则同步

- 2026-11-25 远端核实：PR #55 已合入 main，`ADR-004` 已接受；T5、T7 的 ADR-004 闸门解除，可按本表开发。
- 2026-11-24 远端核实：`ADR-002` 已接受（PR #56 合入 main），T6/T7 解除闸门。
- 2026-11-24 #43–#45 Issue 回填同步：T5 加 `ADR-004` 闸门，T6/T7 加 `ADR-002`（及 T7 的 `ADR-004`）闸门；分支名不变，详见 `plans/mvp1-plan.md` v0.6 §2.2。
- 2026-11-24 #39–#41 Issue 回填同步：T1 分支改为 `feature/issue-39-qbank-db-schema`；T3、T4 分支名不变，AC 与依赖调整见 `plans/mvp1-plan.md` v0.5。
- 2026-11-23 三组负责人已回填：qbank 周裔 / 孙宇萱（评审）、exam 钱斓轩 / 李昕彤（评审）、grading 王麒博 / 左恩东（评审）。
- 2026-11-21 已将 `agent-rules.md` AR-3.2 与 `CLAUDE.md` 统一为课程规范 `feature/issue-{N}-{short-name}`。
- 旧格式 `<module>-<issue>-...` 只对应已存在的历史分支，不再新建；历史分支不改名。
