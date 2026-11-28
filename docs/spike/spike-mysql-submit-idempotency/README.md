# SP-02：MySQL 并发交卷幂等

| 项目 | 内容 |
| --- | --- |
| 编号 | SP-02 |
| 状态 | 已完成（2026-11-18） |
| 主执行 | 钱斓轩 |
| 复核 | 李昕彤 |
| 日期 | 2026-11-18 |
| 关联 Issue | #32 |
| 依据 | `docs/spike/plan.md` 第 3 节；`adr/ADR-002-exam-submit-idempotency.md`；`docs/architecture.md` 6.3.6 / 6.3.8 |
| 红线 | 探针代码只放本目录，**禁止合并进 `src/`、`tests/`** |

## 结论（先行）

**结论：可行。** 在 MySQL 8.0.37 / REPEATABLE-READ / utf8mb4 下，「唯一约束 + 条件更新」组合满足并发交卷幂等：

- **方案 C（唯一约束 + 条件更新）**：10 轮 × 50 并发，每轮恰好 **1 次成功 / 49 次冲突 / 1 行答卷**；`submitted_at` 与 `submit_type` 在成功后不再变化。
- **方案 A（仅唯一约束）**：并发插入同一 `(paper_id, student_id)` 为 1 成功 / 1 重复、1 行；但去掉 `AND status='DRAFT'` 的无条件 `UPDATE` 两次都成功 → **唯一约束单独不能防止重复状态迁移**。
- **方案 B（仅条件更新）**：去掉唯一约束后，两个并发插入产生 **2 行** → **条件更新单独不能防止第二份答卷**；50 并发条件更新仍为 1 成功 / 49 冲突。
- **手动 vs 自动**：1 成功 / 1 冲突，最终 `submit_type=AUTO`、`submitted_at=endAt`，未被手动请求覆盖。
- **回滚**：同一事务内先写 `answer_items`、条件更新 0 行后 `ROLLBACK`，`answer_items` 无残留。

因此 ADR-002 的「唯一约束 + 条件更新」组合是必要的；单独任一项都不够。限制：单机 MySQL、REPEATABLE-READ、50 线程；未测多实例与网络分区。

## 1. 验证问题

> 在 MySQL 8 下，用「唯一约束 + 条件更新」能否保证手动交卷与重复请求并发时只发生一次 `DRAFT → SUBMITTED` 状态迁移，且已交卷内容与 `submitted_at` 不被覆盖？

## 2. 假设

- `(paper_id, student_id)` 唯一约束保证同一学生同一试卷最多一行答卷；并发首次进入不会产生第二份。
- `UPDATE answer_sheets SET status='SUBMITTED', submitted_at=?, submit_type=? WHERE id=? AND status='DRAFT'` 在 50 个并发重复请求下只有 1 个请求影响 1 行，其余影响 0 行。
- 条件更新影响 0 行时，若在事务中先写了答案，回滚后不会修改已交卷内容。
- 手动交卷与自动交卷同时到达时，只有先执行条件更新的一方写入 `submitted_at`，后到者不覆盖。
- 上述行为在 10 轮重复实验中稳定，不依赖线程调度顺序。

## 3. 实验步骤

### 3.1 环境

- MySQL 8.0.37（Docker 容器 `mysql8`），`utf8mb4`，`InnoDB`，隔离级别 `REPEATABLE-READ`。
- JDK 26（Temurin 26.0.2.1）运行单文件 Java；项目目标为 Java 21，语法兼容。MySQL Connector/J 9.7.0。
- 单机、单进程；不接 Spring、不接业务代码。
- 记录：MySQL 版本、Connector/J 版本、CPU/内存、执行日期（2026-11-18）。

### 3.2 最小表

```sql
-- 仅在专用、可丢弃的本地实验库中执行；不要连接生产或共享数据库。
USE sp02_probe;

DROP TABLE IF EXISTS answer_sheets;

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

-- 答案明细：验证「先写答案、条件更新 0 行、回滚」用
CREATE TABLE answer_items (
  answer_sheet_id VARCHAR(36) NOT NULL,
  question_id      VARCHAR(36) NOT NULL,
  content          MEDIUMTEXT  NOT NULL,
  saved_at         DATETIME(3) NOT NULL,
  PRIMARY KEY (answer_sheet_id, question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.3 并发脚本

最小 Java 单文件（`SubmitIdempotencySpike.java`，放在本目录，**不放进 `src/`**）：

1. 每轮插入 1 份 `DRAFT` 答卷（固定 `id`、`paper_id`、`student_id`）。
2. 用 `ExecutorService` 开 50 个线程，`CountDownLatch` 让它们尽量同时开始。
3. 每个线程执行同一条条件更新，记录 `executeUpdate()` 返回值（1 / 0）与异常。
4. 主线程汇总：成功数、冲突数、`SELECT COUNT(*)`、最终 `status` / `submitted_at` / `submit_type`。
5. 重复 10 轮，每轮前重置数据。
6. 回滚用例：在同一事务中先 upsert 一条 `answer_items`，再执行一个必定 0 行的条件更新（例如把 `status` 预先改为 `SUBMITTED`），回滚后确认 `answer_items` 没有新增/修改。
7. 对照组：
   - **A 仅唯一约束**：两个线程同时插入同一 `(paper_id, student_id)`，验证只成功 1 行；不测状态迁移。
   - **B 仅条件更新**：去掉唯一约束，只保留条件更新，验证重复交卷不双成功。
   - **C 唯一约束 + 条件更新**：生产方案，跑 50 并发 × 10 轮。
8. 手动 vs 自动：一个线程用 `submitted_at = NOW(3)`、`submit_type='MANUAL'`；另一个线程用 `submitted_at = end_at`、`submit_type='AUTO'`，同时执行条件更新；确认最终值只来自一方。

运行方式（示例）：

```bash
javac -cp mysql-connector-j-8.x.jar SubmitIdempotencySpike.java
java -cp ".;mysql-connector-j-8.x.jar" SubmitIdempotencySpike
```

> Windows 用 `;` 分隔 classpath；Linux/macOS 用 `:`。数据库连接串与口令只从环境变量读取，不写进脚本。

### 3.4 记录表

每轮一行，填入 `evidence/rounds.csv`：

| 轮次 | 方案 | 成功迁移数 | 冲突数 | answer_sheets 行数 | 最终 status | 最终 submitted_at | 最终 submit_type | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:49.727 | MANUAL | 50 线程 |
| 2 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:49.996 | MANUAL | 50 线程 |
| 3 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:50.415 | MANUAL | 50 线程 |
| 4 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:50.690 | MANUAL | 50 线程 |
| 5 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:50.953 | MANUAL | 50 线程 |
| 6 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:51.212 | MANUAL | 50 线程 |
| 7 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:51.468 | MANUAL | 50 线程 |
| 8 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:51.743 | MANUAL | 50 线程 |
| 9 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:52.004 | MANUAL | 50 线程 |
| 10 | C | 1 | 49 | 1 | SUBMITTED | 2026-11-18 06:52:52.250 | MANUAL | 50 线程 |

补充对照：

| 场景 | 结果 |
| --- | --- |
| A 仅唯一约束 | 并发插入 1 成功 / 1 重复、1 行；无条件 `UPDATE` 2/2 成功（不能单独防重复迁移） |
| B 仅条件更新 | 并发插入 2 行；50 并发条件更新 1 成功 / 49 冲突（不能单独防第二份答卷） |
| 手动 vs 自动 | 1 成功 / 1 冲突；最终 `AUTO`、`submitted_at=endAt`，未被覆盖 |
| 回滚 | 条件更新 0 行后 `ROLLBACK`；`answer_items` 0 行残留 |

脚本与原始 CSV（`Sp02.java`、`rounds.csv`）保留在本机探针目录，未合入 docs PR；本文件只保留可复核的数据摘要。

## 4. 成功标准

- 方案 C 的 10 轮中，每轮**恰好 1 次**成功迁移，其余 49 个请求全部冲突；`answer_sheets` 始终 1 行。
- `submitted_at` 与 `submit_type` 在首轮成功后不再变化；手动 vs 自动场景只有一方写入。
- 条件更新影响 0 行时，事务回滚后答案表/答卷内容与交卷前一致（补一条「先写答案再更新失败」的用例）。
- 结论能直接落到 ADR-002 的具体 SQL、错误码（409 `EXAM_ALREADY_SUBMITTED`）与第 10 周测试用例。
- 若方案 C 出现双成功或 `submitted_at` 被覆盖：标记「不可行」，记录失败轮次与日志，ADR-002 改为悲观锁或其他方案。

## 5. 结论回填位置

| 内容 | 回填到 |
| --- | --- |
| 实测数据与结论 | 本文件「结论（先行）」+ `evidence/rounds.csv` |
| SQL 与错误码确认 | `adr/ADR-002-exam-submit-idempotency.md` 第 1～3、7 节 |
| 接口行为与检查顺序 | `docs/architecture.md` 6.3.6 / 6.3.8 |
| 探针状态 | `docs/spike/README.md` 第六节；`docs/spike/plan.md` SP-02 认领记录 |

## 6. 明确不做

- 不写答题页面、不接 Spring 业务层、不写正式 `AnswerSheet` 业务代码。
- 不引入 Redis、消息队列、分布式锁、Quartz。
- 不合并 `src/`、`tests/`；脚本与证据只保留在本目录或 `spike/spike-mysql-submit-idempotency` 分支。
- 不做压力测试平台、不做 MySQL 参数调优。

## 7. 风险与限制

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 本机 MySQL 版本/隔离级别与第 10 周环境不同 | 结论可能不可直接复用 | 记录 `SELECT VERSION()`、`@@transaction_isolation`；在 Docker MySQL 8 上复跑 |
| 50 线程在单机可能被调度成串行，掩盖竞争 | 高估方案可靠性 | 用 `CountDownLatch` 同步起跑；记录实际并发窗口；必要时提高到 100 线程 |
| 条件更新 0 行后的回滚行为未验证 | 可能修改已交卷答案 | 增加「先 upsert 答案、再条件更新 0 行、回滚」用例，检查答案表 |
| 自动交卷与手动交卷的时间参数不同 | `submitted_at` 语义混淆 | 明确手动=服务端当前时间、自动=`end_at`；结果表分别记录 |
