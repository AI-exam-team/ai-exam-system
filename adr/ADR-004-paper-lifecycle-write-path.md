# ADR-004：Paper 发布/关闭的跨模块写路径

| 字段 | 内容 |
| --- | --- |
| 编号 | ADR-004 |
| 标题 | Paper 生命周期由 qbank 受控命令执行，exam 不直接写 qbank 表 |
| 状态 | 提议（集成裁决；待 qbank 与 exam 评审后转已接受） |
| 日期 | 2026-11-18 |
| 决策者 | 李昕彤（集成与契约） |
| 评审人 | 孙宇萱（qbank）、钱斓轩（exam） |
| 关联需求 | `spec/contract-v0.1.md` 2.3 / 3.1；`spec/module-02-exam.md` FR-1 / FR-2 / AC-1 / AC-5 / AC-8；`docs/architecture.md` 4.1 / 6.3.1 / 6.3.8 / 6.5 |
| 关联 Issue | #32（第 8 周 exam 文档任务） |
| 相关 ADR | ADR-001（快照）、ADR-002（交卷幂等） |

---

## 背景

`Paper` 由 qbank 创建并维护，但**发布考试**（`DRAFT → PUBLISHED`，写入 `startAt` / `endAt` / `publishedAt`）和**关闭考试**（`PUBLISHED → CLOSED`）是 exam 的职责。当前三份文档对写路径的说法不一致：

1. `docs/architecture.md` 4.1 规定：`exam → qbank` 只读，禁止跨模块写表；
2. `docs/architecture.md` 6.3.1（PR #34）要求 exam 发布时写 `Paper.status / startAt / endAt / publishedAt`；
3. `adr/ADR-001-qbank-snapshot.md` 又写：exam“只改 Paper.status、不调用 qbank 写接口”。

三者不能同时成立。若 exam 直接写 qbank 表，模块边界和依赖规则被破坏；若把发布字段迁到 exam 自有表，又会改变“一份试卷即一场考试”的核心契约，牵动 qbank / grading / SRS。

课程约束：单体应用、单一 MySQL、禁止 Redis / 消息队列 / 微服务；跨模块调用是进程内调用，不存在分布式事务。

---

## 决策

**qbank 保留 `Paper` 所有权，并暴露一组受控的 Paper 生命周期命令；exam 只调用命令，不直接写 qbank 表。**

### 1. 受控写命令（qbank 实现，exam 调用）

```text
PaperLifecyclePort.markPublished(
    paperId, teacherId, startAt, endAt, publishedAt
) -> PaperForExam

PaperLifecyclePort.markClosed(paperId) -> void
```

`markPublished` 在 qbank 内完成并校验：

1. `paper.createdBy == teacherId`；
2. `status == DRAFT`，否则 409 `PAPER_NOT_DRAFT`；
3. `items` 非空，否则 409 `EMPTY_PAPER`；
4. `totalScore == Σ items[].score`，否则 409 `PAPER_SCORE_MISMATCH`；
5. `startAt < endAt` 且发布时 `endAt` 未过期，否则 409 `INVALID_EXAM_WINDOW`；
6. 写入 `status=PUBLISHED`、`startAt`、`endAt`、`publishedAt`；
7. 按 ADR-001 冻结基线快照为正式快照；
8. 返回 `PaperForExam`。

`markClosed` 在 qbank 内完成并校验：

1. `status == PUBLISHED`；若已是 `CLOSED`，按幂等处理（返回成功，不改字段）；
2. 写入 `status=CLOSED`；
3. 不涉及答卷数据，防止 qbank 反向依赖 exam。

### 2. 到期试卷查询（qbank 只读）

```text
PaperDueQueryPort.findDuePapers(now)
    -> [{ paperId, endAt }]   // status=PUBLISHED 且 endAt <= now
```

自动交卷扫描以**到期试卷**为起点，而不是只扫 `answer_sheets` 中的 `DRAFT`。这样：

- 零答卷的试卷也能在 `endAt` 后被关闭；
- 扫描不需要直接 JOIN qbank 的 `papers` 表；
- 每张到期试卷处理一次，避免按答卷重复查询试卷。

### 3. `PaperForExam` 补齐字段

```text
PaperForExam {
  paperId, title, totalScore, status,
  startAt, endAt, publishedAt, createdBy,
  items[{ questionId, order, score, type, stem }]
}
```

- `startAt` / `endAt`：窗口控制与自动交卷判断；
- `publishedAt`：发布展示与审计；
- `createdBy`：教师发布/查看答卷的归属校验；
- `createdBy` 只在进程内 DTO 使用，不返回学生端。

### 4. 自动交卷与关闭顺序

1. `findDuePapers(now)` 取出到期 `PUBLISHED` 试卷；
2. 对每张试卷，按 ADR-002 的条件更新自动交卷其全部 `DRAFT` 答卷；
3. 全部成功（或本来就没有 `DRAFT`）后，调用 `markClosed(paperId)`；
4. 任一份失败则本轮不关闭，下一轮重试，避免 `CLOSED` 后无法再自动交卷。

### 5. 依赖规则例外

`docs/architecture.md` 4.1 改为：

> 跨模块默认只读。`Paper` 的发布/关闭是**唯一受控写命令**，由 qbank 实现、exam 调用（ADR-004）；除该命令外，exam 不得写 qbank 任何表或字段。

这是**受控命令**，不是通用写权限：qbank 负责全部校验与状态迁移，exam 不能直接 SQL / Mapper 操作 `papers`。

---

## 备选方案

| 方案 | 优点 | 缺点 | 未采用原因 |
| --- | --- | --- | --- |
| A. exam 直接写 `papers` 表 | 实现最短，无新接口 | 破坏模块边界；qbank 的校验与快照逻辑被绕过；依赖规则形同虚设 | 违反 4.1 / AR-2.4 / AR-2.6 |
| B. qbank 受控命令（**采用**） | 单一数据源；qbank 集中校验；exam 不碰表；零答卷关闭可解决 | qbank 多 3 个端口；exam 需映射命令错误 | — |
| C. 新建 exam 自有 `exam_sessions` 表 | exam 完全拥有发布字段，职责清晰 | 改变“一份试卷即一场考试”；`PaperForExam`、快照、成绩发布、SRS 都要改；数据双写风险 | MVP1 改动面过大，且与 contract 2.3 冲突 |
| D. 事件/消息队列 | 解耦 | 课程禁止 MQ；最终一致性对 MVP1 过度 | 范围红线 |
| E. qbank 直接提供发布 REST API | 复用现有 owner | 发布是 exam 的职责与权限入口，qbank 会反向依赖 exam 的窗口语义 | 职责倒置 |

**为什么选 B**：它把“谁能改 Paper”和“谁决定何时发布”分开——qbank 拥有数据与校验，exam 拥有发布动作与时间窗口。既不破坏依赖方向，也不改变“一份试卷即一场考试”的契约。

---

## 后果

### 正面影响

- `Paper` 只有一个写入方（qbank），状态迁移、快照冻结、分值校验集中在一处。
- exam 不需要直接 SQL/Mapper 操作 qbank 表，依赖规则可检查。
- `findDuePapers` 让自动交卷从“到期试卷”出发，零答卷试卷也能关闭。
- `PaperForExam` 补齐字段后，exam 的窗口控制、自动交卷、发布归属校验都能落地。

### 负面影响 / 代价

- qbank 需要新增 2 个命令 + 1 个查询端口，第 9 周 qbank 任务量增加。
- exam 需要把命令返回的错误映射为 6.3.1 的 HTTP 错误码。
- `markClosed` 在自动交卷失败时可能延迟一轮扫描；这是可接受的最终一致。
- `PaperForExam` 暴露 `createdBy` 给 exam 进程内使用，必须确保不进入学生端响应。
- ADR-001 中“exam 不调用 qbank 写接口”的措辞需要修订为“exam 调用受控命令”。

### 后续需要完成的事项

- [ ] qbank 确认 `PaperLifecyclePort` / `PaperDueQueryPort` 的命名、参数与错误映射（孙宇萱、周裔）。
- [ ] exam 更新 6.3.1 / 6.3.8：发布调用 `markPublished`，关闭调用 `markClosed`，扫描改用 `findDuePapers`（钱斓轩）。
- [ ] `architecture.md` 4.1 / 6.5 / 5.1 更新；ADR-001 增补关联说明。
- [ ] 契约 v0.2 登记 `PAPER_NOT_DRAFT`；`VALIDATION_ERROR` / `PAPER_NOT_FOUND` 已在 5.1。
- [ ] 第 10 周测试：发布状态迁移、重复发布 409、关闭幂等、零答卷试卷关闭、无直接 SQL 访问。

---

## 验证方式

| 验证项 | 方式 | 成功标准 |
| --- | --- | --- |
| 发布状态迁移 | qbank 单元测试 + exam 集成测试 | `DRAFT → PUBLISHED` 一次成功；重复发布 409 `PAPER_NOT_DRAFT` |
| 快照冻结 | 发布后修改原题，再读 `PaperForExam` | 返回发布时的快照内容 |
| 关闭幂等 | 连续两次 `markClosed` | 第二次不改字段、不报错 |
| 零答卷关闭 | 一张 `PUBLISHED` 试卷无任何答卷，`endAt` 到期 | 下一轮扫描后 `Paper.status=CLOSED` |
| 依赖合规 | 代码检索 / 评审 | exam 无 `papers` 表 SQL/Mapper；只调用端口 |

---

## 关联需求 / Issue

- 需求：`spec/contract-v0.1.md` 2.3 / 3.1；`spec/module-02-exam.md` FR-1 / FR-2 / AC-1 / AC-5 / AC-8
- Issue：#32
- 相关 ADR：ADR-001（发布冻结快照）、ADR-002（交卷幂等与自动交卷触发）
