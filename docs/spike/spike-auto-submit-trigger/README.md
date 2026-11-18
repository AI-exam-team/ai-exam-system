# SP-03：自动交卷触发方式与调度漂移

| 项目 | 内容 |
| --- | --- |
| 编号 | SP-03 |
| 状态 | 进行中（**待执行**；本机无 MySQL 8 / Docker） |
| 主执行 | 李昕彤 |
| 复核 | 钱斓轩 |
| 日期 | 2026-11-18 |
| 关联 Issue | #32 |
| 依据 | `docs/spike/plan.md` 第 4 节；`adr/ADR-002-exam-submit-idempotency.md`；`adr/ADR-004-paper-lifecycle-write-path.md`；`docs/architecture.md` 6.3.8 / 6.5 |
| 红线 | 探针代码只放本目录，**禁止合并进 `src/`、`tests/`** |

## 结论（先行）

**结论：待执行。** 本机没有 MySQL 8 / Docker，尚未采集数据，不能标记「可行 / 不可行」。

待验证的预期结论：在 MySQL 8 单实例下，`@Scheduled(fixedDelay = 30s)` + `findDuePapers(now)` + `UPDATE ... WHERE status='DRAFT'` 能在 `endAt + 60s` 内把 10 份到期答卷全部置为 `SUBMITTED`，每份只迁移一次，零答卷试卷也能被 `markClosed`；进程重启后首轮扫描能补齐漏扫。

> 回填格式：`结论：可行 / 有条件可行 / 不可行` + 关键数据（10 份完成时间、重复迁移次数、零答卷关闭结果、重启补扫结果）+ 限制条件 + 对 ADR-002 的影响。

## 1. 验证问题

> 在单实例 Spring Boot / MySQL 8 下，用「定时扫描到期试卷 + 条件更新」能否可靠完成自动交卷：`endAt + 60s` 内全部 `DRAFT → SUBMITTED`、每份只迁移一次、零答卷试卷也能 `PUBLISHED → CLOSED`，并且进程重启后能补扫？

## 2. 假设

- 扫描间隔 30 秒时，`endAt` 后 60 秒内可覆盖全部到期答卷（最坏情况等待 30 秒 + 处理时间）。
- `findDuePapers(now)` 以到期试卷为起点，能覆盖「有 DRAFT 答卷」和「零答卷」两类试卷。
- 每份答卷的 `DRAFT → SUBMITTED` 由条件更新保证只发生一次；`submittedAt` 固定为 `paper.endAt`，不是扫描时刻。
- 手动交卷与自动交卷并发时，只有一方写入，另一方不覆盖。
- 进程重启后，首轮扫描能补齐重启期间漏掉的答卷；不需要补偿表。

## 3. 实验步骤

### 3.1 环境

- MySQL 8.x（Docker 或本机），`utf8mb4`、`InnoDB`。
- JDK 21 + Spring Boot 4.1（或最小调度循环，只要能复现 `fixedDelay` 与事务边界）。
- 单机、单实例；不接 Redis / MQ / Quartz。
- 记录：MySQL 版本、JDK 版本、CPU/内存、执行日期。

### 3.2 最小表

```sql
DROP TABLE IF EXISTS answer_items;
DROP TABLE IF EXISTS answer_sheets;
DROP TABLE IF EXISTS papers;

CREATE TABLE papers (
  id         VARCHAR(36) NOT NULL PRIMARY KEY,
  status     VARCHAR(16) NOT NULL,          -- DRAFT / PUBLISHED / CLOSED
  start_at   DATETIME(3) NOT NULL,
  end_at     DATETIME(3) NOT NULL,
  created_by VARCHAR(36) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE answer_sheets (
  id           VARCHAR(36) NOT NULL PRIMARY KEY,
  paper_id     VARCHAR(36) NOT NULL,
  student_id   VARCHAR(36) NOT NULL,
  status       VARCHAR(16) NOT NULL,        -- DRAFT / SUBMITTED
  started_at   DATETIME(3) NOT NULL,
  submitted_at DATETIME(3) NULL,
  submit_type  VARCHAR(8)  NULL,            -- MANUAL / AUTO
  UNIQUE KEY uk_answer_sheet_paper_student (paper_id, student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE answer_items (
  answer_sheet_id VARCHAR(36) NOT NULL,
  question_id     VARCHAR(36) NOT NULL,
  content         MEDIUMTEXT NOT NULL,
  saved_at        DATETIME(3) NOT NULL,
  PRIMARY KEY (answer_sheet_id, question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.3 数据与时间线

1. 建 3 张 `PUBLISHED` 试卷，`endAt = 当前时间 + 60 秒`：
   - 试卷 A：5 份 `DRAFT` 答卷；
   - 试卷 B：0 份答卷；
   - 试卷 C：1 份 `SUBMITTED` 答卷（验证不被改写）。
2. 每份 DRAFT 答卷写入 1~2 条 `answer_items`，模拟“最后一次成功保存”。
3. 手动交卷与自动交卷并发用例单独准备一份 DRAFT。

### 3.4 三种方案

| 方案 | 触发 | 预期 |
| --- | --- | --- |
| A 仅定时 | 每 30 秒 `findDuePapers(now)` + 条件更新 + `markClosed` | 到期后 60 秒内全部交卷；零答卷试卷关闭 |
| B 仅惰性 | 学生下次请求时检查并交卷 | 无人访问的答卷永远停在 `DRAFT`（应失败） |
| C 定时 + 请求兜底 | A + 学生请求时对本人 DRAFT 执行同一条件更新 | 与 A 相同，且调度短暂不可用时可兜底 |

### 3.5 扫描逻辑（复用 ADR-002 / ADR-004）

```sql
-- 1. qbank 只读端口：到期试卷
-- findDuePapers(now) => [{paperId, endAt}] WHERE status='PUBLISHED' AND end_at <= now

-- 2. 对每张到期试卷，逐份条件更新
UPDATE answer_sheets
   SET status='SUBMITTED',
       submitted_at = ?,          -- paper.endAt，不是扫描时刻
       submit_type = 'AUTO'
 WHERE paper_id = ?
   AND status = 'DRAFT';

-- 3. 该试卷无剩余 DRAFT 后
-- markClosed(paperId)  // qbank 受控命令，PUBLISHED -> CLOSED
```

> 扫描不得直接查询 qbank 的 `papers` 表；必须通过 `findDuePapers` / `PaperLifecyclePort`（ADR-004）。

### 3.6 重启与并发

1. 在 `endAt` 前 10 秒杀掉进程，`endAt + 30s` 前重启；记录首轮扫描补齐时间。
2. 手动交卷与扫描同时到达：记录最终 `submitted_at` / `submit_type`，确认只来自一方。
3. 每轮记录：到期时间、扫描开始/结束、每份答卷的 `submittedAt`、重复迁移次数、试卷最终状态。

### 3.7 记录表

每轮一行，填入 `evidence/rounds.csv`：

| 轮次 | 方案 | 到期数 | endAt+60s 完成数 | 重复迁移数 | 零答卷试卷关闭 | 重启补扫 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | A | | | | | | |
| 2 | B | | | | | | |
| 3 | C | | | | | | |

同时保留：建表 SQL、扫描日志（脱敏）、MySQL/JDK 版本、执行日期。

## 4. 成功标准

- 方案 A 或 C 在 `endAt + 60s` 内完成 10/10 份 DRAFT 答卷；每份只迁移一次。
- 所有自动交卷 `submittedAt = endAt`、`submitType=AUTO`；`SUBMITTED` 答卷不被改写。
- 零答卷试卷 B 在到期后被 `CLOSED`。
- 进程重启后首轮扫描能补齐漏扫，无需补偿表。
- 手动交卷与自动交卷并发时只有一方写入。
- 扫描只调用 `findDuePapers` / `markClosed`，不直接读/写 qbank 的 `papers` 表。

## 5. 结论回填位置

| 内容 | 回填到 |
| --- | --- |
| 实测数据与结论 | 本文件「结论（先行）」+ `evidence/rounds.csv` |
| 扫描间隔、单批上限、完成率 | `adr/ADR-002-exam-submit-idempotency.md` 第 4 / 5 / 8 节 |
| 到期试卷扫描与关闭 | `docs/architecture.md` 6.3.8 / 6.5；ADR-004 |
| 探针状态 | `docs/spike/README.md` 第六节；`docs/spike/plan.md` SP-03 记录 |

## 6. 明确不做

- 不写答题页面、不写正式 exam 业务代码、不合并 `src/` / `tests/`。
- 不引入 Quartz、Redis、消息队列、分布式锁。
- 不做压力测试平台、不做 MySQL 参数调优。
- 不用 SQL Server / SQLite 替代 MySQL 8（SP-04 的教训：环境不一致的结论不能外推）。

## 7. 当前阻塞与执行方式

**阻塞**：本机没有 MySQL 8、没有 Docker，无法采集有效数据。

**执行方式（二选一）**：

```bash
# 方式 1：Docker
docker run --name spin-mysql8 -e MYSQL_ROOT_PASSWORD=spike \
  -e MYSQL_DATABASE=spike -p 3306:3306 -d mysql:8.0

# 方式 2：本机 MySQL 8，建独立 schema
mysql -u root -p -e "CREATE DATABASE spike CHARACTER SET utf8mb4;"
```

执行后把 `SELECT VERSION()`、轮次数据与日志写入 `evidence/`，再把本文件状态改为「已完成」并写结论。未执行前不得标记「可行」。

## 8. 变更记录

| 日期 | 变更 | 原因 |
| --- | --- | --- |
| 2026-11-18 | 建立 SP-03 探针：三种触发方案、到期试卷扫描、零答卷关闭、重启补扫；因本机无 MySQL 8 标记为待执行 | 为 ADR-002 的扫描间隔与 `markClosed` 顺序提供实测依据 |
