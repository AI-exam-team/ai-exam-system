# 跨模块契约（contract-v0.1）

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.1 |
| 状态 | 草稿（待三组评审） |
| 日期 | 2026-11-10 |
| 负责人 | 李昕彤（集成与契约） |
| 关联 Issue | 待关联（第 7 周 Spec 任务） |
| 依据 | `context.md` v0.1；`spec/mvp1-scope.md` v0.1；2026-11-10 组内四项决策 |

> 本契约规定**实体、字段名、状态机、错误码与可见性**，是三份模块 spec 的共同前提。
> 契约不规定接口路径、数据库表结构与实现方式——接口以 OpenAPI、技术决策以 ADR 在第 8 周确定。
> 变更本文件须走独立 PR，说明影响面，并由受影响模块双方各 1 人确认。

---

## 1. 实体总览

| 实体 | 英文名 | 产生模块 | 消费模块 | 说明 |
| --- | --- | --- | --- | --- |
| 题目 | `Question` | qbank | qbank、grading | 简答或论述题，含参考答案与评分点 |
| 评分点 | `RubricItem` | qbank | grading | 可独立判定的得分要点，分值之和等于题目分值 |
| 试卷 | `Paper` | qbank | exam | 题目有序集合；**一份试卷即一场考试**，时间窗口写在试卷上 |
| 答卷 | `AnswerSheet` | exam | grading | 一名学生对一份试卷的一次作答 |
| 评分结果 | `GradeResult` | grading | grading、学生 | 一道题在答卷上的 AI 建议分与教师确认分 |

**不单独建实体**：成绩是答卷上各题 `GradeResult.reviewedScore` 的汇总，通过计算得到，不允许独立维护一份「成绩表」造成双写。

---

## 2. 实体字段

### 2.1 题目 `Question`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 题目唯一标识（格式第 8 周 ADR 确定） |
| `type` | enum | 是 | `SHORT_ANSWER` / `ESSAY`，仅此两种 |
| `stem` | text | 是 | 题干 |
| `referenceAnswer` | text | 是 | 参考答案与要点，供 AI 评分参考 |
| `rubric` | `RubricItem[]` | 是 | 至少 1 项；分值之和必须等于 `totalScore` |
| `totalScore` | int | 是 | 题目分值，等于评分点分值之和 |
| `status` | enum | 是 | `DRAFT` / `ACTIVE` / `ARCHIVED`；只有 `ACTIVE` 可被组卷 |
| `createdBy` | string | 是 | 创建教师 ID |
| `createdAt` / `updatedAt` | datetime | 是 | 服务端时间 |

### 2.2 评分点 `RubricItem`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 评分点唯一标识 |
| `questionId` | string | 是 | 所属题目 |
| `description` | text | 是 | 得分要点，可独立判定 |
| `score` | int | 是 | 该点分值，≥ 0 |
| `order` | int | 是 | 展示与输出顺序，从 1 开始 |

锁定规则：

1. 同一题内评分点 `score` 之和必须等于题目 `totalScore`，否则拒绝保存（`RUBRIC_SCORE_MISMATCH`）。
2. 一个评分点只描述一个可判定要点；禁止「以及」「等等」「酌情」「其他合理」这类不可判定表述。**校验时点**：保存题目时由 qbank 做禁用词检查，命中返回 409 `RUBRIC_DESCRIPTION_VAGUE`；语义上是否真的可判定，由 module-01-qbank 的 spec 评审与冷启动确认。
3. MVP1 采用**二值判定**：命中得满分，未命中得 0 分；需要部分得分时，由教师把评分点拆细，而不是引入区间分。

### 2.3 试卷 `Paper`（= 考试）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 试卷唯一标识 |
| `title` | string | 是 | 试卷名称 |
| `items` | `PaperItem[]` | 是 | 有序题目列表，至少 1 项 |
| `totalScore` | int | 是 | 等于各题 `Question.totalScore` 之和 |
| `status` | enum | 是 | `DRAFT` / `PUBLISHED` / `CLOSED` |
| `startAt` | datetime | 发布时必填 | 考试开始时间 |
| `endAt` | datetime | 发布时必填 | 考试截止时间，必须晚于 `startAt` |
| `publishedAt` | datetime | 发布时必填 | 实际发布时间 |
| `createdBy` | string | 是 | 创建教师 ID |

`PaperItem`：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `questionId` | string | 是 | 引用的题目 |
| `order` | int | 是 | 试卷内顺序，从 1 开始 |
| `score` | int | 是 | 该题在试卷中的分值，**必须等于题目 `totalScore`** |

锁定规则：

1. MVP1 **不允许在组卷时改写单题分值**；如需不同分值，先修改题目并重新组卷。
2. 一份试卷只形成一场考试，不设独立考试实体；复用试卷发布多场属于 MVP2。
3. 试卷 `PUBLISHED` 后，**试卷结构、每题分值与时间窗口不可修改**（MVP1）；题目本体与评分点是否允许修改、历史试卷与答卷取哪一版数据，由 C-01 决定。

### 2.4 答卷 `AnswerSheet`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 答卷唯一标识 |
| `paperId` | string | 是 | 所属试卷 |
| `studentId` | string | 是 | 作答学生；同一试卷同一学生只能有一份答卷 |
| `answers` | `Answer[]` | 是 | 各题作答内容 |
| `status` | enum | 是 | `DRAFT` / `SUBMITTED` |
| `startedAt` | datetime | 是 | 开始作答时间（服务端） |
| `submittedAt` | datetime | 交卷后必填 | 交卷时间（服务端） |
| `submitType` | enum | 交卷后必填 | `MANUAL` / `AUTO` |
| `finalScore` | int | 否 | 成绩发布后由各题 `reviewedScore` 汇总，不允许提前写入 |

`Answer`：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `questionId` | string | 是 | 对应试卷中的题目 |
| `content` | text | 是 | 学生作答文本，允许为空字符串 |
| `savedAt` | datetime | 是 | 最近一次保存时间（服务端） |

锁定规则：

1. 草稿自动保存可反复覆盖，以服务端收到的最后一次为准。
2. 交卷后答卷只读；再次交卷返回 409 `EXAM_ALREADY_SUBMITTED`。
3. 到 `endAt` 仍未交卷，由服务端自动交卷：`status=SUBMITTED`、`submitType=AUTO`、`submittedAt=endAt`。

### 2.5 评分结果 `GradeResult`

一道题一行，`(answerSheetId, questionId)` 唯一。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 评分结果唯一标识 |
| `answerSheetId` | string | 是 | 所属答卷 |
| `questionId` | string | 是 | 所属题目 |
| `aiStatus` | enum | 是 | `NOT_STARTED` / `PENDING` / `SUCCEEDED` / `FAILED` |
| `rubricHits` | `RubricHit[]` | AI 成功时必填 | 逐评分点命中情况 |
| `aiScore` | int | AI 成功时必填 | 建议分，等于各命中评分点得分之和；不得超出 `[0, 题目分值]` |
| `aiReason` | text | AI 成功时必填 | 整体评分说明 |
| `reviewedScore` | int | 复核后必填 | 教师确认分，`[0, 题目分值]` |
| `reviewComment` | text | 否 | 复核意见，学生可见 |
| `reviewedBy` | string | 复核后必填 | 复核教师 ID |
| `reviewedAt` | datetime | 复核后必填 | 复核时间 |

`RubricHit`：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `rubricItemId` | string | 是 | 对应评分点 |
| `hit` | boolean | 是 | 是否命中 |
| `score` | int | 是 | 该点得分，二值规则下为 0 或评分点分值 |
| `reason` | text | 是 | 命中/未命中的依据 |

锁定规则：

1. `aiScore` 是**建议分**，未经复核不得作为正式成绩。
2. 复核时保留 `aiScore` 原值，只写 `reviewedScore`，实现「留痕」。
3. `AI_FAILED` 时允许教师直接填写 `reviewedScore`，不阻塞整场流程。
4. 学生端不展示 `aiScore`、`aiReason`、`rubricHits`，只展示 `reviewedScore` 与 `reviewComment`。

---

## 3. 状态机

### 3.1 试卷 / 考试

```
DRAFT ──发布──► PUBLISHED ──到达 endAt──► CLOSED
```

| 迁移 | 触发者 | 前置条件 | 失败行为 |
| --- | --- | --- | --- |
| DRAFT → PUBLISHED | 教师（exam） | 至少 1 题；每题评分点分值合计正确；`startAt < endAt`；总分一致 | 409 `EMPTY_PAPER` / `PAPER_SCORE_MISMATCH` / `INVALID_EXAM_WINDOW` |
| PUBLISHED → CLOSED | 系统（服务端时间） | 到达 `endAt` | 无需人工操作 |

### 3.2 答卷

```
DRAFT ──交卷（手动/自动）──► SUBMITTED
```

| 迁移 | 触发者 | 前置条件 | 失败行为 |
| --- | --- | --- | --- |
| 创建 DRAFT | 学生 | 考试 `PUBLISHED` 且在窗口内 | 403 `EXAM_NOT_STARTED` / `EXAM_CLOSED` |
| DRAFT → SUBMITTED | 学生 / 系统 | 窗口内且未交卷 | 409 `EXAM_ALREADY_SUBMITTED` |

### 3.3 单题评分

```
NOT_STARTED ──教师触发──► PENDING ──AI 成功──► SUCCEEDED ──教师复核──► 已写 reviewedScore
                                └──AI 失败──► FAILED ──教师人工复核──► 已写 reviewedScore
```

### 3.4 成绩

```
NOT_READY ──整场所有答卷所有题已复核──► READY ──教师发布──► PUBLISHED
```

| 迁移 | 触发者 | 前置条件 | 失败行为 |
| --- | --- | --- | --- |
| NOT_READY → READY | 系统 | 该试卷下所有 `SUBMITTED` 答卷的每道题均有 `reviewedScore` | — |
| READY → PUBLISHED | 教师（grading） | 当前状态为 READY | 409 `GRADE_NOT_FULLY_REVIEWED` |

---

## 4. 跨模块传递

| 方向 | 传递内容 | 约束 |
| --- | --- | --- |
| qbank → exam | 已发布试卷：题目 ID、顺序、分值、时间窗口 | exam 不得修改题目与评分点 |
| qbank → grading | 题目、评分点（`RubricItem[]`） | grading 不得自行重算分值 |
| exam → grading | 状态为 `SUBMITTED` 的答卷与答案 | 未交卷答卷不进入评分 |
| grading → 学生端 | 已发布成绩：每题 `reviewedScore` + `reviewComment` | 未发布前一律不可见 |
| grading → 教师端 | `rubricHits`、`aiScore`、`aiReason` | 仅该试卷的创建教师可见 |

---

## 5. 统一错误码

| 错误码 | HTTP | 场景 | 产生模块 |
| --- | --- | --- | --- |
| `UNAUTHORIZED` | 401 | 未登录或 JWT 失效 | 集成 |
| `FORBIDDEN` | 403 | 越权访问非本人资源 | 全部 |
| `QUESTION_NOT_FOUND` | 404 | 题目不存在 | qbank |
| `RUBRIC_SCORE_MISMATCH` | 409 | 评分点分值之和不等于题目分值 | qbank |
| `RUBRIC_DESCRIPTION_VAGUE` | 409 | 评分点描述含「以及/等等/酌情/其他合理」等不可判定表述 | qbank |
| `EMPTY_PAPER` | 409 | 试卷无题目即发布 | exam |
| `PAPER_SCORE_MISMATCH` | 409 | 试卷总分与各题分值之和不一致 | exam |
| `INVALID_EXAM_WINDOW` | 409 | 开始时间不早于截止时间 | exam |
| `EXAM_NOT_STARTED` | 403 | 未到开始时间作答 | exam |
| `EXAM_CLOSED` | 403 | 已过截止时间仍尝试作答 | exam |
| `ANSWER_SHEET_NOT_FOUND` | 404 | 答卷不存在 | exam |
| `EXAM_ALREADY_SUBMITTED` | 409 | 重复交卷 | exam |
| `AI_SERVICE_TIMEOUT` | 502 | DeepSeek 超时 | grading |
| `AI_OUTPUT_INVALID` | 502 | AI 返回无法解析或评分点对不上 | grading |
| `AI_SCORE_OUT_OF_RANGE` | 502 | AI 分数越界 | grading |
| `GRADE_NOT_FULLY_REVIEWED` | 409 | 未完成整场复核即发布成绩 | grading |
| `SCORE_NOT_PUBLISHED` | 403 | 成绩未发布，学生查询 | grading |

约定：所有错误响应体必须包含 `code`（上表错误码）与 `message`（人类可读），不得出现空响应体；禁止用 200 表示失败。

---

## 6. 权限与可见性

| 资源 | 学生 | 教师 |
| --- | --- | --- |
| 题目 / 评分点 | 作答时可见题干，**不可见评分点与参考答案** | 仅本人创建 |
| 试卷 / 考试 | 仅已发布且在参与范围内 | 仅本人创建 |
| 答卷 | 仅本人 | 仅本人试卷的答卷 |
| AI 结果（`aiScore`/`aiReason`/`rubricHits`） | 不可见 | 仅本人试卷 |
| 成绩（`reviewedScore`/`reviewComment`） | 发布后仅本人可见 | 仅本人试卷 |

---

## 7. 发布前校验规则

| 编号 | 规则 |
| --- | --- |
| R1 | 题目至少 1 个评分点，且评分点分值之和 = 题目分值 |
| R2 | 试卷至少 1 题，总分 = 各题分值之和 |
| R3 | `startAt < endAt`，且发布时 `endAt` 尚未过期 |
| R4 | 同一学生同一试卷只能有一份答卷 |
| R5 | 交卷幂等：重复请求不得生成第二份答卷或改变已交卷内容 |
| R6 | AI 输出必须通过结构校验：评分点 ID 全匹配、分数在范围内，否则标记 `AI_OUTPUT_INVALID`，不得部分采纳 |
| R7 | 成绩发布前，该试卷所有 `SUBMITTED` 答卷的每道题必须已有 `reviewedScore` |

---

## 8. 留给第 8 周 ADR 的未决项

> 第 7 周的分工是：`qbank` 负责试卷与题目定义，`exam` 负责交卷与考试窗口，`grading` 负责 AI 调用与复核。下表按该分工标注归属，避免把不同模块的未决项混在一条。

| 编号 | 未决问题 | 归属 | 说明 |
| --- | --- | --- | --- |
| C-01 | 已发布试卷与题目之间是引用还是快照？若用快照，保存哪些字段？题目后续修改后，历史试卷、答卷、评分结果取哪一版数据？ | qbank + 集成 | 已发布试卷自身不可改；本条只解决「题目本体改动后历史数据如何保持一致」，不是重复确认冻结策略 |
| C-02 | ID 格式与生成方式 | 集成 | UUID / 雪花 / 自增，本契约暂不约束 |
| C-03 | 并发交卷与自动交卷的幂等实现：唯一索引、状态条件更新还是加锁 | exam | 手动交卷与到点自动交卷同时到达时，只允许一次状态迁移；对应 `EXAM_ALREADY_SUBMITTED` |
| C-04 | AI 输出 JSON 的具体字段名 | grading | 本契约只约束逻辑字段，物理 schema 在第 8 周固化 |
| C-05 | 成绩发布职责归属 | 集成 + grading | 本契约暂定 grading；若第 8 周调整，须同步 `plans/module-ownership.md` |
| C-06 | AI 调用幂等与重试策略：同一答卷同一题重复触发时是否复用已有结果，失败重试几次、结果与状态如何落库 | grading | 无 Redis，需在 MySQL 记录调用状态；不得重复调用已成功的结果，也不得覆盖已复核分数 |

---

## 9. 变更记录

| 版本 | 日期 | 变更人 | 变更内容 |
| --- | --- | --- | --- |
| v0.1 | 2026-11-10 | 李昕彤 | 建立契约：5 个实体、4 组状态机、错误码、权限矩阵、校验规则；固化四项组内决策 |
| v0.1-r1 | 2026-11-10 | 李昕彤 | 评审修订：C-03 拆出 AI 调用幂等并新增 C-06（归属 grading）、C-03 限定为 exam 的交卷幂等；C-01 重定义为题目引用/快照与历史数据一致性；补充评分点表述校验时点与 `RUBRIC_DESCRIPTION_VAGUE` |
