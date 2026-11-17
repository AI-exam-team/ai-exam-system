# 架构基线（architecture.md）

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.1 |
| 状态 | 草稿（待三组评审） |
| 日期 | 2026-11-17 |
| 负责人 | 李昕彤（集成与契约） |
| 关联任务 | 第 8 周架构设计 |
| 依据 | `context.md` v0.1；`spec/mvp1-scope.md` v0.1；`spec/contract-v0.1.md`；`spec/module-01-qbank.md` v0.2；`spec/module-02-exam.md` v0.2；`spec/module-03-grading.md` v0.2（评审中，尚未合入） |
| 评审人 | qbank：孙宇萱、周裔；exam：钱斓轩；grading：左恩东、王麒博 |

> 本文件是第 8 周架构基线，回答「模块怎么分、谁依赖谁、接口长什么样、失败时发生什么」。
> 本文件**不包含业务生产代码**；模块内部类名、UI 样式、索引优化不属于冻结范围。
> 冻结项变更（模块边界、接口契约、依赖方向、关键 ADR）必须新增 ADR 留痕，见第 8 节。
>
> **分工边界**：第 5～7 节由集成负责人维护；各模块的请求/响应字段细节由模块组在对应小节补充并确认。错误码以 `spec/contract-v0.1.md` 第 5 节为准；本文新增的错误码在第 5.1 节单独标注，契约升版前不生效。

---

## 1. 架构目标与红线

**目标**：让第 9 周每个任务都能回答三个问题——改哪个模块、调哪个接口、依赖谁。

**红线**（与第 8 周课程要求一致）：

1. 不写业务生产代码，`src/` 保持占位。
2. 技术探针只放 `docs/spike/`，不合并进 `src/`。
3. 接口契约必须同时写成功与失败；禁止用 HTTP 200 表示业务失败。
4. 展示层不判断业务规则，API 层不写业务规则，数据层不处理 UI。
5. 模块之间只通过契约调用，禁止直接读写其他模块的表或内部类。

---

## 2. 模块划分与职责

| 模块 | 职责 | 明确不负责 | 依据 |
| --- | --- | --- | --- |
| `qbank` 题库与组卷 | 题目与评分点维护；组卷为 `DRAFT` 试卷；分值一致性校验 | 考试发布、时间窗口、作答、AI 评分、成绩发布 | `module-01-qbank.md` v0.2 |
| `exam` 在线考试与答卷 | 发布考试（`DRAFT → PUBLISHED`）；窗口控制；进入考试；草稿保存；手动/自动交卷 | 题目与评分点维护；调用 DeepSeek；教师复核；成绩发布 | `module-02-exam.md` v0.2 |
| `grading` AI 阅卷与复核 | 接收 `SUBMITTED` 答卷；AI 初评与结构校验；教师逐题复核；整场发布成绩；学生查询本人成绩 | 组卷；考试发布与计时；修改已交卷答案 | `module-03-grading.md` v0.2（评审中） |
| `integration` 集成与契约（横切） | 登录与 JWT；统一错误码与响应；`AIService` 收口；跨模块契约；端到端联调 | 不代替模块实现业务规则 | `mvp1-scope.md` 3.3 |

### 2.1 边界判断练习

| 判断 | 结论 | 原因 |
| --- | --- | --- |
| 交卷页根据浏览器本地时间判断是否截止 | ✗ | 窗口判定必须用服务端时间，属于 `exam` 服务层 |
| `qbank` 在组卷时读取答卷表统计参考人数 | ✗ | 反向依赖 + 跨模块读表 |
| `exam` 交卷后直接调用 DeepSeek 给分 | ✗ | AI 调用属于 `grading` |
| `grading` 通过 `exam` 的已提交答卷查询接口取答案 | ✓ | 正向依赖，走契约 |
| `exam` 发布时调用 `qbank` 的试卷查询接口做发布校验 | ✓ | 正向依赖，只读 |
| 结果页把 `reviewedScore` 是否为空翻译成「待复核」 | ✓ | 展示层只消费响应，不判断规则 |

---

## 3. 分层架构

```
展示层  Vue 3（Composition API + Vite）    页面、交互、倒计时展示
   │    HTTP + JSON + JWT
   ▼
API 层  Spring Boot Controller             路由、参数校验、鉴权、统一响应
   │
   ▼
服务层  Service / 领域规则                  业务规则、事务、状态迁移
   │
   ▼
数据层  Repository + MySQL 8               持久化、唯一约束、条件更新

横切：JWT 鉴权 · 统一错误码 · 日志 · AIService（仅后端持有 DeepSeek Key）
```

约束：

- **展示层**：只消费 API 响应；倒计时仅展示，是否超时以服务端返回为准。禁止在前端拼接业务判定。
- **API 层**：只做身份、参数与权限校验，不写借阅/考试规则；`studentId`、`reviewedBy` 等身份字段一律取自 JWT，不接受请求体伪造。
- **服务层**：承载规则与事务（发布校验、交卷幂等、复核、成绩发布）。AI 调用统一经 `AIService`。
- **数据层**：不感知 UI 与 HTTP；唯一性与幂等由数据库约束 + 条件更新保证。
- 单体应用，按模块分包：`src/modules/qbank/`、`src/modules/exam/`、`src/modules/grading/`；公共能力在 `src/main/`；前端在 `src/frontend/`。

---

## 4. 模块依赖

### 4.1 依赖方向

```
qbank  ◄──── exam  ◄──── grading
   ▲                         │
   └───────────┬─────────────┘
               │ 只读评分点
```

读法：箭头指向被依赖方，`exam → qbank` 表示 exam 依赖 qbank 提供的试卷与题目查询能力。

| 消费方 | 被依赖方 | 用途 | 约束 |
| --- | --- | --- | --- |
| `exam` | `qbank` | 读取 `DRAFT/PUBLISHED` 试卷、题目分值 | 只读，不修改题目与评分点 |
| `grading` | `exam` | 读取 `SUBMITTED` 答卷与答案 | 只读，不改变答案、提交方式与时间 |
| `grading` | `qbank` | 读取题干、参考答案、评分点 | 只读，不重算评分点分值 |
| 各模块 | `integration` | JWT 身份、统一错误码、`AIService` | 横切能力，不得反向依赖业务模块 |

规则：

1. 单向依赖，禁止循环；`qbank` 不得依赖 `exam` 或 `grading`。
2. 禁止展示层直连数据层。
3. 禁止跨模块直接读写表；跨模块只走第 6 节的契约。
4. `integration` 是下层公共能力，不得依赖任何业务模块的服务层。
5. 依赖方向变更必须先改本文件并新增 ADR。

### 4.2 循环依赖自查

- [ ] `qbank` 无对 `exam` / `grading` 的 import 或 SQL。
- [ ] `exam` 对 `qbank` 只有读接口调用。
- [ ] `grading` 对 `exam` / `qbank` 只有读接口调用。
- [ ] 没有通过共享表绕过依赖方向。

---

## 5. 统一接口规范（集成层约定，评审后冻结）

| 项 | 约定 |
| --- | --- |
| 基础路径 | `/api/v1` |
| 数据格式 | JSON，UTF-8；请求/响应均不含 HTML |
| 鉴权 | `Authorization: Bearer <JWT>`；身份与角色取自令牌，不接受请求体传入 |
| 时间 | ISO-8601 带时区，例：`2026-11-17T09:00:00+08:00`；所有时间以服务端为准 |
| ID | 统一为字符串；具体生成方式由 ADR 决定（C-02 未决） |
| 成功响应 | 单资源直接返回对象；列表返回数组；创建成功用 `201` |
| 失败响应 | `{ "code": "<错误码>", "message": "<人类可读>", "requestId": "<可选>" }` |
| 禁止 | 用 `200` 表示业务失败；空响应体表示失败；在错误中泄露堆栈、SQL、密钥 |
| 分页 | MVP1 不设计分页；接口若返回列表直接返回数组 |

### 5.1 错误码

既有错误码以 `spec/contract-v0.1.md` 第 5 节为唯一来源。集成层当前只登记以下**需要新增**的错误码（提交契约 v0.2 评审后生效）：

| 错误码 | HTTP | 场景 | 产生模块 | 状态 |
| --- | --- | --- | --- | --- |
| `ANSWER_NOT_SUBMITTED` | 409 | 对 `DRAFT` 答卷触发 AI 初评 | grading | 待契约升版 |
| `AI_GRADING_IN_PROGRESS` | 409 | 同一题初评处于 `PENDING` 时重复触发 | grading | 待契约升版 |
| `INVALID_REVIEWED_SCORE` | 400 | 确认分非整数或不在 `[0, 题目分值]` | grading | 待契约升版 |

> 说明：G-03（错误码补齐）与本表合并处理；契约升版前不得在代码中先使用。

---

## 6. 接口契约清单

> 路径为集成基线建议，模块组在评审时确认；确认后即冻结，变更走 ADR。
> 成功/失败码只列主要分支，完整字段由模块组补充。

### 6.1 集成层（integration）

| 方法 | 路径 | 说明 | 成功 | 主要失败 |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | 账号密码登录，返回 JWT 与角色 | 200 `{ token, role }` | 401 `UNAUTHORIZED`、400 参数缺失 |

### 6.2 题库与组卷（qbank）

| 方法 | 路径 | 说明 | 成功 | 主要失败 |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/questions` | 建题（含评分点） | 201 `Question` | 409 `RUBRIC_SCORE_MISMATCH` / `RUBRIC_DESCRIPTION_VAGUE`、400 |
| PUT | `/api/v1/questions/{id}` | 修改题目 | 200 `Question` | 404 `QUESTION_NOT_FOUND`、409、400 |
| GET | `/api/v1/questions?status=ACTIVE` | 建卷选题 | 200 `Question[]` | 401 |
| POST | `/api/v1/papers` | 组卷，保存 `DRAFT` | 201 `Paper` | 409 `PAPER_SCORE_MISMATCH`、400 |
| GET | `/api/v1/papers/{id}` | 试卷详情 | 200 `Paper` | 404、403 |
| GET | `/api/v1/papers?status=DRAFT` | 待发布试卷列表 | 200 `Paper[]` | 401 |

### 6.3 在线考试与答卷（exam）

| 方法 | 路径 | 说明 | 成功 | 主要失败 |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/papers/{id}/publish` | 发布考试，设置时间窗口 | 200 `Paper` | 409 `EMPTY_PAPER` / `PAPER_SCORE_MISMATCH` / `INVALID_EXAM_WINDOW` |
| GET | `/api/v1/exams?status=AVAILABLE` | 学生可见考试列表 | 200 `ExamSummary[]` | 401 |
| GET | `/api/v1/exams/{paperId}` | 学生进入考试页（不含评分点与参考答案） | 200 `ExamDetail` | 403 `EXAM_NOT_STARTED` / `EXAM_CLOSED`、404 |
| POST | `/api/v1/exams/{paperId}/answer-sheet` | 进入考试，创建或返回本人 `DRAFT` 答卷 | 200/201 `AnswerSheet` | 403 `EXAM_NOT_STARTED` / `EXAM_CLOSED` |
| PUT | `/api/v1/answer-sheets/{id}/answers` | 保存草稿（可批量按题覆盖） | 200 `{ savedAt }` | 409 `EXAM_ALREADY_SUBMITTED`、403、404 `ANSWER_SHEET_NOT_FOUND` |
| POST | `/api/v1/answer-sheets/{id}/submit` | 手动交卷，携带全部答案 | 200 `AnswerSheet` | 409 `EXAM_ALREADY_SUBMITTED`、403、404 |
| GET | `/api/v1/papers/{id}/answer-sheets` | 教师查看本人试卷的答卷 | 200 `AnswerSheetSummary[]` | 403、404 |

### 6.4 AI 阅卷与复核（grading）

| 方法 | 路径 | 说明 | 成功 | 主要失败 |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/papers/{id}/grading-sheets` | 教师查看逐题评分状态 | 200 `GradingSheetView` | 403（非本人试卷）、404 |
| POST | `/api/v1/answer-sheets/{id}/questions/{questionId}/ai-grade` | 触发单题初评（整卷批量=循环调用） | 200 `GradeResult` | 409 `ANSWER_NOT_SUBMITTED` / `AI_GRADING_IN_PROGRESS`、502 `AI_SERVICE_TIMEOUT` / `AI_OUTPUT_INVALID` / `AI_SCORE_OUT_OF_RANGE` |
| PUT | `/api/v1/answer-sheets/{id}/questions/{questionId}/review` | 教师复核并写确认分 | 200 `GradeResult` | 400 `INVALID_REVIEWED_SCORE`、403、404 |
| POST | `/api/v1/papers/{id}/grades/publish` | 整场发布成绩 | 200 `{ publishedAt }` | 409 `GRADE_NOT_FULLY_REVIEWED`、403 |
| GET | `/api/v1/my/grades/{paperId}` | 学生查本人成绩 | 200 `PublishedGrade` | 403 `SCORE_NOT_PUBLISHED`、404 |

> 触发粒度（逐题 vs 整卷）待 G-08 决议；本表按单题幂等键设计，整卷批量不引入新的幂等语义。

### 6.5 跨模块交接数据

跨模块采用**进程内只读接口 + DTO**，不使用事件总线（MVP1 禁止消息队列）。

| 方向 | 数据契约（逻辑字段） | 约束 |
| --- | --- | --- |
| qbank → exam | `PaperForExam { paperId, title, totalScore, items[{questionId, order, score, type, stem}], status }` | 不包含参考答案与评分点；`exam` 发布时重新校验分值 |
| qbank → grading | `QuestionForGrading { questionId, type, stem, referenceAnswer, totalScore, rubric[{rubricItemId, description, score, order}] }` | 只读；题目版本取值待 ADR-001（C-01） |
| exam → grading | `SubmittedSheetForGrading { answerSheetId, paperId, studentId, submittedAt, submitType, answers[{questionId, content}] }` | 仅 `SUBMITTED`；只读，不改变答案与时间 |
| grading → 学生端 | `PublishedGrade { paperId, totalScore, items[{questionId, reviewedScore, reviewComment}] }` | 仅成绩发布后；不返回 `aiScore` / `aiReason` / `rubricHits` |
| grading → 教师端 | `GradingSheetView { answerSheetId, items[{questionId, aiStatus, rubricHits, aiScore, aiReason, reviewedScore, reviewComment, reviewedAt}] }` | 仅试卷创建教师可见 |

**契约字段冻结规则**：上述字段名一旦冻结，模块内部 DTO 可以不同，但跨模块边界必须使用契约字段；改名属于接口变更，需 ADR。

---

## 7. 端到端数据流

### 7.1 成功路径

```
教师登录（integration）
  → 建题（qbank：POST /questions，校验评分点分值和）
  → 组卷（qbank：POST /papers，保存 DRAFT，分值继承）
  → 发布考试（exam：POST /papers/{id}/publish，校验题目/总分/窗口）
  → 学生进入（exam：POST /exams/{paperId}/answer-sheet，窗口内创建 DRAFT）
  → 作答与草稿保存（exam：PUT /answer-sheets/{id}/answers）
  → 手动或自动交卷（exam：POST /submit；SUBMITTED、只读）
  → 教师触发 AI 初评（grading：qbank 取评分点 + exam 取答案 → DeepSeek）
  → 教师逐题复核（grading：PUT .../review，写 reviewedScore，保留 aiScore）
  → 整场发布成绩（grading：POST .../grades/publish，汇总 reviewedScore）
  → 学生查询本人成绩（grading：GET /my/grades/{paperId}）
```

### 7.2 失败路径与不变式

| 失败场景 | 返回 | 必须保持不变 |
| --- | --- | --- |
| 发布时试卷为空 / 总分不一致 / 窗口非法 | 409 对应错误码 | 试卷仍为 `DRAFT`，不写 `publishedAt` |
| 窗口外进入、保存、交卷 | 403 `EXAM_NOT_STARTED` / `EXAM_CLOSED` | 不创建、不修改答卷 |
| 重复交卷（含网络重试、自动交卷竞争） | 409 `EXAM_ALREADY_SUBMITTED` | 答案、`submittedAt`、状态均不变 |
| AI 超时 / 输出不合法 / 分数越界 | 502 对应错误码 | 该题标 `FAILED`，不写 `aiScore`，不自动记 0 分 |
| 未完成整场复核即发布 | 409 `GRADE_NOT_FULLY_REVIEWED` | 不写任何 `finalScore`，学生不可见 |
| 学生查询未发布成绩 | 403 `SCORE_NOT_PUBLISHED` | 不返回任何分值 |
| 越权访问他人答卷 / 成绩 | 403 `FORBIDDEN` | 不泄露资源是否存在及内容 |

**核心不变式**：

1. 失败请求不产生副作用：不新增记录、不改变状态、不提前写 `finalScore`。
2. 交卷幂等：同一学生同一试卷最多一份答卷，只允许一次 `DRAFT → SUBMITTED`。
3. AI 与教师分离：`aiScore` 只是建议，`reviewedScore` 是正式分；复核不得覆盖 `aiScore`。
4. 零分 ≠ 未复核：`reviewedScore = 0` 是有效确认；缺失记录或 null 才表示未复核。
5. 发布原子性：整场成绩要么全部可见，要么全部不可见。
6. 时间权威：考试窗口、保存时间、交卷时间、复核时间一律以服务端为准。

---

## 8. 架构冻结范围

| 冻结（变更走 ADR） | 不冻结（第 10 周可迭代） |
| --- | --- |
| 模块边界与职责、不负责事项 | 模块内部函数、类名、包结构细节 |
| 接口路径、请求/响应字段、错误码 | UI 样式、页面布局、文案 |
| 依赖方向（单向、禁循环、禁跨模块读表） | 框架版本细节、构建脚本 |
| 关键 ADR（交卷幂等、AI 调用、题目版本） | 非关键实现细节、日志格式 |
| 核心实体与字段名（`spec/contract-v0.1.md`） | 索引优化、缓存策略（本期无缓存） |
| 跨模块交接 DTO 字段 | 数据库物理表设计（在契约内自由） |

变更规则：

1. 接口 / 依赖 / 关键 ADR 变更 → 新增 ADR，说明影响面与回滚方式。
2. 契约文件变更走独立 PR，集成负责人 + 受影响模块各 1 人评审。
3. 冻结不是不能改，是改要留证据。

---

## 9. 开放决策与 ADR 映射

| ADR | 主题 | 对应未决项 | 主笔 | 状态 |
| --- | --- | --- | --- | --- |
| ADR-001 | 已发布试卷取题目快照还是引用 | C-01 | 孙宇萱（qbank） | 待提交 |
| ADR-002 | 交卷并发与自动交卷幂等 | C-03 | 钱斓轩（exam） | 待提交 |
| ADR-003 | AI 初评调用、超时重试与幂等 | C-06 | 李昕彤 + grading | 本 PR 提交（提议） |

仍在开放的问题：

| 编号 | 问题 | 负责人 | 计划 |
| --- | --- | --- | --- |
| C-02 | ID 格式（UUID / 雪花 / 自增） | 李昕彤 | 第 8 周 ADR 或架构附录 |
| C-04 | AI 返回 JSON 物理字段与 schema | 王麒博 + 李昕彤 | 随 ADR-003 定稿 |
| G-01 | 成绩发布是否必须等考试 `CLOSED` | 钱斓轩 + 左恩东 + 李昕彤 | 接口冻结前 |
| G-02 | 发布后是否允许改分 / 重复发布语义 | 左恩东 + 李昕彤 | 接口冻结前 |
| G-06 | 成绩发布状态如何存储与判定 | 李昕彤 + 左恩东 | 接口冻结前 |
| TBD-07/08 | 并发与费用上限、JWT 有效期 | 李昕彤 | 第 8 周内给出数值 |

---

## 10. 面向第 9 周的任务拆解映射

| 候选任务 | 改动模块 | 主要接口 | 依赖 |
| --- | --- | --- | --- |
| T1 建题与评分点校验 | qbank | `POST/PUT /questions` | 无 |
| T2 组卷与分值校验 | qbank | `POST /papers` | T1 |
| T3 发布考试与窗口校验 | exam | `POST /papers/{id}/publish` | T2、qbank 试卷查询 |
| T4 学生进入与草稿保存 | exam | `POST /exams/{paperId}/answer-sheet`、`PUT .../answers` | T3 |
| T5 交卷与自动交卷 | exam | `POST .../submit` | T4、ADR-002 |
| T6 AI 初评与输出校验 | grading | `POST .../ai-grade` | T5、qbank 评分点、ADR-003 |
| T7 教师逐题复核 | grading | `PUT .../review` | T6 |
| T8 成绩发布与学生查询 | grading | `POST .../publish`、`GET /my/grades` | T7、G-06 |
| T9 登录、JWT、统一错误处理 | integration | `POST /auth/login` | 无 |
| T10 端到端联调与演示数据 | integration | 全链路 | T1～T9 |

> 第 9 周只拆 MVP1，不拆扩展模块；每个任务必须绑定 spec 的 AC 或边界异常。

---

## 11. 变更记录

| 版本 | 日期 | 变更人 | 变更内容 |
| --- | --- | --- | --- |
| v0.1 | 2026-11-17 | 李昕彤 | 建立架构基线：模块边界、四层架构、单向依赖、统一接口规范、跨模块 DTO、成功/失败数据流、冻结范围、ADR 映射与第 9 周任务映射 |
