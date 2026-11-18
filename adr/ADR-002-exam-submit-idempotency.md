# ADR-002：交卷幂等与自动交卷的触发方式

| 字段 | 内容 |
| --- | --- |
| 编号 | ADR-002 |
| 标题 | 交卷采用唯一约束 + 条件更新保证幂等；自动交卷采用定时扫描 + 请求兜底 |
| 状态 | 提议（SP-02 / SP-03 实验已验证；待 exam 组与集成负责人评审） |
| 日期 | 2026-11-18 |
| 决策者 | 钱斓轩（exam） |
| 评审人 | 李昕彤（集成与契约）、左恩东（grading，跨模块影响） |
| 关联需求 | `spec/contract-v0.1.md` C-03、R5；`spec/module-02-exam.md` AC-5 / AC-6、FR-6 / FR-9；`docs/architecture.md` 6.3；`docs/dependency.md` R-01 / R-08 |
| 关联 Issue | #32（第 8 周 exam 文档任务） |

## 背景

交卷是 exam 模块唯一同时涉及「学生主动操作 + 服务端定时操作 + 网络重试」的状态迁移：

- 学生可能双击交卷、网络超时后重试，或前端在收到成功响应前重复提交。
- 到达 `endAt` 时，服务端必须自动交卷；自动任务可能与学生的手动交卷同时到达。
- 同一学生同一试卷只能有一份答卷；重复请求不能生成第二份，也不能覆盖已交卷的答案与 `submittedAt`。
- 课程约束：单体应用、仅 MySQL，**禁止 Redis / 消息队列 / 微服务**（`context.md` 第 5 节），因此不能用分布式锁或 MQ 承担幂等。
- 自动交卷若只靠「学生下次请求时惰性触发」，无人访问的答卷会永远停在 `DRAFT`，阻塞 grading。
- 自动交卷若只靠定时任务，进程重启或调度漂移期间可能漏扫；必须有补偿路径。

不决策的后果：重复交卷、`submittedAt` 被覆盖、生成第二份答卷；`DRAFT` 答卷漏交导致 grading 无法开始；第 9 周无法拆出可测试的交卷任务。

## 决策

**MVP1 采用「`(paper_id, student_id)` 唯一约束 + `UPDATE ... WHERE status='DRAFT'` 条件更新 + 定时扫描（请求兜底）」：**

### 1. 答卷唯一性

`answer_sheets` 加唯一约束，保证同一学生同一试卷最多一份答卷：

```sql
CREATE TABLE answer_sheets (
  id           VARCHAR(36)  NOT NULL PRIMARY KEY,
  paper_id     VARCHAR(36)  NOT NULL,
  student_id   VARCHAR(36)  NOT NULL,
  status       VARCHAR(16)  NOT NULL,          -- DRAFT / SUBMITTED
  started_at   DATETIME(3)  NOT NULL,
  submitted_at DATETIME(3)  NULL,
  submit_type  VARCHAR(8)   NULL,              -- MANUAL / AUTO
  version      INT          NOT NULL DEFAULT 0,
  UNIQUE KEY uk_answer_sheet_paper_student (paper_id, student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

> 答案明细表 `answer_items` 略；本 ADR 只约束状态迁移，答案写入与状态迁移在同一事务内完成。

并发首次进入时，两个请求都尝试插入；唯一约束让一方成功，另一方捕获重复键后**重新读取并返回已有答卷**，不返回 500。

### 2. 状态迁移只走条件更新

所有 `DRAFT → SUBMITTED` 都执行同一条条件更新：

```sql
UPDATE answer_sheets
   SET status = 'SUBMITTED',
       submitted_at = ?,
       submit_type = ?,
       version = version + 1
 WHERE id = ?
   AND status = 'DRAFT';
```

- 影响行数 `1`：本次请求赢得迁移，继续提交事务。
- 影响行数 `0`：说明已被其他请求（手动重试、自动交卷）迁移，或 `id` 不存在；重新读取后分别返回 `409 EXAM_ALREADY_SUBMITTED` 或 `404 ANSWER_SHEET_NOT_FOUND`。
- 不使用「先查状态、再更新」的两步写法；该写法在并发下会双成功。

### 3. 手动交卷的事务边界

`POST /api/v1/answer-sheets/{id}/submit` 在同一事务内完成：

1. 校验 JWT 归属、答卷存在、时间窗口、请求体（全量答案）；
2. 按题 upsert 本次提交的答案；
3. 执行第 2 条的条件更新；
4. 条件更新影响 `0` 行时**回滚答案写入**并返回 409，避免修改已交卷答卷；
5. 影响 `1` 行时提交，`submitted_at` 取本次事务的服务端时间。

这样 AC-11「最后一次自动保存失败后交卷不丢答案」成立：交卷请求携带的全量答案与状态迁移同生共死。

### 4. 自动交卷：定时扫描为主，请求兜底为辅

**主机制**：单实例 `@Scheduled(fixedDelay = 30_000)` 扫描到期答卷。扫描分两步，**不直接 JOIN qbank 的 `papers` 表**：

```sql
-- 步骤 1：只查 exam 自有表，取出待检查的答卷
SELECT id, paper_id
  FROM answer_sheets
 WHERE status = 'DRAFT'
 LIMIT 200;

-- 步骤 2：对去重后的 paper_id，调用 qbank 只读接口 PaperForExam，
--         取得 status / endAt；仅当 status='PUBLISHED' 且 endAt <= NOW()
--         时，对该 paper 下的 DRAFT 答卷执行第 2 条条件更新。
```

> 跨模块读取走 `docs/architecture.md` 6.5 的 `PaperForExam`，不直接读 qbank 表（依赖规则 4.1 第 3 条）。MVP1 演示规模下按 `paper_id` 去重后逐张查询即可；若第 9 周实测 N+1 影响扫描时间，再评估「qbank 提供 `findDuePapers(now)` 只读接口」或「同库 JOIN 例外」，两者都需要 ADR 留痕（见 Q-6）。

对每一份答卷执行第 2 条条件更新，参数为：

- `submitted_at = paper.endAt`（**不是扫描时刻**，符合 AC-5 / contract 2.4）；
- `submit_type = 'AUTO'`。

**兜底机制**：学生在 `endAt` 后调用进入、保存或交卷接口时，先对本人 `DRAFT` 答卷执行同一条件更新，再返回 `403 EXAM_CLOSED`。兜底不替代定时扫描，只覆盖「调度器短暂不可用 + 学生恰好访问」的场景。

**为什么不只用惰性触发**：无人访问的答卷永远不会交卷，grading 无法开始；这不是可接受的失败模式。

### 5. 试卷关闭顺序

到达 `endAt` 后，对每张试卷：

1. 先完成该试卷所有 `DRAFT` 答卷的自动交卷；
2. 全部成功（或本来就没有 `DRAFT` 答卷）后，再执行 `UPDATE papers SET status='CLOSED' WHERE id=? AND status='PUBLISHED'`；
3. 任一份失败则本轮不关闭该试卷，下一轮重试，避免 `CLOSED` 后无法再自动交卷。

> 写路径待 Q-1 裁决：`Paper` 归 qbank，exam 不能直接跨模块改表；见 `docs/architecture.md` 6.3.1 与 6.3.10。

### 6. 并发结果矩阵

| 场景 | 结果 |
| --- | --- |
| 手动交卷 vs 手动交卷（双击/重试） | 一方 200；另一方条件更新 0 行 → 409 `EXAM_ALREADY_SUBMITTED`；答案与 `submittedAt` 不变 |
| 手动交卷 vs 自动交卷 | 先执行条件更新者成功；另一方 0 行 → 手动返回 409（若窗口检查已过 `endAt` 则返回 403），自动静默跳过并记日志 |
| 自动交卷 vs 自动交卷（扫描重叠） | 条件更新保证只有一次迁移；使用 `fixedDelay` 而非 `fixedRate`，单实例下不重叠 |
| 首次进入 vs 首次进入 | 唯一约束一方成功；另一方重新读取并返回已有答卷（200） |
| 手动交卷请求已过窗口 | 条件更新前返回 403 `EXAM_CLOSED`；由自动交卷接管，使用最后成功保存的答案 |

### 7. 错误码

| 场景 | 返回 |
| --- | --- |
| 重复交卷 / 自动交卷已先完成 | `409 EXAM_ALREADY_SUBMITTED` |
| 窗口外手动交卷且仍为 `DRAFT` | `403 EXAM_CLOSED` |
| 未到开始时间 | `403 EXAM_NOT_STARTED` |
| 答卷不存在 | `404 ANSWER_SHEET_NOT_FOUND` |
| 请求体缺题/多题/重复、内容超长 | `400 VALIDATION_ERROR`（待登记） |

不新增交卷专用错误码；`PAPER_NOT_DRAFT` 仅用于发布接口，见 architecture 6.3.1。

### 8. 验证方式

- **SP-02**：50 个并发请求重复交卷同一答卷，重复 10 轮；每轮恰好 1 次成功迁移、1 行答卷、`submitted_at` 不被改写。分别测试「仅唯一约束」「仅条件更新」「两者组合」，证明组合是必要的。
- **SP-03**：10 份 `DRAFT` 答卷、`endAt` 设为 1 分钟后；方案 A（仅定时）、B（仅惰性）、C（定时 + 惰性兜底）对比；C 应在 `endAt + 60s` 内完成 10/10，0 次重复迁移。
- **第 10 周测试**：AC-5 / AC-6 / AC-11 / FR-9；重点覆盖「手动 + 自动同时到达」「进程重启后补扫」「条件更新 0 行回滚答案」。

## 验证结果（2026-11-18）

| 探针 | 环境 | 结果 | 结论 |
| --- | --- | --- | --- |
| SP-02 | MySQL 8.0.37 / REPEATABLE-READ / 50 线程 | C 方案 10 轮 × 50 并发：每轮 1 成功 / 49 冲突 / 1 行；A 仅唯一约束时无条件 `UPDATE` 2/2 成功；B 仅条件更新时并发插入 2 行；手动 vs 自动 1 成功 / 1 冲突，`AUTO` 未被覆盖；回滚后答案无残留 | 可行；唯一约束 + 条件更新缺一不可 |
| SP-03 | MySQL 8.0.37 / 单实例 `ScheduledExecutorService` / 30s 扫描 | A 10/10，最大触发延迟 10.1s；B 5/10，5 份仍 `DRAFT`；C 10/10，0 重复；重启首轮 10/10 补齐 | 可行；采用定时扫描 + 请求兜底 |

## 备选方案

| 方案 | 优点 | 缺点 | 未采用原因 |
| --- | --- | --- | --- |
| A. 无并发控制：先查 `status` 再更新 | 实现最简单 | 两个请求可同时读到 `DRAFT`，双成功；`submittedAt` 被覆盖 | 违反 AC-6 / FR-9，直接排除 |
| B. 唯一约束 + 条件更新（**采用**） | 仅用 MySQL；一次原子迁移；可测试；符合单实例 MVP | 需要处理 0 行后的分支与事务回滚 | — |
| C. 悲观锁 `SELECT ... FOR UPDATE` | 语义直观 | 锁持有时间长、死锁风险高；对单行状态迁移收益低 | 不如条件更新轻量；MVP 不需要 |
| D. Redis / MQ 分布式锁 | 多实例下更强 | 课程明确禁止 Redis、MQ、微服务 | 范围红线，直接排除 |
| E. 仅惰性触发自动交卷 | 实现最少 | 无人访问的答卷永不交卷，grading 被阻塞 | 失败模式不可接受 |
| F. 仅定时扫描 | 无人访问也能交卷 | 调度器停机/漂移期间漏扫；重启前答卷一直 `DRAFT` | 作为主机制可以，但必须加请求兜底 |
| G. Quartz / 调度框架 | 功能完整 | 引入新依赖，超出课程技术栈 | MVP1 禁止新增依赖 |

**为什么选 B + F（定时扫描）+ 请求兜底**：幂等只依赖 MySQL 的唯一约束与条件更新，不引入锁或中间件；自动交卷以定时扫描保证「无人访问也能交」，以请求兜底覆盖调度器短暂不可用。SP-02/SP-03 用实测数据验证这两个假设，而不是凭感觉。

## 后果

### 正面影响

- 同一答卷最多一次 `DRAFT → SUBMITTED`，重复请求、双击、网络重试都得到确定的 409。
- 自动交卷不依赖学生在线；进程重启后首轮扫描自动补齐。
- 交卷与答案写入同事务，AC-11 的「不丢答案」可测试。
- 只依赖 MySQL 与 Spring `@Scheduled`，技术栈不越界，第 9 周可拆成「唯一约束、条件更新、手动交卷事务、自动扫描」四个任务。

### 负面影响 / 代价

- 自动交卷有最多约 30 秒的延迟；`submittedAt` 仍记为 `endAt`，但学生看到「已交卷」可能比 `endAt` 晚。
- 单实例假设：多实例部署时两个调度器会同时扫描；条件更新保证不重复迁移，但会产生无效扫描。MVP1 单实例可接受；多实例需另起 ADR（如 ShedLock 或数据库抢占）。
- `fixedDelay` 扫描会占用一个调度线程；单批 200 份、每份一次条件更新，正常规模可接受。
- 试卷 `CLOSED` 的写路径尚未裁决（Q-1），实现前必须解决，否则自动交卷完成后无法正确关闭试卷。
- 需要契约升版登记 `VALIDATION_ERROR`；`PAPER_NOT_DRAFT` 是否登记待集成负责人决定。

### 后续需要完成的事项

- [x] SP-02：执行 50 并发 × 10 轮实验，回填成功/冲突/行数/`submitted_at` 数据（钱斓轩）。
- [x] SP-03：执行三种触发方案对比，回填扫描间隔与漂移结论（钱斓轩主、李昕彤复核）。
- [ ] 契约 v0.2：登记 `VALIDATION_ERROR`；决定 `PAPER_NOT_DRAFT` 是否入表（集成负责人）。
- [ ] Q-1：裁决 `Paper` 发布/关闭写路径；同步 `architecture.md` 6.3.1 / 6.3.8（李昕彤 + qbank）。
- [ ] Q-2：G-01 若要求 `CLOSED` 后才能发布成绩，补 `ExamProgressForGrading` DTO（李昕彤 + 左恩东）。
- [ ] Q-6：自动交卷扫描读取 `Paper.status/endAt` 走 qbank 只读接口；若改为同库 JOIN，先补 ADR 例外（李昕彤 + 钱斓轩）。
- [ ] Q-7：6.5 `PaperForExam` 补 `startAt` / `endAt` / `publishedAt` / `createdBy`，否则自动交卷无法判断窗口（李昕彤 + qbank）。
- [ ] 第 10 周测试：唯一约束、条件更新 0 行回滚、手动/自动并发、重启补扫、窗口边界。
- [ ] 若 SP-02/SP-03 结论推翻假设，另起 ADR 替代本决策，并在本文件标注「被 ADR-XXXX 替代」。

## 关联需求 / Issue

- 需求：`spec/contract-v0.1.md` C-03、R5；`spec/module-02-exam.md` AC-5 / AC-6 / AC-11、FR-6 / FR-9；`docs/architecture.md` 6.3；`docs/dependency.md` R-01 / R-08
- Issue：#32
- 相关 ADR：ADR-001（试卷快照，影响自动交卷读取的题目版本）、ADR-003（AI 初评幂等，与本 ADR 共享「唯一约束 + 条件更新」思路但对象不同）
