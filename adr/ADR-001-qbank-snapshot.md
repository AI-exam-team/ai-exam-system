# ADR-001：已发布试卷取题目快照还是引用

| 项目 | 内容 |
| --- | --- |
| 编号 | ADR-001 |
| 状态 | 提议（待评审；通过前 `architecture.md` 6.2 的快照行为仅作设计草案） |
| 日期 | 2026-11-17（第 8 周） |
| 主笔 | 孙宇萱（qbank） |
| 复核 | 周裔（qbank）、李昕彤（集成与契约） |
| 关联未决项 | `contract-v0.1.md` C-01 |
| 影响模块 | qbank（主）、exam（只读消费方）、grading（只读消费方） |
| 依据 | `contract-v0.1.md` 2.1 / 2.3 / 第 8 节；`module-01-qbank.md` 第 7、8 节；`architecture.md` 6.5 |

---

## 背景

`contract-v0.1.md` 2.3 已冻结：试卷 `PUBLISHED` 后，试卷结构、每题分值与时间窗口不可修改。但**题目本体**（题干、参考答案、评分点）在其被引用之后是否还允许修改、历史试卷与答卷取哪一版数据，是 C-01 留给第 8 周的问题。

具体冲突场景：

1. 教师 A 组卷并发布考试后，回头修改了原题目（改题干、改评分点分值）；
2. 学生正在作答，进入考试页时读到的是**修改后**的题干，与他此前作答时看到的题干不一致；
3. `grading` 用**修改后**的评分点评判学生按**旧评分点**作答的内容，出现评分不公；
4. 考试结束后回看历史，试卷内容已与当时不同，无法追溯。

谁在读题目：

| 消费方 | 读取时机 | 读取内容 |
| --- | --- | --- |
| exam | 发布校验、学生进入考试 | 题目 ID、顺序、分值、题干（不含评分点与参考答案） |
| grading | AI 初评 | 题干、参考答案、评分点 |

约束前提：

- MVP1 Non-Goals 明确**不做题目版本管理**（`mvp1-scope.md` 3.2）；
- MVP1 单库单实例，数据量小（题库 < 1000 题、试卷 < 50 份）；
- 跨模块只允许通过契约传递只读数据，禁止跨模块读表（`architecture.md` 4.1）；
- `exam` 对 `qbank` 只能只读，发布动作只改 `Paper.status`，不得反向写 qbank 数据。

---

## 决策

**采用「组卷时保存基线快照 + 发布时冻结为正式快照」**：

1. **组卷时（qbank）**：`POST /api/v1/papers` 在同一事务内，把每道入选题目的 `type`、`stem`、`referenceAnswer`、`totalScore` 及全部 `rubric` 条目（`rubricItemId` / `description` / `score` / `order`）深拷贝到 `paper_items` 的快照列，保留 `questionId` 作为追溯关联。这份快照在本文中称为**基线快照**。
2. **草稿阶段（qbank）**：基线快照用于对比，不自动跟随原题变化。新增只读接口 `GET /api/v1/papers/{id}/snapshot-diff`，逐题返回 `changed` 与 `baseline` / `current` 内容；**接口契约本期预留，前端对比页面第 10 周实现**。MVP1 不提供“刷新快照”写接口；教师若确认要换用当前题目，重新组卷即可。
3. **发布时（exam）**：`exam` 只把 `Paper` 从 `DRAFT` 改为 `PUBLISHED`，**不调用 qbank 写接口**。基线快照随 `Paper.status=PUBLISHED` 在语义上成为**正式快照**，并停止变更；下游只读这份快照。这样避免 `exam → qbank` 的跨模块写，保持依赖方向不变。
4. **下游读取**：`exam` 发布校验、学生答题页、`grading` AI 初评只读快照，永不回源读取 `questions` 表的最新内容。
5. **锁题规则（保留）**：`PUT /api/v1/questions/{id}` 在题目被任一 `PUBLISHED` 试卷引用时返回 409 `QUESTION_ALREADY_USED`。这是**产品策略**，不是快照机制的技术必需；代价与取舍见“取舍与 trade-off”。

> **为什么不在发布时“生成”一份新快照**：发布属于 exam，快照属于 qbank。若 exam 在发布时调用 qbank 写接口生成正式快照，会形成 `exam → qbank` 的跨模块写，违反当前依赖规则。MVP1 采用“组卷时存基线、发布时冻结”的一快照模型；若未来需要发布前刷新快照，应增加 qbank 的 **DRAFT 专用**刷新接口，由教师在草稿阶段触发，而不是让 exam 写 qbank。

配套规则：

1. `DRAFT` 试卷的快照在组卷时固定；教师若需换题或更新快照，重新组卷（MVP1）。
2. 快照列在 `PUBLISHED` 后不可更新；`CLOSED` 后仍保留。
3. 锁题规则覆盖“被任一 `PUBLISHED` 试卷引用”的题目，避免原题与正式快照出现两套真相。

---

## 备选方案

### 方案 A：动态引用（`paper_items` 只存 `questionId`）

- **优点**：零冗余；题目修改自动在所有试卷生效；存储与实现最简单。
- **缺点**：
  - 考试进行中改题会导致同一场考试内学生看到的题干不一致；
  - `grading` 会用新评分点评判旧答案，破坏评分一致性；
  - 历史考试不可追溯，与「试卷发布后冻结」的契约精神冲突；
  - 一旦出现事故，是**静默的数据漂移**，排查成本极高。

### 方案 B1：组卷时基线快照 + 发布冻结（✅ 采用）

- **优点**：
  - 试卷内容在组卷时即固定，学生、教师、AI 三方看到的是同一份内容；
  - 草稿阶段可通过 diff 看到“当初选的题目”和当前题目的差异；
  - 发布只改 `Paper.status`，保持 `exam → qbank` 只读，不引入跨模块写；
  - 不引入版本号概念，符合 MVP1 Non-Goals。
- **缺点**：
  - 数据冗余：一题被 N 份试卷引用则有 N 份快照；
  - 草稿阶段想更新快照只能重新组卷（MVP1）；
  - 锁题规则会阻止教师修改被用于已发布试卷的原题（见 trade-off）。

### 方案 B2：组卷基线快照 + 发布时另存正式快照

- **优点**：草稿基线与正式快照解耦；发布时可自由选择是否按当前题目刷新。
- **缺点**：
  - 同一份内容存两次，存储与一致性检查翻倍；
  - “刷新正式快照”要么由 exam 写 qbank（破坏依赖方向），要么新增 qbank 的 DRAFT 刷新接口（多一个接口与状态）；
  - MVP1 规模下收益不足以抵消复杂度。

### 方案 C：题目版本号（`paper_items` 存 `questionId + version`）

- **优点**：冗余小于快照；天然支持「题目历史版本」。
- **缺点**：
  - 等价于提前实现「题目版本管理」，触碰 `mvp1-scope.md` 3.2 Non-Goals；
  - 所有读题目方（exam / grading / 学生端）都要理解版本语义，接口复杂度上升；
  - 需要额外的版本表与版本切换流程，第 9 周任务量不可控。

---

## 取舍与 trade-off

选 **方案 B1**，理由：

1. **一致性优先于存储效率**：正式考试场景下「试卷内容冻结」是不可妥协的不变式。方案 A 的风险是静默的、影响评分公平的，MVP1 不应承担。
2. **不破坏依赖方向**：发布只改 `Paper.status`，不产生 `exam → qbank` 的写调用；跨模块仍然是只读。
3. **冗余成本可忽略**：单题快照约 1~3 KB（题干 + 参考答案 + 评分点 JSON），50 份试卷 × 10 题 ≈ 1~1.5 MB，对 MySQL 8 无压力。
4. **满足草稿对比需求**：基线快照保存在组卷时，diff 接口能回答“当初选的题目和现在有没有变化”；前端页面第 10 周实现，不阻塞第 9 周任务。

**保留锁题规则的代价**：

- 教师不能直接修改被已发布试卷引用的原题，包括错别字；
- 需要额外查询“该题是否被 `PUBLISHED` 试卷引用”，并新增 `QUESTION_ALREADY_USED` 错误码；
- 若后续要放开，应通过新 ADR 改为“允许改原题、只读正式快照”，而不是直接删规则。

方案 C 的版本号机制属于 v2 议题，MVP1 不引入。

---

## 后果与影响文件

### 数据模型（qbank）

`paper_items` 在原有 `paper_id`、`question_id`、`order`、`score` 基础上新增快照列：

| 新增列 | 类型 | 说明 |
| --- | --- | --- |
| `type_snapshot` | VARCHAR | 题型快照 |
| `stem_snapshot` | MEDIUMTEXT NOT NULL | 题干快照（存储类型待 SP-04 在 MySQL 8 复核） |
| `reference_answer_snapshot` | MEDIUMTEXT NOT NULL | 参考答案快照（contract 2.1 规定 `referenceAnswer` 必填，快照不可为空） |
| `rubric_json_snapshot` | JSON NOT NULL | 评分点数组快照：`[{rubricItemId, description, score, order}]`（JSON + utf8mb4 待 SP-04 复核） |
| `total_score_snapshot` | INT NOT NULL | 题目分值快照 |

约束：`UNIQUE(paper_id, question_id)`。

### 逻辑与接口

| 位置 | 变更 |
| --- | --- |
| `POST /api/v1/papers` | 同一事务内完成基线快照深拷贝；提交前校验 `paper_items` 行数 == `questionIds` 长度 |
| `GET /api/v1/papers/{id}/snapshot-diff` | 新增只读 diff 接口：逐题返回 `changed`、`baseline`、`current`；仅教师本人试卷；前端第 10 周实现 |
| `PUT /api/v1/questions/{id}` | 若题目被任一 `PUBLISHED` 试卷引用，返回 409 `QUESTION_ALREADY_USED`（待契约 v0.2 登记） |
| `GET /api/v1/papers/{id}` | `DRAFT` 返回基线快照字段；当前题目与差异通过 `snapshot-diff` 获取；`PUBLISHED` / `CLOSED` 只返回冻结的正式快照 |
| `POST /api/v1/papers/{id}/publish` | 属于 exam；只改状态，不调用 qbank 写接口；快照随状态成为正式快照 |
| 跨模块只读读取，按 `architecture.md` 6.5 的 `PaperForExam` | 从 `paper_items` 快照组装，不从 `questions` 取 |
| 跨模块只读读取，按 `architecture.md` 6.5 的 `QuestionForGrading` | 从快照组装；同一题在不同试卷可能是不同快照，需按 `paperId` 定位 |

### 跨模块影响

- **exam**：`PaperForExam` 契约字段不变，取值来源改为快照，对 exam 透明；发布仍只改 `Paper.status`。
- **grading**：`QuestionForGrading` 契约字段不变；仍需包含完整 `rubric`，且不得重算分值。
- **`architecture.md` 6.5**：需补注「qbank 侧取值来自 `paper_items` 快照」。
- **契约 v0.2**：需登记 `QUESTION_ALREADY_USED`；若采用 diff 接口，需新增该接口与权限说明。

### 不影响

- 试卷状态机、时间窗口、交卷、AI 评分、成绩发布；
- `contract-v0.1.md` 已冻结的字段名；本 ADR 的新增错误码在契约 v0.2 登记前只作为候选，不生效。

---

## 待验证

| # | 待验证项 | 方式 | 结论去向 |
| --- | --- | --- | --- |
| 1 | 快照长文本（`stem` / `referenceAnswer` / `rubric` JSON）在 MySQL 8 + utf8mb4 下能否完整往返（含 emoji、换行、中文标点） | SP-04（**待 MySQL 8 重跑**） | 当前 SQL Server 证据只作初步参考，不能作为 MySQL 结论 |
| 2 | 20KB / 50KB 内容选 `TEXT` 还是 `MEDIUMTEXT` | SP-04（**待 MySQL 8 重跑**） | 初步建议 `MEDIUMTEXT`，以 MySQL 实测为准 |
| 3 | 组卷深拷贝事务中途异常能否完整回滚（无半成品 `paper_items`） | 第 9 周集成测试 | 由 qbank 在第 9 周补验证，未验证前 R-01 标“待验证” |
| 4 | `JSON` 快照列在 utf8mb4 下的字符保留 | SP-04（与 #1 同时验证） | 同上 |

> 验证完成后由本 ADR 主笔（孙宇萱）回写结论；探针代码只留 `docs/spike/spike-mysql-text-storage/`，不合并 `src/`。

---

## 变更记录

| 日期 | 变更 | 原因 |
| --- | --- | --- |
| 2026-11-17 | 初版：确定组卷快照方案，明确快照字段与跨模块取值来源；题目被已发布试卷引用时的修改限制按 409 处理（待集成层在契约第 5 节登记） | 关闭 C-01，冻结 qbank→exam/grading 的一致性语义 |
| 2026-11-17 | 评审修订：改为“组卷基线快照 + 发布冻结”，新增 draft diff 接口（前端后置）；明确 exam 不写 qbank；保留锁题规则并记录代价；SP-04 结论改为待 MySQL 8 复核 | 回应第 8 周评审：避免跨模块写、修正证据链、统一快照语义 |
