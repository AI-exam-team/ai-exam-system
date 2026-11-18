# 跨模块契约 v0.2（grading 增量草案）

状态：待集成、grading 与受影响模块评审，接口暂不冻结。
关联 [Issue #33](https://github.com/AI-exam-team/ai-exam-system/issues/33)。本文拟补充 [v0.1](contract-v0.1.md)，其余规则沿用 v0.1。

## 快照定位

grading 使用答卷确定的 paperId 与试卷内 questionId 查询 qbank。两者均为 string，并随 QuestionForGrading 返回。采用快照时，只读取对应组合键的试卷快照。

## 错误响应

错误响应体至少包含 `code: string` 与 `message: string`，并可包含统一响应约定中的 `requestId`。身份来自 JWT。先鉴权和验证归属，再执行操作。

| HTTP | code | 触发条件 |
| --- | --- | --- |
| 400 | VALIDATION_ERROR | 路径或请求格式非法，确认分专用错误优先 |
| 400 | INVALID_REVIEWED_SCORE | 教师确认分缺失、非整数或超出题目分值范围 |
| 401 | UNAUTHORIZED | JWT 缺失、无效或过期 |
| 403 | FORBIDDEN | 角色不符或资源越权 |
| 403 | SCORE_NOT_PUBLISHED | 本人已提交答卷的成绩尚未发布 |
| 404 | PAPER_NOT_FOUND | 请求的试卷不存在 |
| 404 | ANSWER_SHEET_NOT_FOUND | 答卷不存在，或本人没有该场已提交答卷 |
| 404 | QUESTION_NOT_FOUND | 题目不属于答卷对应试卷 |
| 409 | ANSWER_NOT_SUBMITTED | 对草稿答卷请求初评或复核 |
| 409 | AI_GRADING_IN_PROGRESS | 已有正在进行的初评 |
| 409 | AI_ATTEMPT_LIMIT_REACHED | 三次实际调用额度用尽且无成功结果可复用 |
| 409 | AI_RESULT_DISCARDED | 回写时已人工复核或尝试号失效 |
| 409 | GRADE_NOT_FULLY_REVIEWED | 存在未复核题目时请求发布 |
| 502 | AI_SERVICE_TIMEOUT | 最终失败原因为模型超时 |
| 502 | AI_SERVICE_UNAVAILABLE | 最终失败原因为非超时上游故障 |
| 502 | AI_OUTPUT_INVALID | JSON、字段类型、评分点映射或 scoring 一致性校验失败 |
| 502 | AI_SCORE_OUT_OF_RANGE | 结构可校验但分数越界 |

请求前置校验（鉴权、资源归属、请求格式及业务前置条件）失败时，不启动模型调用，也不写入评分业务状态。模型调用已受理后，按结构与映射、分数范围、命中与合计一致性的顺序校验模型输出，统一 v0.1 R6 对越界的映射。模型输出校验失败时，记录该次尝试与审计信息；最终失败将 aiStatus 置为 FAILED，不采纳该题的 AI 建议分，也不覆盖教师确认分。迟到或失效结果只记录该次尝试，不覆盖当前状态和确认分。

## 审计字段

| 字段 | 类型 | 来源与语义 |
| --- | --- | --- |
| modelName | string nullable | 实际调用的模型配置 |
| promptVersion | string nullable | 实际使用的提示词版本 |
| rawResponse | string nullable | 脱敏后的模型输出正文，无响应时为空 |
| attemptCount | integer | 单答卷单题累计实际调用次数，初始 0，上限 3，首次、自动重试、人工再触发的调用均计入 |
| lastErrorCode | string nullable | 最新实际调用的失败码，无失败或最新调用成功时为空 |
| requestedBy | string nullable | 发起本次调用的教师 JWT subject |
| requestedAt | datetime nullable | 发起本次调用的服务端时间 |

每次调用前原子占用一次额度，记录尝试号并用于回写保护。审计字段为持久化契约，不默认暴露在 GradeResult HTTP 响应中。学生不可见，原始响应若需提供给教师，只允许试卷创建教师查看脱敏内容。

G-01、G-02、G-04 及 ADR-003 的 SP-01 实测阈值仍待确认。
