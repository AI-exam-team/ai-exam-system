# SP-03：自动交卷触发方式与调度漂移

| 项目 | 内容 |
| --- | --- |
| 编号 | SP-03 |
| 状态 | 已完成（2026-11-18） |
| 主执行 | 钱斓轩 |
| 复核 | 李昕彤 |
| 日期 | 2026-11-18 |
| 关联 Issue | #32 |
| 依据 | `docs/spike/plan.md` 第 4 节；`adr/ADR-002-exam-submit-idempotency.md`；`docs/architecture.md` 6.3.8 |
| 红线 | 探针代码只放本目录/探针分支，**禁止合并进 `src/`、`tests/`** |

## 结论（先行）

**结论：可行。** 在 MySQL 8.0.37 / REPEATABLE-READ / utf8mb4、单实例 JDK 调度器下：

- **方案 A（仅定时扫描，30s 间隔）**：10/10 在 `endAt` 后 **10.1s** 内完成，`version` 最大 1（0 次重复迁移）。
- **方案 B（仅惰性触发）**：只有 5/10 被模拟请求触发，另外 **5 份永远是 `DRAFT`** → 不能单独使用。
- **方案 C（定时 + 惰性兜底）**：10/10 完成，0 次重复迁移；前 5 份由惰性请求在 ~5.1s 完成，后 5 份由定时扫描在 ~10.1s 完成。
- **重启补偿**：`endAt` 已过 5s 后启动扫描器，首轮扫描 10/10 补齐，最大延迟 ~5.1s，0 次重复。

结论支持 ADR-002 的「定时扫描 + 请求兜底」：30s 间隔下最坏延迟不超过一个扫描周期（30s），在 `endAt + 60s` 目标内。限制：用 `ScheduledExecutorService` 模拟 `@Scheduled`，未接 Spring；单实例；未测多实例与调度器长时间停机；**零答卷试卷关闭未覆盖**，6.3.8 已改为 `findDuePapers(now)` 枚举到期试卷，第 10 周补「零答卷 → CLOSED」测试。

## 1. 验证问题

> 在单实例 Spring Boot / 单实例调度器下，定时扫描（`@Scheduled`）与「学生下次请求时惰性触发」两种方式，哪一种能在 `endAt` 后可靠地把 `DRAFT` 答卷置为 `SUBMITTED`，且不会重复交卷？

## 2. 假设

- 单实例定时扫描每 30 秒执行一次，在 `endAt` 后 60 秒内可完成全部到期答卷的自动交卷。
- 定时扫描与手动交卷并发时，条件更新保证只有一次 `DRAFT → SUBMITTED`（复用 SP-02 结论）。
- 惰性触发实现更简单，但存在「无人访问则永不交卷」的漏洞，不能单独使用。
- 进程重启后首轮扫描能补齐 `endAt` 已过的 `DRAFT` 答卷，无需补偿表。
- 自动交卷的 `submittedAt` 应记为 `endAt`，而不是扫描时刻。

## 3. 实验步骤

### 3.1 环境

- 单实例；MySQL 8.0.37（Docker 容器 `mysql8`，`REPEATABLE-READ`，utf8mb4）；JDK 26（Temurin 26.0.2.1）；MySQL Connector/J 9.7.0；不引入 Quartz、消息队列、Redis。
- 为贴近 `@Scheduled` 的单线程调度语义，用 JDK `ScheduledExecutorService.scheduleWithFixedDelay` 模拟；记录该限制，结论按「单实例定时扫描」而非特定框架表述。
- 若第 9 周实现用 Spring `@Scheduled`，默认单线程调度与 `fixedDelay` 语义一致。

### 3.2 最小表

```sql
DROP TABLE IF EXISTS spike_sheets;

CREATE TABLE spike_sheets (
  id           VARCHAR(36) NOT NULL PRIMARY KEY,
  status       VARCHAR(16) NOT NULL,          -- DRAFT / SUBMITTED
  end_at       DATETIME(3) NOT NULL,
  submitted_at DATETIME(3) NULL,
  submit_type  VARCHAR(8)  NULL,              -- AUTO / MANUAL
  version      INT         NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.3 三种方案

| 方案 | 触发方式 | 预期 |
| --- | --- | --- |
| A 仅定时扫描 | 每 30 秒扫描 `status='DRAFT' AND end_at <= NOW()`，逐份条件更新 | 10/10 在 `endAt + 60s` 内交卷 |
| B 仅惰性触发 | 只有「学生请求」到达时才条件更新；模拟 5/10 份有请求 | 5 份交卷，5 份永远 `DRAFT`，证明不能单独使用 |
| C 定时扫描 + 惰性兜底 | 定时扫描为主；学生请求到达时先对本人 `DRAFT` 条件更新 | 10/10 交卷；兜底不产生重复迁移 |

### 3.4 步骤

1. 建 10 份 `DRAFT` 答卷，`end_at = NOW(3) + 1 分钟`。
2. 方案 A：启动扫描器，每 30 秒扫描一次；记录每份的 `submitted_at`、`submitted_at - end_at`、重复迁移次数。
3. 方案 B：不启动扫描器，只对第 1～5 份模拟一次请求；观察第 6～10 份是否仍为 `DRAFT`。
4. 方案 C：启动扫描器，同时对第 1～5 份模拟请求；确认 10/10 交卷、0 重复迁移。
5. 重启补偿：在 `end_at` 已过后启动扫描器，确认首轮扫描补齐所有 `DRAFT`。
6. 记录：完成数、`submitted_at - end_at` 的最大/中位数、重复迁移次数、重启后的行为。

### 3.5 记录表

| 方案 | 完成数 / 10 | 最大 `submittedAt - endAt` | 中位 `submittedAt - endAt` | 重复迁移 | 备注 |
| --- | --- | --- | --- | --- | --- |
| A 仅定时 | 10/10 | 10.1s | 10.1s | 0 | 30s 扫描；`endAt` 后首次扫描完成 |
| B 仅惰性 | 5/10 | 5.1s | 5.1s | 0 | 第 6～10 份仍 `DRAFT`，证明不能单独使用 |
| C 定时 + 惰性 | 10/10 | 10.1s | 10.0s | 0 | 5 份惰性 ~5.1s，5 份定时 ~10.1s |
| 重启补偿 | 10/10 | 5.1s | 5.1s | 0 | `endAt` 已过 5s，首轮扫描补齐 |

> 实际时间用 `observed_at=NOW(3)` 记录触发时刻；`submitted_at` 按契约写 `end_at`，因此上表的延迟是「实际触发 - endAt」，不是 `submitted_at - endAt`。
> 脚本与原始日志（`Sp03.java`）保留在本机探针目录，未合入 docs PR。

## 4. 成功标准

- 方案 A 或 C 在 `endAt + 60s` 内完成 10/10 自动交卷，0 次重复迁移。
- 方案 B 明确暴露「无人访问则漏交」的漏洞（至少 5 份仍为 `DRAFT`）。
- 重启后首轮扫描能补齐所有到期 `DRAFT`。
- 结论能直接写入 ADR-002：采用哪种触发方式、扫描间隔、重启后的补偿规则。

## 5. 结论回填位置

| 内容 | 回填到 |
| --- | --- |
| 三种方案数据与结论 | 本文件「结论（先行）」+ `evidence/` |
| 触发方式、扫描间隔、补偿规则 | `adr/ADR-002-exam-submit-idempotency.md` 第 4、5 节 |
| 接口可见行为 | `docs/architecture.md` 6.3.8 |
| 探针状态 | `docs/spike/README.md` 第六节；`docs/spike/plan.md` SP-03 认领记录 |

## 6. 明确不做

- 不引入 Quartz、调度框架、消息队列、Redis。
- 不写答题页面、不接正式 Spring 业务层、不合并 `src/`。
- 不做多实例调度、分布式锁、压测平台。
- 不做 UI 原型或页面开发。

## 7. 风险与限制

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| JDK 调度器与 Spring `@Scheduled` 线程模型不完全相同 | 结论不能直接等同于 Spring 实测 | 记录限制；第 10 周用 Spring `@Scheduled` 复跑一次 |
| 30 秒间隔在演示中等待较久 | 实验时间长 | 时间盒 0.5 天；只跑 10 份、1 分钟窗口 |
| 惰性触发模拟的「学生请求」不真实 | 低估实际请求量 | 只用于证明「无人访问会漏交」，不作为生产方案 |
| 进程重启测试需要停止/启动进程 | 可能漏记录 | 先记录基线，再重启，再记录首轮扫描结果 |
| 零答卷试卷未被本轮实验覆盖 | 可能漏关 `CLOSED` | 6.3.8 改为 `findDuePapers(now)` 枚举到期试卷；第 10 周补「零答卷 → CLOSED」测试 |
