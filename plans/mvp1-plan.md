# MVP1 任务计划（mvp1-plan）

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.4（三组任务负责人已回填） |
| 状态 | 草稿，待交叉评审与看板录入 |
| 日期 | 2026-11-21 |
| 负责人 | 李昕彤（组长 / 集成与契约） |
| 依据 | `docs/architecture.md` v0.1；`spec/mvp1-scope.md` v0.2；`spec/module-01~03`；`spec/contract-v0.1.md`；`adr/ADR-001`、`adr/ADR-004`；课程第 9 周 |
| 评审人 | 待指定 1 名组员（作者不得自审） |

> 本文件是第 9 周唯一任务清单。任务行的「负责人」由各组回报名单后由组长统一回填，组长不指定组内分工；最终提交时不得留「待定」。

---

## 1. 使用规则

- 一个任务 = 一个可评审 PR，1–3 天可完成。
- 每个任务绑定 1–2 条 AC，最多 3 条；AC 必须带模块前缀，例如 `module-01 AC-3`，不能只写 `AC-3`。
- 没有 AC 绑定的任务不得进看板（课程红线，违者评分上限 3.0）。
- 分支名已按 Issue 实际编号回填；一个任务一个分支。
- 状态取值：`Backlog` / `This Week` / `In Progress` / `Review` / `Done`；`Done` 只由 PR 合并或明确验收结论触发。
- 跨模块变更先改 `spec/` 或 `adr/`，再实现。

## 2. 任务表（八列）

| 任务ID | 对应 spec/AC | 任务描述 | 负责人 | 分支名 | 依赖 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | `contract` §3；`ADR-001` 快照字段 | 数据库表与迁移初始化：题目、评分点、试卷、答卷、评分结果（#39） | 周裔（qbank） | `feature/issue-39-schema-init` | 无 | 迁移可重复执行；表结构与 `contract` §3 一致；三方评审确认字段无遗漏 | Backlog |
| T2 | `mvp1-scope` §3.3；`module-02 AC-9` | 教师 / 学生登录与 JWT 鉴权（#42） | 李昕彤（组长 / 集成） | `feature/issue-42-auth-jwt` | T1（#39） | 登录成功返回 JWT；无 token / 失效 token 401；越权 403 | Backlog |
| T3 | `module-01 AC-1`、`AC-2` | 题目与评分点录入（含模糊词拦截）（#40） | 周裔（qbank） | `feature/issue-40-question-rubric` | T1（#39） | 建题保存成功；模糊评分点 409 `RUBRIC_DESCRIPTION_VAGUE`；分值不等 409 `RUBRIC_SCORE_MISMATCH` | Backlog |
| T4 | `module-01 AC-3`、`AC-4` | 组卷与分值一致性校验（保存 DRAFT 试卷）（#41） | 周裔（qbank） | `feature/issue-41-paper-draft` | T3（#40） | 2–5 题组卷保存为 DRAFT；越界或分值不一致被拒绝 | Backlog |
| T5 | `module-02 AC-1`、`AC-8`；`ADR-004` | 发布考试与时间窗口校验（DRAFT → PUBLISHED）（#43） | 钱斓轩（exam） | `feature/issue-43-exam-publish` | T4（#41） | 发布成功；空卷 / 总分不符 / 窗口非法分别 409；非本人试卷 403 | Backlog |
| T6 | `module-02 AC-2`、`AC-3`、`AC-10` | 学生进入考试与草稿自动保存（#44） | 钱斓轩（exam） | `feature/issue-44-answer-draft` | T5（#43）、T2（#42） | 首次进入建卷、重复进入返回同一份；保存失败 1s/2s/4s 重试 3 次并提示未保存 | Backlog |
| T7 | `module-02 AC-4`、`AC-5`、`AC-6` | 手动交卷、到点自动交卷与幂等（#45） | 钱斓轩（exam） | `feature/issue-45-submit` | T6（#44） | 交卷置 SUBMITTED；重复交卷 409 `EXAM_ALREADY_SUBMITTED`；手动与自动并发仅迁移一次 | Backlog |
| T8 | `module-03 AC-1`、`AC-2`、`AC-3` | AI 初评成功路径与结果复用（#46） | 王麒博（grading） | `feature/issue-46-ai-grade` | T7（#45） | 仅 SUBMITTED 可初评；逐评分点输出命中、理由与得分；重复触发不重复调用模型 | Backlog |
| T9 | `module-03 AC-4`、`AC-5` | AI 输出校验与失败降级（#47） | 王麒博（grading） | `feature/issue-47-ai-fallback` | T8（#46） | 结构异常整单拒绝并标 FAILED；超时 / 越界返回契约错误码；不自动记 0 分 | Backlog |
| T10 | `module-03 AC-6`、`AC-7`、`AC-8` | 教师逐题复核与留痕（#48） | 王麒博（grading） | `feature/issue-48-review` | T9（#47） | 采纳 / 修改 / 驳回均留痕；确认分边界正确；AI 原建议分不被覆盖 | Backlog |
| T11 | `module-03 AC-9`、`AC-10` | 整场复核校验与统一发布成绩（#49） | 王麒博（grading） | `feature/issue-49-score-publish` | T10（#48） | 未全复核发布 409 `GRADE_NOT_FULLY_REVIEWED`；全复核后 finalScore = 各题确认分之和，无部分发布 | Backlog |
| T12 | `module-03 AC-11`、`AC-12` | 学生查分与访问隔离（#50） | 王麒博（grading） | `feature/issue-50-score-view` | T11（#49）、T2（#42） | 发布前 403 `SCORE_NOT_PUBLISHED`；发布后仅本人可见确认分与意见；不泄露参考答案与 AI 分 | Backlog |

## 3. 依赖与关键路径

```text
T1 ─┬─ T2 ─────────────────────────────┐
    └─ T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12
```

- 关键路径：`T1 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12`
- 并行线：`T2` 在 `T1` 后可与 qbank 线并行，`T12` 与 `T2` 汇合。
- 数据层先做（T1）；所有跨模块读取只走契约。

## 4. 第 9 周横向任务（不占 12 个 MVP1 任务名额）

| ID | 交付 | 负责人 | 截止 | 看板列 |
| --- | --- | --- | --- | --- |
| D1 | 本文件：八列任务表与规则 | 李昕彤 | 周会前 | This Week |
| D2 | `plans/branch-plan.md` 分支规划表 | 李昕彤 | 周会后次日 | This Week |
| D3 | PR 准入条件（模板 + 本文件附录） | 李昕彤 | 周会前 | This Week |
| D4 | 12 个 Issue 已建（#39–#50），本周卡 #51，待录入 Project #2 | 李昕彤 | 周会后次日 | This Week |
| D5 | `plans/roles.md` 角色轮换表 | 李昕彤 + 各组回填 | 周会后 | This Week |

> 看板「This Week」至少放 D1、D3 两张卡，避免“只建不用”。

## 5. 端到端验收（AC-S1）

- 演示路径：建题 → 组卷 → 发布 → 作答 → 交卷 → AI 初评 → 逐题复核 → 发布成绩 → 学生查分。
- 责任人：组长组织；各组提供演示数据与验收证据。
- 证据：演示脚本、接口请求 / 响应记录、关键页面截图，附在 T12 的验收证据中。
- 不单列任务，避免任务数超过 12。

## 6. 范围红线

- 只拆 MVP1；Non-Goals 以 `spec/mvp1-scope.md` §3.2 为准。
- 第 9 周不写业务生产代码；`src/` 保持占位。
- 不拆预约、统计、监考等非 MVP1 能力。

## 7. 状态与待办

- 容量：T2 登录与 JWT 已归集成（组长）；exam 组 T5–T7 由钱斓轩主笔，是否补第 2 名成员由组内商定，不阻塞第 9 周交付。
- 已统一：`mvp1-scope` v0.2、`module-02` v0.3、`plans/module-ownership.md` 的负责人；`agent-rules.md` 与 `CLAUDE.md` 的分支规范；PR 模板。
- D4 看板：Issue #39–#51 已在 GitHub；Project #2 的录入、字段与 This Week 列待完成。
- 任务行负责人已按各组回报回填：qbank 周裔（Reviewer 孙宇萱）、exam 钱斓轩（Reviewer 李昕彤）、grading 王麒博（Reviewer 左恩东）；T2 由李昕彤承担，评审人指定钱斓轩（作者不自审）。
- grading 组的负责人与 Reviewer 按模块 spec 文件头（王麒博主笔、左恩东冷启动/评审）回填；若组内另有安排，改 `plans/roles.md` 与本表即可。

## 8. 变更记录

| 版本 | 日期 | 变更人 | 内容 |
| --- | --- | --- | --- |
| v0.1 | 2026-11-21 | 李昕彤 | 建立第 9 周骨架：12 个任务、依赖与关键路径、横向任务、验收与待确认 |
| v0.2 | 2026-11-21 | 李昕彤 | 创建 Issues #39–#50，回填分支名与依赖编号 |
| v0.3 | 2026-11-21 | 李昕彤 | T2 登录归集成负责人；创建本周看板卡 #51；统一负责人与分支规范 |
| v0.4 | 2026-11-23 | 李昕彤 | 回填三组任务负责人与 Reviewer：qbank 周裔/孙宇萱、exam 钱斓轩/李昕彤、grading 王麒博/左恩东；T2 评审人钱斓轩 |
