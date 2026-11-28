# 跨模块契约 v0.3（grading 评审稿）

| 项目 | 内容 |
| --- | --- |
| 状态 | 草稿：集成负责人已确认候选规则，待 grading / exam 模块评审；未冻结 |
| 日期 | 2026-11-28 |
| 负责人 | 集成与契约（评审稿）；grading / exam 评审待定 |
| 关联 | `spec/module-03-grading.md` v0.3；`adr/ADR-003-grading-ai-invocation-and-idempotency.md`；[#33](https://github.com/AI-exam-team/ai-exam-system/issues/33) |
| API 定义 | [`openapi.yaml`](./openapi.yaml)，当前覆盖 grading endpoints |

本文升级 `contract-v0.2.md`，并明确覆盖 `contract-v0.1.md` 中 grading 相关的路径、错误映射和发布规则。经相关模块评审后，状态才可改为“已冻结”。

## 1. AI 初评与触发粒度

- MVP1 使用同步 HTTP。单题初评成功返回 200 `GradeResult`；不使用 202 或轮询端点。
- API 按单个 `(answerSheetId, questionId)` 触发和重试。整卷操作由前端逐题调用并分别显示进度与失败，不提供批量端点。
- 每个键最多 3 次实际模型调用；每个 HTTP 请求最多自动重试 1 次，且只对可重试网络故障执行。成功结果永久复用；已成功、PENDING 冲突和请求前置校验失败不增加调用次数。
- 重复触发规则：SUCCEEDED 返回已有结果；PENDING 返回 409 `AI_GRADING_IN_PROGRESS`；额度耗尽返回 409 `AI_ATTEMPT_LIMIT_REACHED`；NOT_STARTED / FAILED 且仍有额度时可启动一次新尝试。
- 后端模型调用超时 30 秒，前端请求超时 65 秒。SP-01 的 21 次真实调用仅作为小样本延迟与结构观察；PR #52 的证据评审尚未完成，不据此宣称准确率或广泛可靠性已验证。

## 2. AI 输出校验与错误优先级

1. JSON 无法解析、必需字段缺失、类型错误、评分点 ID 缺失 / 重复 / 陌生、命中与评分点分值不一致，或逐点合计与 `aiScore` 不一致：整题拒绝，返回 502 `AI_OUTPUT_INVALID`。
2. 分数字段可解析且类型正确，但 `aiScore` 或逐点分数超出允许范围：返回 502 `AI_SCORE_OUT_OF_RANGE`。越界检查优先于分值合计一致性检查。
3. AI 超时返回 502 `AI_SERVICE_TIMEOUT`；其他最终上游故障（包括限流或连接失败）返回 502 `AI_SERVICE_UNAVAILABLE`。
4. 任何 AI 失败都将当前尝试记为 FAILED，不保存可用建议分、不自动记 0、不修改教师确认分。失败后仍可人工复核；额度未耗尽时可再次请求。

## 3. 人工复核

- 只有本人创建试卷的教师可复核；答卷必须为 SUBMITTED，试卷成绩尚未发布。
- NOT_STARTED、PENDING、SUCCEEDED、FAILED 均可人工复核。`reviewedScore` 为 `[0, questionScore]` 内整数；0 是有效确认分。`reviewComment` 可选。
- 发布前允许更新当前确认分；服务端保留 AI 建议原值，并记录最新 `reviewedBy`、`reviewedAt` 与 `reviewComment`。完整复核历史及“采纳 / 修改 / 驳回”动作记录不属于此版要求。
- 若教师在 AI 为 PENDING 时完成复核，服务端以条件更新将该尝试标记为 FAILED / `AI_RESULT_DISCARDED`；迟到响应返回 409 `AI_RESULT_DISCARDED`，不得覆盖确认分或 AI 建议。
- 空答案允许像其他答案一样请求 AI；AI 返回 0 仍须教师确认，空答案不能被系统自动视为已复核。

## 4. 成绩发布

- 只有 Paper 状态为 CLOSED、至少存在一份 SUBMITTED 答卷，且所有已提交答卷的所有题目均有有效 `reviewedScore` 时，允许发布。
- 未满足前置条件时分别返回 409 `PAPER_NOT_CLOSED`、`NO_SUBMITTED_ANSWER_SHEETS` 或 `GRADE_NOT_FULLY_REVIEWED`。不得先对部分学生发布。
- 发布后确认分与学生可见成绩锁定；MVP1 不支持撤回、修改已发布成绩或重新发布修订结果。
- 每张试卷最多一条 grading 自有 `GradePublication` 记录，含唯一 `paperId`、`publishedAt`、`publishedBy`。记录不存在表示未发布；READY 由 Paper 状态、已提交答卷和逐题确认分推导，不单独存储。
- 重复发布请求返回 200 和原 `publishedAt`，不得创建第二条记录或改变成绩。学生查询是否已发布以 `GradePublication` 记录为准，不使用 `Paper.status` 或 `finalScore` 推断。
- `finalScore` 在发布响应 / 学生查询时由逐题 `reviewedScore` 汇总，不另存成绩副本。

## 5. 评分与发布实体

### GradeResult

每道题一条记录，唯一键为 `(answerSheetId, questionId)`。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `id` | string | 评分记录 ID |
| `answerSheetId` | string | 所属已提交答卷 |
| `questionId` | string | 对应试卷题目 |
| `aiStatus` | enum | `NOT_STARTED` / `PENDING` / `SUCCEEDED` / `FAILED` |
| `rubricHits` | `RubricHit[]` | 成功建议；未成功时为空数组 |
| `aiScore` | integer nullable | AI 建议分，不是正式成绩 |
| `aiReason` | string nullable | 整体建议理由 |
| `reviewedScore` | integer nullable | 教师确认分；0 表示已复核 |
| `reviewedBy` | string nullable | 认证身份对应的教师 ID |
| `reviewedAt` | datetime nullable | 服务端复核时间 |
| `reviewComment` | string nullable | 学生可见的教师意见 |

每个评分点的 `RubricHit` 包含 `rubricItemId`、`hit`、`score` 和 `reason`。每个评分点必须恰好出现一次；`hit=true` 得该点满分，`hit=false` 得 0。

以下调用审计字段仅由服务端持久化，默认不出现在 `GradeResult` API 响应，也不返回给学生：`modelName`、`promptVersion`、脱敏后的 `rawResponse`、`attemptCount`、`lastErrorCode`、`requestedBy`、`requestedAt`、`currentAttempt`。`currentAttempt` 用于丢弃过期或已被人工复核取代的调用结果。

### GradePublication

每张试卷最多一条记录：`paperId`（唯一）、`publishedAt`（服务端时间）、`publishedBy`（认证教师 ID）。发布后记录不可由 MVP1 API 更新或删除。

## 6. 错误响应

错误体包含 `code` 与人类可读的 `message`，可包含 `requestId`。JWT 缺失 / 无效返回 401；资源越权返回 403；业务冲突不使用 200 伪装失败。

| HTTP | code | 触发条件 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 路径或请求格式错误 |
| 400 | `INVALID_REVIEWED_SCORE` | 确认分缺失、非整数或超出题目分值 |
| 401 | `UNAUTHORIZED` | JWT 缺失、无效或过期 |
| 403 | `FORBIDDEN` | 角色不符或资源越权 |
| 403 | `SCORE_NOT_PUBLISHED` | 学生成绩尚未发布 |
| 404 | `PAPER_NOT_FOUND` | 试卷不存在 |
| 404 | `ANSWER_SHEET_NOT_FOUND` | 答卷不存在或学生没有本人已提交答卷 |
| 404 | `QUESTION_NOT_FOUND` | 题目不属于该答卷的试卷 |
| 409 | `ANSWER_NOT_SUBMITTED` | 对 DRAFT 答卷请求 AI 初评或人工复核 |
| 409 | `AI_GRADING_IN_PROGRESS` | 同一题已有 PENDING 尝试 |
| 409 | `AI_ATTEMPT_LIMIT_REACHED` | 三次实际调用额度用尽且无成功结果可复用 |
| 409 | `AI_RESULT_DISCARDED` | 迟到响应对应尝试已失效或已被人工复核取代 |
| 409 | `PAPER_NOT_CLOSED` | 试卷尚未 CLOSED 即请求发布成绩 |
| 409 | `NO_SUBMITTED_ANSWER_SHEETS` | 没有已提交答卷时请求发布成绩 |
| 409 | `GRADE_NOT_FULLY_REVIEWED` | 存在未确认题目时请求发布 |
| 409 | `GRADES_ALREADY_PUBLISHED` | 成绩发布后请求改变评分或再次触发 AI |
| 502 | `AI_SERVICE_TIMEOUT` | 最终失败原因为模型超时 |
| 502 | `AI_SERVICE_UNAVAILABLE` | 最终失败原因为非超时上游故障 |
| 502 | `AI_OUTPUT_INVALID` | JSON、字段、映射或评分一致性校验失败 |
| 502 | `AI_SCORE_OUT_OF_RANGE` | 可解析的 AI 分数超出允许范围 |

前置校验失败时不调用模型、不写评分状态。模型调用失败记下对应尝试与审计字段；失败结果不能覆盖已有教师确认分。

## 7. 评审状态

本版本记录集成负责人的候选选择；grading 组需确认单题接口、重试和审计字段，exam 组需确认 `Paper.CLOSED` 与已提交答卷计数的读取契约。上述评审完成前，v0.3 和 OpenAPI 为评审草案，不是冻结实现依据。

## 8. 变更记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| v0.3 | 2026-11-28 | 明确同步初评、逐题接口、错误优先级、空答案和人工复核、成绩发布边界及发布记录；待 grading / exam 组评审 |
