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
| `exam` | `qbank` | 读取 `DRAFT/PUBLISHED` 试卷、题目分值；调用 Paper 生命周期受控命令 | 默认只读；`markPublished` / `markClosed` 是唯一受控写命令，不直接写表（ADR-004） |
| `grading` | `exam` | 读取 `SUBMITTED` 答卷与答案 | 只读，不改变答案、提交方式与时间 |
| `grading` | `qbank` | 读取题干、参考答案、评分点 | 只读，不重算评分点分值 |
| 各模块 | `integration` | JWT 身份、统一错误码、`AIService` | 横切能力，不得反向依赖业务模块 |

规则：

1. 单向依赖，禁止循环；`qbank` 不得依赖 `exam` 或 `grading`。
2. 禁止展示层直连数据层。
3. 禁止跨模块直接读写表；跨模块默认只读。`Paper` 的发布/关闭是**唯一的受控写命令组**，由 qbank 实现、exam 调用（ADR-004）；除此之外，exam 不得写 qbank 任何表或字段。
4. `integration` 是下层公共能力，不得依赖任何业务模块的服务层。
5. 依赖方向变更必须先改本文件并新增 ADR。

### 4.2 循环依赖自查

- [ ] `qbank` 无对 `exam` / `grading` 的 import 或 SQL。
- [ ] `exam` 对 `qbank` 只有读接口 + `PaperLifecyclePort` 受控命令，无直接 SQL / Mapper。
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
| `VALIDATION_ERROR` | 400 | 通用参数校验失败（缺字段、类型错误、非法枚举） | integration / 各模块 | 待契约升版 |
| `PAPER_NOT_FOUND` | 404 | 试卷不存在 | qbank / exam | 待契约升版 |
| `PAPER_NOT_DRAFT` | 409 | 试卷当前状态不是 `DRAFT`（重复发布或已关闭） | qbank（经 exam 返回） | 待契约升版 |
| `QUESTION_NOT_ACTIVE` | 409 | 组卷引用非 `ACTIVE` 题目 | qbank | 待契约升版 |
| `QUESTION_ALREADY_USED` | 409 | 题目被任一 `PUBLISHED` 试卷引用，禁止修改 | qbank | 待契约升版 |
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
| POST | `/api/v1/questions` | 建题（含评分点） | 201 `Question` | 409 `RUBRIC_SCORE_MISMATCH` / `RUBRIC_DESCRIPTION_VAGUE`、400 `VALIDATION_ERROR` |
| PUT | `/api/v1/questions/{id}` | 修改题目 | 200 `Question` | 404 `QUESTION_NOT_FOUND`、409 `QUESTION_ALREADY_USED`、400 `VALIDATION_ERROR` |
| GET | `/api/v1/questions?status=ACTIVE` | 建卷选题 | 200 `Question[]` | 401 |
| POST | `/api/v1/papers` | 组卷，保存 `DRAFT` | 201 `Paper` | 409 `PAPER_SCORE_MISMATCH` / `QUESTION_NOT_ACTIVE`、400 `VALIDATION_ERROR` |
| GET | `/api/v1/papers/{id}` | 试卷详情 | 200 `Paper` | 404 `PAPER_NOT_FOUND`、403 |
| GET | `/api/v1/papers?status=DRAFT` | 待发布试卷列表 | 200 `Paper[]` | 401 |
| GET | `/api/v1/papers/{id}/snapshot-diff` | 草稿快照对比（只读） | 200 `SnapshotDiff[]` | 404 `PAPER_NOT_FOUND`、403 |

> 契约第 5 节未覆盖的失败场景，优先使用 5.1 表列出的待登记错误码；契约 v0.2 登记前按提案名使用并注明，不得长期以「契约未覆盖」作为错误码。
> 身份字段（`createdBy`）取自 JWT `subject`，不接受请求体传入；跨模块 DTO 见本文件 6.5 节，本节不重复定义。

---

#### 6.2.1 POST /api/v1/questions — 新建题目（含评分点）

**请求**

| 字段 | 类型 | 必填 | 约束与依据 |
| --- | --- | --- | --- |
| `type` | enum | 是 | `SHORT_ANSWER` / `ESSAY`，仅此两种（contract 2.1） |
| `stem` | text | 是 | 题干（contract 2.1） |
| `referenceAnswer` | text | 是 | 参考答案与要点，供 AI 评分参考，必填（contract 2.1） |
| `totalScore` | int | 是 | 题目分值（contract 2.1） |
| `rubric` | `RubricItem[]` | 是 | 至少 1 项；`score` 之和必须等于 `totalScore`（contract 2.1 / R1） |

`rubric[]` 元素（contract 2.2）：

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `description` | text | 是 | 可独立判定的得分要点，禁止「以及 / 等等 / 酌情 / 其他合理」 |
| `score` | int | 是 | 该点分值，`≥ 0` |
| `order` | int | 是 | 展示顺序，从 1 开始 |

> `id`、`questionId` 由服务端生成，请求体不传。

身份来源：JWT `role=TEACHER`；`createdBy` 取自 JWT `subject`。

**成功 201：`Question`**（字段见 contract 2.1）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 题目唯一标识 |
| `type` | enum | `SHORT_ANSWER` / `ESSAY` |
| `stem` | text | 题干 |
| `referenceAnswer` | text | 参考答案与要点 |
| `rubric` | `RubricItem[]` | 含 `id`、`questionId`、`description`、`score`、`order` |
| `totalScore` | int | 等于各评分点分值之和 |
| `status` | enum | 创建后为 `DRAFT`，可流转 `ACTIVE` / `ARCHIVED`（contract 2.1、AC-1） |
| `createdBy` | string | 取自 JWT `subject` |
| `createdAt` / `updatedAt` | datetime | 服务端时间 |

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | 缺少必填字段；`rubric` 为空数组；`score` 为负；`type` 不属于 `SHORT_ANSWER` / `ESSAY` | 原表 400；contract 2.1 / 2.2 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | JWT 角色不是教师 | contract 第 5 节 |
| 409 | `RUBRIC_SCORE_MISMATCH` | 评分点 `score` 之和 ≠ `totalScore` | contract 第 5 节 / AC-3 |
| 409 | `RUBRIC_DESCRIPTION_VAGUE` | 任一评分点描述含「以及 / 等等 / 酌情 / 其他合理」 | contract 第 5 节 / AC-2 |

**权限**：仅教师（`role=TEACHER`）；`createdBy` 取自 JWT，不接受请求体伪造。

**对应 AC**：`module-01-qbank.md` AC-1 / AC-2 / AC-3

---

#### 6.2.2 PUT /api/v1/questions/{id} — 修改题目

**请求**

- 路径参数：`id` = `Question.id`
- 请求体：字段同 6.2.1，按需传递需修改的字段
- 修改 `totalScore` 时必须整体重传 `rubric`，重新执行「分值之和」与「禁用词」两项校验（contract 2.2 锁定规则 1）

身份来源：JWT `role=TEACHER`。

**成功 200：`Question`**（结构同 6.2.1，`updatedAt` 刷新）

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | 修改后字段类型或取值非法 | 原表 400 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师；或该题 `createdBy` ≠ 当前 JWT `subject`（教师仅能操作本人创建的资源） | contract 第 5、6 节 |
| 404 | `QUESTION_NOT_FOUND` | `id` 不存在 | contract 第 5 节 |
| 409 | `RUBRIC_SCORE_MISMATCH` | 修改后评分点分值之和 ≠ `totalScore` | contract 第 5 节 |
| 409 | `RUBRIC_DESCRIPTION_VAGUE` | 修改后评分点描述含禁用词 | contract 第 5 节 |
| 409 | `QUESTION_ALREADY_USED`（待登记） | 该题已被 `PUBLISHED` 试卷引用，禁止修改以保护历史一致性 | ADR-001 锁题规则 |

**权限**：仅教师，且仅题目创建者本人；已被 `PUBLISHED` 试卷引用的题目禁止修改。

**对应 AC**：`module-01-qbank.md` AC-1（状态流转）；AC-2 / AC-3（修改后重新校验）

---

#### 6.2.3 GET /api/v1/questions — 查询题目列表（建卷选题）

**请求**

| 参数 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `status` | query | enum | 否 | 默认 `ACTIVE`（组卷只选 `ACTIVE`）；可选 `DRAFT` / `ACTIVE` / `ARCHIVED` / `ALL` |

身份来源：JWT；仅返回 `createdBy` = 当前 `subject` 的题目（contract 第 6 节：教师仅本人创建）。

**成功 200：`Question[]`**（字段见 contract 2.1）

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | `status` 取值不在允许范围 | 原表未列，参数校验归 API 层 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师 | contract 第 5 节 |

**权限**：仅教师；仅本人创建的题目。

**对应 AC**：`module-01-qbank.md` AC-4 的前置能力（组卷选题）

---

#### 6.2.4 POST /api/v1/papers — 组卷并保存 `DRAFT`

**请求**

| 字段 | 类型 | 必填 | 约束与依据 |
| --- | --- | --- | --- |
| `title` | string | 是 | 试卷名称（contract 2.3） |
| `questionIds` | string[] | 是 | 至少 1 项；不得重复；每题必须存在且状态为 `ACTIVE`（FR-4）；**数组顺序即 `PaperItem.order`** |

关键约定（contract 2.3 锁定规则 / FR-4）：

1. **不接收** `totalScore`：由系统按各题 `Question.totalScore` 汇总，不接受手工填写。
2. **不接收** 单题 `score`：`PaperItem.score` 必须等于题目 `totalScore`，组卷时不可改写。
3. 保存结果固定为 `DRAFT`，**不写入** `startAt` / `endAt` / `publishedAt`（contract 2.3：发布时必填，由 `exam` 设置）。
4. 组卷时按 ADR-001 在同一事务内写入**基线快照**（题干、参考答案、总分、评分点），供草稿阶段对比；发布时 `exam` 调用 qbank 的 `markPublished` 受控命令，qbank 完成 `DRAFT → PUBLISHED`、写入窗口并冻结正式快照；`exam` 不直接写 qbank 表（ADR-004）。
5. 草稿快照对比见 6.2.7；具体快照行为待 ADR-001 评审通过后生效。

**成功 201：`Paper`**（字段见 contract 2.3）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 试卷唯一标识 |
| `title` | string | 试卷名称 |
| `items` | `PaperItem[]` | `{ questionId, order, score }`，`order` 从 1 开始，`score` 等于题目 `totalScore` |
| `totalScore` | int | 等于各题 `Question.totalScore` 之和 |
| `status` | enum | 固定 `DRAFT` |
| `startAt` / `endAt` / `publishedAt` | datetime | `DRAFT` 状态下为空 |
| `createdBy` | string | 取自 JWT `subject` |

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | `title` 为空；`questionIds` 为空数组；`questionIds` 中存在重复题目 | 原表 400 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师 | contract 第 5 节 |
| 404 | `QUESTION_NOT_FOUND` | `questionIds` 中任一题目不存在 | contract 第 5 节 |
| 409 | `PAPER_SCORE_MISMATCH` | 系统汇总的总分与各题分值之和不一致（防御性校验，正常路径不应触发） | contract 第 5 节（该码产生模块标注为 exam） |
| 409 | `QUESTION_NOT_ACTIVE`（待登记） | `questionIds` 中任一题目状态 ≠ `ACTIVE` | FR-4；module-01 §6 |

**权限**：仅教师；组卷后试卷归属该教师（`createdBy`）。

**对应 AC**：`module-01-qbank.md` AC-4

---

#### 6.2.5 GET /api/v1/papers/{id} — 试卷详情

**请求**

- 路径参数：`id` = `Paper.id`
- 身份来源：JWT

**成功 200：`Paper`**（字段见 contract 2.3）

- `DRAFT` 试卷：返回 contract 2.3 全部字段，另含各题基线快照的 `stem`、`referenceAnswer`、`rubric`，供教师核对后交 `exam` 发布；
- `PUBLISHED` / `CLOSED` 试卷：只返回冻结的正式快照，不回源读取最新题目；
- 草稿阶段若要查看“组卷时的题目 vs 当前题目”，使用 6.2.7 的 diff 接口。
- 快照行为待 ADR-001 评审通过后生效；通过前按现行动态引用实现不得合并。

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师；或试卷 `createdBy` ≠ 当前 JWT `subject` | contract 第 5、6 节 |
| 404 | `PAPER_NOT_FOUND`（待登记） | 试卷不存在 | 原表 404；契约 v0.2 登记 |

**权限**：仅教师；仅本人创建的试卷。已发布试卷面向学生的可见性由 `exam` 控制，qbank 不实现该逻辑。

**对应 AC**：`module-01-qbank.md` AC-4（交接前核对）、FR-5

---

#### 6.2.6 GET /api/v1/papers — 试卷列表（待发布）

**请求**

| 参数 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `status` | query | enum | 否 | 默认 `DRAFT`；可选 `PUBLISHED` / `CLOSED` / `ALL` |

身份来源：JWT；仅返回 `createdBy` = 当前 `subject` 的试卷。

**成功 200：`Paper[]`**（字段见 contract 2.3）

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | `status` 取值不在允许范围 | 原表未列，参数校验归 API 层 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师 | contract 第 5 节 |

**权限**：仅教师；仅本人创建的试卷。

**对应 AC**：`module-01-qbank.md` AC-4、FR-5（仅 `DRAFT` 试卷可交接给 `exam`）

---

#### 6.2.7 GET /api/v1/papers/{id}/snapshot-diff — 草稿快照对比（契约预留，UI 后置）

**用途**：教师查看组卷时的基线快照与当前题目内容的差异。只读，不修改任何数据；前端对比页第 10 周实现。

**请求**

- 路径参数：`id` = `Paper.id`
- 身份来源：JWT；仅教师本人试卷

**成功 200：`SnapshotDiff[]`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `questionId` | string | 题目 ID |
| `changed` | boolean | 基线快照与当前题目是否不同 |
| `currentStatus` | enum | `ACTIVE` / `ARCHIVED` / `MISSING` |
| `baseline` | object | 基线快照：`type`、`stem`、`referenceAnswer`、`totalScore`、`rubric[]` |
| `current` | object / null | 当前题目内容；`MISSING` 时为 `null` |

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师；或试卷 `createdBy` ≠ 当前 JWT `subject` | contract 第 5、6 节 |
| 404 | `PAPER_NOT_FOUND`（待登记） | 试卷不存在 | 5.1 表；契约 v0.2 登记 |

**权限**：仅教师本人试卷；不返回他人试卷内容。

**对应 AC**：`module-01-qbank.md` AC-4（交接前核对）；ADR-001 草稿对比能力。

> MVP1 只预留契约与数据结构，不做前端页面；不提供“刷新快照”写接口。教师确认要更新快照时，重新组卷。

---

#### 6.2.8 数据流与风险

**成功路径**

```
教师登录（integration，JWT role=TEACHER）
  → POST /questions：参数校验 → 禁用词检查 → 评分点分值之和 = totalScore
      → 同一事务写入题目与评分点（referenceAnswer 必填；rubric 至少 1 项；status 默认 DRAFT）
  → 题目流转为 ACTIVE
  → GET /questions?status=ACTIVE：按 JWT subject 过滤，返回本人 ACTIVE 题
  → POST /papers：存在性 + ACTIVE + 去重校验 → 系统汇总 totalScore
      → 按 ADR-001 在同一事务内写入基线快照 → 提交
  → 返回 201 Paper（status=DRAFT，startAt/endAt/publishedAt 为空）
  → 草稿阶段：GET /papers/{id}/snapshot-diff 对比基线快照与当前题目（只读，UI 后置）
  → 交接：exam 发布时只把 Paper 改为 PUBLISHED，基线快照随状态成为正式快照；
    exam 按本文件 6.5 节 `PaperForExam` 读取，grading 按 `QuestionForGrading` 读取。
    qbank 不实现发布、计时、作答与阅卷。
```

**失败路径**（均不产生副作用：不新增记录、不改状态）

| 失败场景 | 返回 | 保证不变 |
| --- | --- | --- |
| 评分点描述含「以及 / 等等 / 酌情 / 其他合理」 | 409 `RUBRIC_DESCRIPTION_VAGUE` | 不写题目与评分点 |
| 评分点分值之和 ≠ 题目总分 | 409 `RUBRIC_SCORE_MISMATCH` | 不写题目与评分点 |
| 组卷引用非 `ACTIVE` 题目 | 409 `QUESTION_NOT_ACTIVE`（待登记） | 不写试卷与试卷题目 |
| 组卷 `questionIds` 重复 | 400 `VALIDATION_ERROR`（待登记） | 不写试卷与试卷题目 |
| 修改已被 `PUBLISHED` 试卷引用的题目 | 409 `QUESTION_ALREADY_USED`（待登记） | 原题目与历史快照均不变 |
| 组卷事务中途异常 | 事务回滚 | 试卷与试卷题目均无残留 |

**风险 R-01：组卷快照写入的事务原子性**

| 项 | 内容 |
| --- | --- |
| 风险 | 组卷事务在写入 N 道题快照的过程中异常退出，可能遗留不完整的试卷题目记录，导致 `exam` 拿到缺题试卷 |
| 影响 | `exam` 发布时会命中 `EMPTY_PAPER` 或 `PAPER_SCORE_MISMATCH`，错误信息对教师不直观，脏数据难以排查 |
| 应对 | ① 试卷与试卷题目写入置于同一事务；② 试卷题目按 `(paperId, questionId)` 唯一，防重复；③ 提交前校验试卷题目行数 == `questionIds` 长度，不等则主动抛异常回滚 |
| 验证 | 仍并入 SP-04，但 SP-04 当前只完成存储验证，**事务回滚尚未测试**；需在 MySQL 8 重跑时补测试，或第 9 周集成测试补。未补前 R-01 标“待验证”，不得算已关闭。 |

---

> **待契约 v0.2 登记的错误码（4 个）**：`VALIDATION_ERROR`（400）、`PAPER_NOT_FOUND`（404）、`QUESTION_NOT_ACTIVE`（409）、`QUESTION_ALREADY_USED`（409）。
> 登记前这些码只在本文作为提案，不得在代码中先使用；接口按对应 HTTP 状态返回，`code` 字段暂用提案名并在 PR 中注明。

### 6.3 在线考试与答卷（exam）

| 方法 | 路径 | 说明 | 成功 | 主要失败 |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/papers/{id}/publish` | 发布考试，设置时间窗口 | 200 `Paper` | 400 `VALIDATION_ERROR`、403 `FORBIDDEN`、404 `PAPER_NOT_FOUND`、409 `EMPTY_PAPER` / `PAPER_SCORE_MISMATCH` / `INVALID_EXAM_WINDOW` / `PAPER_NOT_DRAFT` |
| GET | `/api/v1/exams?status=AVAILABLE` | 学生可见考试列表 | 200 `ExamSummary[]` | 400 `VALIDATION_ERROR`、401、403 |
| GET | `/api/v1/exams/{paperId}` | 学生进入考试页（不含评分点与参考答案） | 200 `ExamDetail` | 401、403 `FORBIDDEN` / `EXAM_NOT_STARTED` / `EXAM_CLOSED`、404 `PAPER_NOT_FOUND` |
| POST | `/api/v1/exams/{paperId}/answer-sheet` | 进入考试，创建或返回本人 `DRAFT` 答卷 | 200/201 `AnswerSheet` | 401、403 `FORBIDDEN` / `EXAM_NOT_STARTED` / `EXAM_CLOSED`、404 `PAPER_NOT_FOUND` |
| PUT | `/api/v1/answer-sheets/{id}/answers` | 保存草稿（按题批量覆盖） | 200 `{ savedAt }` | 400 `VALIDATION_ERROR`、401、403 `FORBIDDEN` / `EXAM_NOT_STARTED` / `EXAM_CLOSED`、404 `ANSWER_SHEET_NOT_FOUND`、409 `EXAM_ALREADY_SUBMITTED` |
| POST | `/api/v1/answer-sheets/{id}/submit` | 手动交卷，携带全部答案 | 200 `AnswerSheet` | 400 `VALIDATION_ERROR`、401、403 `FORBIDDEN` / `EXAM_NOT_STARTED` / `EXAM_CLOSED`、404 `ANSWER_SHEET_NOT_FOUND`、409 `EXAM_ALREADY_SUBMITTED` |
| GET | `/api/v1/papers/{id}/answer-sheets` | 教师查看本人试卷的答卷 | 200 `AnswerSheetSummary[]` | 400 `VALIDATION_ERROR`、401、403 `FORBIDDEN`、404 `PAPER_NOT_FOUND` |

> 本节字段由 exam 组确认；成功/失败分支、权限与 AC 映射按 6.3.1～6.3.7 逐接口写清。自动交卷触发方式见 6.3.8 与 ADR-002。
> 身份字段（`studentId`、`createdBy`）一律取自 JWT `subject`，**不接受请求体传入**；跨模块 DTO 见 6.5 节。
> 触发粒度（逐题 vs 整卷）待 G-08 决议；本表按单题幂等键设计，整卷批量不引入新的幂等语义。

#### 6.3.1 POST /api/v1/papers/{id}/publish — 发布考试

> **实现状态：ADR-004 已接受（2026-11-23）**——发布通过 qbank `PaperLifecyclePort.markPublished` 受控命令完成，exam 不直接写 `Paper` 表。

**请求**

- 路径参数：`id` = `Paper.id`
- 请求体：

| 字段 | 类型 | 必填 | 约束与依据 |
| --- | --- | --- | --- |
| `startAt` | datetime | 是 | ISO-8601 带时区；必须早于 `endAt`；允许早于当前时间（立即开始/已开始），只要 `endAt` 未过期（FR-1 / R3） |
| `endAt` | datetime | 是 | ISO-8601 带时区；必须晚于 `startAt`，且发布时未过期（FR-1 / R3） |

身份来源：JWT `role=TEACHER`，`teacherId` 取自 JWT `subject`；exam 调用 qbank `PaperLifecyclePort.markPublished(paperId, teacherId, startAt, endAt, publishedAt)`，由 qbank 校验归属并写 `Paper`；不接受请求体传入教师 ID。

**成功 200：`Paper`**（字段见 contract 2.3）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 试卷 / 考试 ID |
| `title` | string | 试卷名称 |
| `items` | `PaperItem[]` | `{ questionId, order, score }`，`order` 从 1 开始 |
| `totalScore` | int | 各题分值之和 |
| `status` | enum | `PUBLISHED` |
| `startAt` / `endAt` | datetime | 本次发布设置的服务端时间 |
| `publishedAt` | datetime | 服务端发布时刻，不由请求传入 |
| `createdBy` | string | 试卷创建教师，取自 JWT |

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | 缺少 `startAt` / `endAt`；时间格式非法或无法解析 | 通用参数校验 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师；或试卷 `createdBy` ≠ JWT `subject` | contract 第 5、6 节 |
| 404 | `PAPER_NOT_FOUND`（待登记） | `id` 不存在 | 5.1 表 |
| 409 | `PAPER_NOT_DRAFT` | 试卷当前状态不是 `DRAFT`（重复发布或已关闭） | 5.1（已登记，待契约 v0.2）/ ADR-004 |
| 409 | `EMPTY_PAPER` | 试卷 `items` 为空 | contract 第 5 节 / AC-8 |
| 409 | `PAPER_SCORE_MISMATCH` | `totalScore` ≠ 各 `items[].score` 之和 | contract 第 5 节 / AC-8 |
| 409 | `INVALID_EXAM_WINDOW` | `startAt ≥ endAt`，或 `endAt` 不晚于当前服务端时间 | contract 第 5 节 / AC-8 / FR-1 |

**权限**：仅教师，且仅本人创建的试卷；发布后试卷结构、分值与时间窗口不可修改（FR-1）。

**对应 AC**：`module-02-exam.md` AC-1 / AC-8；FR-1、FR-2。

> **Q-1 已由 ADR-004 裁决（已接受，2026-11-23）**：qbank 提供 `PaperLifecyclePort.markPublished(paperId, teacherId, startAt, endAt, publishedAt)` / `markClosed(paperId)` 受控命令；exam 只调用命令，不直接写 `Paper` 表。6.3.1 / 6.3.8 按该命令描述。

#### 6.3.2 GET /api/v1/exams?status=AVAILABLE — 学生可见考试列表

**请求**

| 参数 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `status` | query | enum | 否 | 默认 `AVAILABLE`；MVP1 仅允许 `AVAILABLE`（已发布且当前在 `[startAt, endAt)` 内） |

身份来源：JWT `role=STUDENT`；返回所有 `PUBLISHED` 且当前在 `[startAt, endAt)` 内的考试。MVP1 无参与名单，不按学生过滤，也不接受 `studentId` 查询参数；`answerSheetStatus` 只取当前学生本人的答卷状态。

**成功 200：`ExamSummary[]`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `paperId` | string | 考试 / 试卷 ID |
| `title` | string | 试卷名称 |
| `totalScore` | int | 试卷总分 |
| `startAt` / `endAt` | datetime | 服务端时间窗口 |
| `status` | enum | `PUBLISHED` |
| `answerSheetStatus` | enum | `NOT_STARTED` / `DRAFT` / `SUBMITTED`，按当前学生答卷派生（视图字段，不新增实体）；用于前端展示“未开始 / 作答中 / 已交卷” |

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | `status` 取值不是 `AVAILABLE` | 参数校验 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是学生 | contract 第 6 节 |

**权限**：仅学生；MVP1 不做参与名单，已发布且在窗口内的考试对全体学生可见（module-02 §8.4）。

**对应 AC**：AC-2（进入前的可见性）、AC-7（窗口外不出现）；FR-2、FR-7。

#### 6.3.3 GET /api/v1/exams/{paperId} — 学生进入考试页

**请求**

- 路径参数：`paperId` = `Paper.id`
- 身份来源：JWT `role=STUDENT`

**成功 200：`ExamDetail`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `paperId` | string | 试卷 ID |
| `title` | string | 试卷名称 |
| `totalScore` | int | 试卷总分 |
| `startAt` / `endAt` | datetime | 服务端时间窗口 |
| `serverTime` | datetime | 服务端当前时间，供前端校准倒计时；**是否截止以服务端为准** |
| `status` | enum | `PUBLISHED` |
| `items` | `ExamItem[]` | `{ questionId, order, score, type, stem }`；**不含 `referenceAnswer` 与 `rubric`** |
| `answerSheetId` | string / null | 当前学生已有答卷 ID；未进入过为 `null` |
| `answerSheetStatus` | enum / null | `DRAFT` / `SUBMITTED`；无答卷为 `null` |

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是学生 | contract 第 6 节 |
| 403 | `EXAM_NOT_STARTED` | 当前服务端时间早于 `startAt` | contract 第 5 节 / AC-7 |
| 403 | `EXAM_CLOSED` | 当前服务端时间到达或超过 `endAt` | contract 第 5 节 / AC-7 |
| 404 | `PAPER_NOT_FOUND`（待登记） | `paperId` 不存在，或试卷不是 `PUBLISHED`（不泄露 `DRAFT` 试卷是否存在） | 5.1 表 / contract 第 6 节 |

**权限**：仅学生；只返回 `PUBLISHED` 试卷；评分点与参考答案永不下发（contract 第 6 节）。

**对应 AC**：AC-2（进入）、AC-7（窗口）；FR-2、FR-7；contract 第 6 节。

#### 6.3.4 POST /api/v1/exams/{paperId}/answer-sheet — 创建或返回本人答卷

**请求**

- 路径参数：`paperId` = `Paper.id`
- 请求体：无（空对象 `{}` 可接受）；**不接受 `studentId`**
- 身份来源：JWT `role=STUDENT`，`studentId` = JWT `subject`

**成功**

- **201 Created**：首次进入，创建 `DRAFT` 答卷，返回 `AnswerSheet`
- **200 OK**：已有答卷（`DRAFT` 或 `SUBMITTED`），返回同一份，不新建

`AnswerSheet` 字段（contract 2.4）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 答卷 ID |
| `paperId` | string | 所属试卷 |
| `studentId` | string | 取自 JWT，不接受请求体 |
| `answers` | `Answer[]` | `{ questionId, content, savedAt }`；新建时为空数组 |
| `status` | enum | `DRAFT` / `SUBMITTED` |
| `startedAt` | datetime | 首次创建时间（服务端） |
| `submittedAt` | datetime / null | 交卷后为服务端时间；`DRAFT` 为 `null` |
| `submitType` | enum / null | `MANUAL` / `AUTO`；`DRAFT` 为 `null` |

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是学生 | contract 第 6 节 |
| 403 | `EXAM_NOT_STARTED` | 当前服务端时间早于 `startAt` | contract 第 5 节 / AC-7 |
| 403 | `EXAM_CLOSED` | 当前服务端时间到达或超过 `endAt`；即使兜底已把答卷置为 `SUBMITTED`，进入接口仍返回 403，状态由 6.3.2 的 `answerSheetStatus` 展示 | contract 第 5 节 / AC-7 |
| 404 | `PAPER_NOT_FOUND`（待登记） | 试卷不存在或不是 `PUBLISHED` | 5.1 表 |

**权限**：仅学生本人；`(paperId, studentId)` 由数据库唯一约束保证最多一份答卷（R4）。并发首次进入时，唯一约束冲突的一方重新读取并返回已有答卷，不产生第二份。已交卷学生在窗口内重复进入返回 200；窗口外不再通过本接口进入，状态由 6.3.2 的 `answerSheetStatus` 展示。

**对应 AC**：AC-2（首次/重复进入）、AC-7；FR-3、FR-8；R4。

#### 6.3.5 PUT /api/v1/answer-sheets/{id}/answers — 保存草稿

**请求**

- 路径参数：`id` = `AnswerSheet.id`
- 请求体：

| 字段 | 类型 | 必填 | 约束与依据 |
| --- | --- | --- | --- |
| `answers` | `AnswerInput[]` | 是 | 至少 1 项；按 `questionId` 覆盖对应题，未出现的题保持不变 |
| `answers[].questionId` | string | 是 | 必须属于本试卷；同一请求内不得重复 |
| `answers[].content` | string | 是 | 允许空字符串（清空该题）；长度上限暂定 20,000 字符，待 SP-04 结论复核 |

身份来源：JWT `role=STUDENT`；`sheet.studentId` 必须等于 JWT `subject`，不接受请求体传入。

**成功 200**

```json
{ "savedAt": "2026-11-18T10:15:30+08:00" }
```

`savedAt` 为本次保存的服务端时间；同一请求内所有题共用该时间。

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | `answers` 缺失/为空/非数组；`content` 非字符串或超长；`questionId` 不属于本试卷；同一请求 `questionId` 重复 | 参数校验 / FR-4 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是学生；或答卷 `studentId` ≠ JWT `subject` | contract 第 5、6 节 |
| 403 | `EXAM_NOT_STARTED` | 当前服务端时间早于 `startAt` | contract 第 5 节 / AC-7 |
| 403 | `EXAM_CLOSED` | 当前服务端时间到达或超过 `endAt`，兜底自动交卷未成功、答卷仍为 `DRAFT` | contract 第 5 节 / AC-7 |
| 404 | `ANSWER_SHEET_NOT_FOUND` | `id` 不存在 | contract 第 5 节 |
| 409 | `EXAM_ALREADY_SUBMITTED` | 答卷已为 `SUBMITTED`（只读），包括请求兜底刚刚完成 | contract 第 5 节 / AC-6 |

**检查顺序**：鉴权 → 答卷存在 → 归属 → 若已到 `endAt` 先执行兜底自动交卷 → 重新读取状态 → 已交卷（409）→ 未交卷且已过窗口（403）→ 请求体校验 → 按题覆盖。兜底成功后返回 409 `EXAM_ALREADY_SUBMITTED`；兜底未成功（仍为 `DRAFT`）才返回 403 `EXAM_CLOSED`。

**权限**：仅学生本人；教师不可写学生答卷。

**对应 AC**：AC-3（保存与续答）、AC-6（交卷后拒绝保存）、AC-7（窗口）、AC-10（前端重试，服务端按最后一次覆盖）；FR-4、FR-7、FR-8。

#### 6.3.6 POST /api/v1/answer-sheets/{id}/submit — 手动交卷

**请求**

- 路径参数：`id` = `AnswerSheet.id`
- 请求体：

| 字段 | 类型 | 必填 | 约束与依据 |
| --- | --- | --- | --- |
| `answers` | `AnswerInput[]` | 是 | **必须覆盖本试卷全部题目**；未作答的题传 `content: ""`；不得缺题、多题或重复 |
| `answers[].questionId` | string | 是 | 必须属于本试卷 |
| `answers[].content` | string | 是 | 允许空字符串；长度上限同 6.3.5 |

身份来源：JWT `role=STUDENT`；`sheet.studentId` 必须等于 JWT `subject`。

**成功 200：`AnswerSheet`**

- `status` = `SUBMITTED`
- `submitType` = `MANUAL`
- `submittedAt` = 本次事务的服务端时间
- `answers[]` 为本次提交的全量答案，`savedAt` = `submittedAt`
- 其余字段同 6.3.4

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | `answers` 未覆盖全部题目 / 含多余题目 / 重复；`content` 非法或超长 | 参数校验 / AC-11 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是学生；或答卷 `studentId` ≠ JWT `subject` | contract 第 5、6 节 |
| 403 | `EXAM_NOT_STARTED` | 当前服务端时间早于 `startAt` | contract 第 5 节 / AC-7 |
| 403 | `EXAM_CLOSED` | 当前服务端时间到达或超过 `endAt`，兜底自动交卷未成功、答卷仍为 `DRAFT`（由定时扫描继续接管） | contract 第 5 节 / AC-7 |
| 404 | `ANSWER_SHEET_NOT_FOUND` | `id` 不存在 | contract 第 5 节 |
| 409 | `EXAM_ALREADY_SUBMITTED` | 答卷已为 `SUBMITTED`（重复点击、网络重试、自动交卷已先完成，或请求兜底刚刚完成） | contract 第 5 节 / AC-6 |

**检查顺序**：鉴权 → 答卷存在 → 归属 → 若已到 `endAt` 先执行兜底自动交卷 → 重新读取状态 → 已交卷（409）→ 未交卷且已过窗口（403）→ 请求体校验 → 事务。

**事务与幂等**（详见 ADR-002）：

1. 校验归属、窗口与请求体；
2. 同一事务内按题 upsert 全量答案；
3. 执行条件更新 `UPDATE ... SET status='SUBMITTED', submitted_at=?, submit_type='MANUAL' WHERE id=? AND status='DRAFT'`；
4. 影响行数为 0 时**回滚答案写入**并返回 409；为 1 时提交。

**窗口判定时点**：在请求处理开始时用服务端时间判定；若事务提交跨越 `endAt`，仍视为窗口内手动交卷，`submittedAt` 取提交时的服务端时间。

**权限**：仅学生本人；交卷后答卷只读，不发生第二次状态迁移。

**对应 AC**：AC-4（手动交卷）、AC-6（重复交卷）、AC-7（窗口）、AC-11（交卷不丢答案）；FR-5、FR-9；R5。

#### 6.3.7 GET /api/v1/papers/{id}/answer-sheets — 教师查看本人试卷的答卷

**请求**

| 参数 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | string | 是 | `Paper.id` |
| `status` | query | enum | 否 | `DRAFT` / `SUBMITTED` / `ALL`，默认 `ALL` |

身份来源：JWT `role=TEACHER`；`paper.createdBy` 必须等于 JWT `subject`。

**成功 200：`AnswerSheetSummary[]`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `answerSheetId` | string | 答卷 ID |
| `studentId` | string | 作答学生 ID |
| `status` | enum | `DRAFT` / `SUBMITTED` |
| `startedAt` | datetime | 开始作答时间 |
| `submittedAt` | datetime / null | 交卷时间 |
| `submitType` | enum / null | `MANUAL` / `AUTO` |
| `answeredCount` | int | `content` 非空的已保存题目数 |
| `questionCount` | int | 试卷题目总数 |

> 本接口只给 exam 侧摘要；AI 建议分、评分点命中与复核字段属于 grading，见 6.4 的 `GradingSheetView`，不在本响应中重复。

**失败响应**

| HTTP | 错误码 | 触发条件 | 依据 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR`（待登记） | `status` 不在允许范围 | 参数校验 |
| 401 | `UNAUTHORIZED` | 未携带 JWT 或 JWT 失效 | contract 第 5 节 |
| 403 | `FORBIDDEN` | 角色不是教师；或试卷 `createdBy` ≠ JWT `subject`；学生访问 | contract 第 5、6 节 |
| 404 | `PAPER_NOT_FOUND`（待登记） | 试卷不存在 | 5.1 表 |

**权限**：仅试卷创建教师；学生不可访问。

**对应 AC**：AC-9（越权与不存在）；contract 第 6 节。module-02 无独立 AC，本接口作为教师复核入口的前置能力，跨模块消费见 6.5 `SubmittedSheetForGrading`。

#### 6.3.8 自动交卷触发方式（ADR-002 决策摘要）

> **实现状态：ADR-004 已接受（2026-11-23）**——`findDuePapers` / `markClosed` 与 `PaperForExam` 字段已由集成分支补齐。

> 完整取舍、并发 SQL 与失败语义见 `adr/ADR-002-exam-submit-idempotency.md`；本节只写 exam 接口可见的行为。

| 项 | 确认结果 |
| --- | --- |
| 主触发 | 单实例 `@Scheduled(fixedDelay = 30s)` 调用 qbank 只读接口 `findDuePapers(now)` 枚举到期 `PUBLISHED` 试卷（**含零答卷试卷**）；对每张试卷下的 `DRAFT` 答卷执行条件更新，再调用 qbank `markClosed(paperId)`。不直接 JOIN qbank 表，也不只从 `answer_sheets` 出发 |
| 兜底触发 | 学生在 `endAt` 后调用保存/交卷时，先对本人 `DRAFT` 答卷执行同一条件更新：兜底成功返回 **409 `EXAM_ALREADY_SUBMITTED`**，兜底未成功才返回 **403 `EXAM_CLOSED`**。进入接口仍返回 403，状态由 6.3.2 展示。不单独依赖惰性触发（无人访问会漏交） |
| 状态迁移 | 条件更新 `WHERE status='DRAFT'`；每份答卷最多一次 `DRAFT → SUBMITTED` |
| 时间字段 | `submitType='AUTO'`；`submittedAt = papers.endAt`（不是扫描时刻，符合 AC-5 / contract 2.4） |
| 答案来源 | 以最后一次成功保存的答案为准；未保存内容不阻塞交卷（FR-6） |
| 重启补偿 | 进程重启后首轮扫描自动补齐；无需补偿表 |
| 试卷关闭 | 到达 `endAt` 后，先完成该试卷所有 `DRAFT` 答卷的自动交卷，再调用 qbank `markClosed(paperId)`（受控命令，ADR-004）；零答卷试卷也会被 `findDuePapers` 枚举并关闭；仍有失败则本轮不关闭，下一轮重试 |
| 失败处理 | 单份失败记录日志并在下一轮重试；不因一份失败阻塞其他答卷；连续失败升级人工 |
| 参数（已回填） | 扫描间隔 30s、单批上限 200 份；SP-03 实测 10/10 在 10.1s 内完成、0 重复；零答卷关闭已用最小表验证，第 10 周在正式表复跑 |

> 扫描入口改为 qbank `findDuePapers(now)`，不再只从 `answer_sheets` 出发；这样零答卷试卷也会被关闭。跨模块不直接读 `papers` 表（ADR-004）。
> 6.5 已补 `PaperForExam` 的 `startAt` / `endAt` / `publishedAt` / `createdBy`；`findDuePapers` / `markClosed` 由 ADR-004 提供（已接受）。
> **SP-02/SP-03 实测（2026-11-18）**：50 并发 × 10 轮每轮 1 次迁移；30s 扫描 + 惰性兜底 10/10，最大触发延迟 10.1s，0 重复；仅惰性 5/10 漏交。

#### 6.3.9 数据流与风险

**成功路径**

```text
教师登录（integration，JWT role=TEACHER）
  → POST /papers/{id}/publish：归属 → 状态 DRAFT → 非空 → 总分一致 → startAt < endAt 且 endAt 未过期
      → 调用 qbank markPublished(...) → Paper: DRAFT → PUBLISHED，publishedAt 为服务端时间
学生登录（JWT role=STUDENT）
  → GET /exams?status=AVAILABLE：只返回 PUBLISHED 且当前在窗口内的考试
  → GET /exams/{paperId}：返回题干与 serverTime，不下发评分点/参考答案
  → POST /exams/{paperId}/answer-sheet：唯一约束创建或返回本人 DRAFT 答卷
  → PUT /answer-sheets/{id}/answers：按题覆盖，savedAt 为服务端时间
  → POST /answer-sheets/{id}/submit：全量答案 + 条件更新 DRAFT → SUBMITTED（MANUAL）
  → grading 通过 SubmittedSheetForGrading 只读消费（仅 SUBMITTED）
到 endAt：
  → findDuePapers(now) 枚举到期 PUBLISHED 试卷（含零答卷）
  → 定时扫描（或学生请求兜底）条件更新 DRAFT → SUBMITTED（AUTO，submittedAt=endAt）
  → 全部成功（或零答卷）后调用 qbank markClosed(paperId)：PUBLISHED → CLOSED
```

**失败路径与不变式**

| 失败场景 | 返回 | 必须保持不变 |
| --- | --- | --- |
| 发布时非 `DRAFT` | 409 `PAPER_NOT_DRAFT` | 原状态、`publishedAt`、窗口均不变 |
| 发布时为空 / 总分不一致 / 窗口非法 | 409 对应错误码 | 试卷仍为 `DRAFT`，不写 `publishedAt` |
| 窗口外进入 / 保存 / 交卷 | 403 `EXAM_NOT_STARTED` / `EXAM_CLOSED` | 不创建、不修改答卷 |
| 重复交卷（含网络重试） | 409 `EXAM_ALREADY_SUBMITTED` | 答案、`submittedAt`、`submitType` 均不变 |
| 手动交卷与自动交卷并发 | 一方成功，另一方 409 或静默跳过 | 只有一次 `DRAFT → SUBMITTED`，`submittedAt` 不被覆盖 |
| 交卷请求体缺题 / 多题 / 重复 | 400 `VALIDATION_ERROR` | 事务回滚，答卷保持 `DRAFT`，答案不变 |
| 越权访问他人答卷 | 403 `FORBIDDEN` | 不泄露资源是否存在与内容 |
| 自动交卷单份失败 | 记录日志，下一轮重试 | 该答卷保持 `DRAFT`，不写入半份答案 |

**风险 R-01 / R-08：交卷并发与自动交卷触发**

| 项 | 内容 |
| --- | --- |
| 风险 | 手动交卷、网络重试、到点自动交卷与定时扫描可能同时到达；若没有单一条件更新，会重复迁移、覆盖 `submittedAt` 或产生第二份答卷；若调度漏扫，`DRAFT` 答卷会阻塞 grading |
| 影响 | grading 无法开始或读到不一致数据；学生看到错误状态；成绩发布被阻塞 |
| 应对 | ① `(paper_id, student_id)` 唯一约束；② `UPDATE ... WHERE status='DRAFT'` 条件更新；③ 手动交卷在同一事务内写答案并迁移；④ 定时扫描 + 请求兜底；⑤ `submittedAt` 手动取服务端时间、自动取 `endAt` |
| 验证 | SP-02（50 并发 × 10 轮，仅 1 次成功）；SP-03（10 份答卷，`endAt + 60s` 内 10/10，0 次重复）；AC-5 / AC-6 / FR-9 |
| 负责人 | 钱斓轩（主）、李昕彤（复核） |

#### 6.3.10 与 grading 的契约对齐

| 对齐点 | exam 侧保证 | grading 侧约束 |
| --- | --- | --- |
| 可评分对象 | 只有 `SUBMITTED` 答卷进入 `SubmittedSheetForGrading`；`DRAFT` 不暴露 | 不读取、不评分 `DRAFT` 答卷 |
| 交卷方式 | `submitType` 区分 `MANUAL` / `AUTO`；`AUTO` 的 `submittedAt=endAt` | 评分逻辑不依赖 `submitType`，两者同等可评 |
| 答案冻结 | 交卷后答案只读；重复交卷/保存不改变内容 | 只读消费，不回写答案 |
| 时间权威 | `startedAt`、`savedAt`、`submittedAt` 全部为服务端时间 | 以 `submittedAt` 作为评分与审计时间 |
| 试卷关闭 | `endAt` 后 `PUBLISHED → CLOSED`（qbank `markClosed`，ADR-004） | 若 G-01 要求关闭后才能发布成绩，需 exam 提供只读进度；当前 6.5 未定义，待 G-01 决议后补 DTO |
| 教师视图 | `GET /papers/{id}/answer-sheets` 只给答卷摘要 | `GET /papers/{id}/grading-sheets` 给 AI/复核字段，二者不重复 |

**跨模块决策与待确认项**

| 编号 | 问题 | 影响 | 建议 |
| --- | --- | --- | --- |
| Q-1 | `Paper` 发布/关闭写路径 | 已由 ADR-004 裁决（已接受，2026-11-23）：qbank `markPublished` / `markClosed`，exam 调用 | 已接受 |
| Q-2 | G-01 是否要求试卷 `CLOSED` 后才能发布成绩？ | 决定是否需要 `ExamProgressForGrading` DTO | 李昕彤 + 左恩东在接口冻结前定 |
| Q-3 | `PAPER_NOT_DRAFT` 错误码 | 5.1 已登记，待契约 v0.2 | 契约升版时转正式 |
| Q-4 | 答案 `content` 长度上限 | 保存/交卷校验与 DB 字段 | SP-04 结论回填；暂定 20,000 字符 |
| Q-5 | 自动交卷扫描间隔与漂移 | `endAt + 60s` 完成率 | 已由 SP-03 回填：30s / 单批 200，10/10 在 10.1s 内 |
| Q-6 | 自动交卷扫描读取 `papers` 的路径 | 已由 ADR-004 改为 `findDuePapers(now)` | 不得同库 JOIN |
| Q-7 | 6.5 的 `PaperForExam` 字段 | 已在 `docs/32-exam-integration` 补齐 `startAt` / `endAt` / `publishedAt` / `createdBy` | qbank 确认；待评审 |
| Q-8 | qbank `findDuePapers(now)` 只读枚举 | 已由 ADR-004 提供；零答卷试卷可关闭 | 已用最小表验证；第 10 周在正式表复跑 |

### 6.4 AI 阅卷与复核（grading）

| 方法 | 路径 | 说明 | 成功 | 主要失败 |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/papers/{id}/grading-sheets` | 教师查看逐题评分状态 | 200 `GradingSheetView[]` | 403（非本人试卷）、404 |
| POST | `/api/v1/answer-sheets/{id}/questions/{questionId}/ai-grade` | 触发单题初评（整卷批量=循环调用） | 200 `GradeResult` | 409 `ANSWER_NOT_SUBMITTED` / `AI_GRADING_IN_PROGRESS`、502 `AI_SERVICE_TIMEOUT` / `AI_OUTPUT_INVALID` / `AI_SCORE_OUT_OF_RANGE` |
| PUT | `/api/v1/answer-sheets/{id}/questions/{questionId}/review` | 教师复核并写确认分 | 200 `GradeResult` | 400 `INVALID_REVIEWED_SCORE`、403、404 |
| POST | `/api/v1/papers/{id}/grades/publish` | 整场发布成绩 | 200 `{ publishedAt }` | 409 `GRADE_NOT_FULLY_REVIEWED`、403 |
| GET | `/api/v1/my/grades/{paperId}` | 学生查本人成绩 | 200 `PublishedGrade` | 403 `SCORE_NOT_PUBLISHED`、404 |

> 触发粒度（逐题 vs 整卷）待 G-08 决议；本表按单题幂等键设计，整卷批量不引入新的幂等语义。

#### 6.4.1 通用请求与响应约定

- 路径 ID 均为非空字符串。以下接口无查询参数，除复核外无请求体。身份和角色只取自 JWT，不接受客户端传入 studentId、createdBy 或 reviewedBy。
- 所有接口：JWT 缺失、无效或过期返回 401 UNAUTHORIZED；角色不符或资源不归属本人返回 403 FORBIDDEN；路径参数或请求体格式非法返回 400 VALIDATION_ERROR。错误体至少包含 { code: string, message: string }，并可包含统一响应约定中的 requestId。
- 以下是第 9 周拆任务用的接口草案，新增错误码和审计字段见 [契约 v0.2 草案](https://github.com/AI-exam-team/ai-exam-system/blob/docs/issue-33-grading-contract/spec/contract-v0.2.md)。待契约评审及标注的未决行为确认后冻结。时间字段为带偏移量的 ISO 8601 字符串；以下 nullable 字段未产生时返回 null，空集合返回 []。

| 类型 | 字段及类型 |
| --- | --- |
| RubricHit | rubricItemId: string, hit: boolean, score: integer, reason: string |
| GradingItem | questionId: string, aiStatus: NOT_STARTED / PENDING / SUCCEEDED / FAILED, rubricHits: RubricHit[]（未成功为 []）, aiScore: integer nullable, aiReason: string nullable, reviewedScore: integer nullable, reviewComment: string nullable, reviewedAt: datetime nullable |
| GradeResult | GradingItem 全部字段，加 id: string, answerSheetId: string, reviewedBy: string nullable |
| GradingSheetView | answerSheetId: string, items: GradingItem[] |
| PublishedGrade | paperId: string, totalScore: integer（教师确认分之和）, items: { questionId: string, reviewedScore: integer, reviewComment: string nullable }[] |

#### 6.4.2 GET /api/v1/papers/{id}/grading-sheets

- 请求：id 为试卷 ID。
- 成功 200：GradingSheetView[]，每份 SUBMITTED 答卷一项，每道试卷题目一条，无评分记录显示 NOT_STARTED。此处明确总览表中的响应为列表，待接口评审确认。
- 失败：404 PAPER_NOT_FOUND（试卷不存在）。无已提交答卷返回空数组。
- 权限：教师，校验 Paper.createdBy 等于 JWT subject。
- 对应 [module-03](../spec/module-03-grading.md) AC-1 / AC-12 / AC-14。

#### 6.4.3 POST /api/v1/answer-sheets/{id}/questions/{questionId}/ai-grade

- 请求：id 为答卷 ID，questionId 为该答卷所属试卷中的题目 ID。
- 成功 200：GradeResult，校验成功后返回，已有 SUCCEEDED 则复用。按单题幂等，整卷操作入口仍待 G-08。
- 失败：404 ANSWER_SHEET_NOT_FOUND（答卷不存在）；404 QUESTION_NOT_FOUND（题目不属于对应试卷）；409 ANSWER_NOT_SUBMITTED（答卷为 DRAFT）；409 AI_GRADING_IN_PROGRESS（该题处于 PENDING）；409 AI_ATTEMPT_LIMIT_REACHED（实际模型调用额度耗尽且无成功结果可复用）；409 AI_RESULT_DISCARDED（响应到达时已复核或尝试号失效）；502 AI_SERVICE_TIMEOUT（最终失败原因为模型超时）；502 AI_SERVICE_UNAVAILABLE（最终失败原因为非超时上游故障，如限流、连接异常或上游非成功响应）；502 AI_OUTPUT_INVALID（结构、评分点映射或评分一致性失败）；502 AI_SCORE_OUT_OF_RANGE（结构可校验但分数越界，优先于评分一致性检查）。新增映射待契约 v0.2 评审。
- 权限：教师，通过答卷的 paperId 校验 Paper.createdBy 等于 JWT subject，再校验题目归属。模型失败后允许人工复核。
- 对应 [module-03](../spec/module-03-grading.md) AC-1～AC-6 / AC-12～AC-14。

#### 6.4.4 PUT /api/v1/answer-sheets/{id}/questions/{questionId}/review

- 请求：路径参数同 6.4.3。请求体 { reviewedScore: integer（必填）, reviewComment?: string }。
- 成功 200：GradeResult，包含确认分、JWT 对应教师 ID 和服务端复核时间，保留已有 AI 结果。
- 失败：400 INVALID_REVIEWED_SCORE（确认分缺失、非整数或超出 [0, 题目分值]）；404 ANSWER_SHEET_NOT_FOUND（答卷不存在）；404 QUESTION_NOT_FOUND（题目不属于对应试卷）；409 ANSWER_NOT_SUBMITTED（草稿答卷，复用码待确认）。发布后能否改分待 G-02，未初评或初评中能否人工确认待 G-04。
- 权限：教师，通过答卷所属试卷校验 Paper.createdBy 等于 JWT subject，并校验题目归属。
- 对应 [module-03](../spec/module-03-grading.md) AC-6～AC-8 / AC-12～AC-14。

#### 6.4.5 POST /api/v1/papers/{id}/grades/publish

- 请求：id 为试卷 ID。
- 成功 200：{ publishedAt: datetime }，整场原子发布，按确认分汇总。重复请求不得改变成绩，原发布时间的返回规则待 G-02。
- 失败：404 PAPER_NOT_FOUND（试卷不存在）；409 GRADE_NOT_FULLY_REVIEWED（任一已提交答卷存在未确认题目，0 分为有效确认）。是否必须等考试结束及无答卷时的行为待 G-01。
- 权限：教师，校验 Paper.createdBy 等于 JWT subject。
- 对应 [module-03](../spec/module-03-grading.md) AC-9 / AC-10 / AC-12 / AC-13。

#### 6.4.6 GET /api/v1/my/grades/{paperId}

- 请求：paperId 为试卷 ID。
- 成功 200：PublishedGrade，仅返回本人确认分、教师意见和总分。
- 失败：404 ANSWER_SHEET_NOT_FOUND（按 JWT 身份和 paperId 查无本人已提交答卷）；403 SCORE_NOT_PUBLISHED（有本人已提交答卷但整场成绩未发布）。不得根据其他学生是否交卷改变响应。
- 权限：学生，按 (paperId, JWT subject) 查本人答卷。
- 对应 [module-03](../spec/module-03-grading.md) AC-10 / AC-11 / AC-12。

### 6.5 跨模块交接数据

跨模块采用**进程内只读接口 + DTO**，不使用事件总线（MVP1 禁止消息队列）。唯一例外是 Paper 生命周期的受控写命令（6.5.1，ADR-004）。

| 方向 | 数据契约（逻辑字段） | 约束 |
| --- | --- | --- |
| qbank → exam | `PaperForExam { paperId, title, totalScore, status, startAt, endAt, publishedAt, createdBy, items[{questionId, order, score, type, stem}] }` | 不包含参考答案与评分点；`exam` 发布时重新校验分值；qbank 侧由 `paper_items` 快照组装，`DRAFT` 用基线快照，`PUBLISHED` / `CLOSED` 用冻结的正式快照（待 ADR-001 通过）；`createdBy` 仅供进程内归属校验，不返回学生端 |
| qbank → grading | `QuestionForGrading { paperId, questionId, type, stem, referenceAnswer, totalScore, rubric[{rubricItemId, description, score, order}] }` | 只读；使用答卷所属的 `paperId` 与 `questionId` 作为组合键定位试卷快照，禁止回退按题目 ID 读取其他试卷的快照或当前题库内容（待 ADR-001 通过） |
| exam → grading | `SubmittedSheetForGrading { answerSheetId, paperId, studentId, submittedAt, submitType, answers[{questionId, content}] }` | 仅 `SUBMITTED`；只读，不改变答案与时间 |
| grading → 学生端 | `PublishedGrade { paperId, totalScore, items[{questionId, reviewedScore, reviewComment}] }` | 仅成绩发布后；不返回 `aiScore` / `aiReason` / `rubricHits` |
| grading → 教师端 | `GradingSheetView { answerSheetId, items[{questionId, aiStatus, rubricHits, aiScore, aiReason, reviewedScore, reviewComment, reviewedAt}] }` | 仅试卷创建教师可见 |

### 6.5.1 跨模块命令（受控写，ADR-004）

| 命令 / 查询 | 提供方 | 调用方 | 语义 |
| --- | --- | --- | --- |
| `PaperLifecyclePort.markPublished(paperId, teacherId, startAt, endAt, publishedAt)` | qbank | exam | 校验归属、`DRAFT`、非空、总分、窗口；写状态与窗口并冻结基线快照；返回 `PaperForExam` |
| `PaperLifecyclePort.markClosed(paperId)` | qbank | exam | 仅 `PUBLISHED → CLOSED`；已 `CLOSED` 按幂等处理 |
| `PaperDueQueryPort.findDuePapers(now)` | qbank | exam | 只读返回 `status=PUBLISHED && endAt <= now` 的 `[{paperId, endAt}]`，供自动交卷按“到期试卷”扫描 |

约束：

1. `markPublished` / `markClosed` 是 exam 写 Paper 的**唯一入口**；`findDuePapers` 是只读查询。exam 不得直接 SQL / Mapper 操作 `papers`。
2. `markPublished` 的校验失败由 qbank 返回领域错误，exam 映射为 6.3.1 的 `PAPER_NOT_FOUND` / `PAPER_NOT_DRAFT` / `EMPTY_PAPER` / `PAPER_SCORE_MISMATCH` / `INVALID_EXAM_WINDOW`。
3. 自动交卷以 `findDuePapers` 为起点，先交卷再 `markClosed`；零答卷试卷也必须关闭。
4. 端口是进程内调用，不新增 REST 端点；不在学生端暴露 `createdBy`。

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

1. 鉴权、归属、输入或业务前置条件校验失败，不启动模型调用、不写业务状态。已受理的模型调用失败应记录该次尝试、错误码和审计信息，最终失败将当前尝试置为 `FAILED`，不采纳非法建议分、不覆盖教师确认分、不提前写 `finalScore`。迟到响应受尝试号保护。
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
| ADR-001 | 已发布试卷取题目快照还是引用（基线快照 + 发布冻结） | C-01 | 孙宇萱（qbank） | 提议（待评审） |
| ADR-002 | 交卷并发与自动交卷幂等 | C-03 | 钱斓轩（exam） | 提议（PR #34，待评审） |
| ADR-003 | AI 初评调用、超时重试与幂等 | C-06 | 李昕彤 + grading | 本 PR 提交（提议） |
| ADR-004 | Paper 发布/关闭的跨模块写路径（qbank 受控命令） | Q-1 | 李昕彤 | 提议（待 qbank / exam 评审） |

仍在开放的问题：

| 编号 | 问题 | 负责人 | 计划 |
| --- | --- | --- | --- |
| Q-1 | Paper 发布/关闭的跨模块写路径 | 李昕彤 + 孙宇萱 / 钱斓轩 | ADR-004（提议，待评审） |
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
| v0.1-exam | 2026-11-18 | 钱斓轩 | 补充 exam 模块 6.3.1～6.3.10：逐接口请求/响应字段、失败码触发条件、权限与 AC 映射、自动交卷触发方式、成功/失败数据流与风险、与 grading 对齐及 Q-1～Q-8 决策/待确认项 |
