# SP-03：MySQL 8 自动交卷实验

| 项目 | 内容 |
| --- | --- |
| 编号 | SP-03 |
| 状态 | 实测已完成（MySQL 8.0.46；PowerShell 调度探针） |
| 主执行 | 李昕彤 |
| 复核 | 钱斓轩 |
| 日期 | 2026-11-18 |
| 关联 Issue | #32 |

## 结论

**有条件可行。** 本机 MySQL Community Server 8.0.46 实测中，A 定时扫描和 C 定时扫描加请求兜底都在 `endAt + 60s` 内完成 10/10 份答卷，重复条件更新影响 0 行。B 仅惰性触发且无人请求时，到 `endAt + 60s` 仍有 10/10 份答卷为 `DRAFT`。零答卷试卷随定时扫描关闭。扫描停摆后，在 `endAt + 30s` 执行首轮补扫，10/10 完成。手动交卷与自动交卷并发时只有一方更新成功。

本轮用 PowerShell `fixedDelay 30s` 探针驱动 MySQL 条件更新，没有运行 Spring Boot `@Scheduled`。补扫用例模拟调度器停扫后恢复首轮扫描，未重启 MySQL 服务。结论适用于本机、单实例和本轮 10 份答卷规模。

## MySQL 8 部署

MySQL Community Server 8.0.46 Windows x64 ZIP 部署在 `D:\SQL2022\mysql8\mysql-8.0.46-winx64`，数据目录为 `D:\SQL2022\mysql8\data`，监听 `127.0.0.1:3306`，实验库为 `spike`（`utf8mb4` / InnoDB）。下载包来自 [MySQL 官方下载页](https://dev.mysql.com/downloads/mysql/8.0.html)，安装按[官方 Windows ZIP 说明](https://dev.mysql.com/doc/refman/8.0/en/windows-install-archive.html)进行，下载文件 MD5 与官方值一致。

本机版本查询结果：

```sql
SELECT VERSION();
-- 8.0.46
```

用 PowerShell 脚本启动或停止当前用户的 MySQL 进程：

```powershell
.\start-mysql.ps1
.\stop-mysql.ps1
```

本机未将其注册为 Windows 服务。部署环境和硬件信息见 `evidence/environment.md`。

## 实验数据与结果

表结构见 `evidence/schema.sql`；探针见 `evidence/probe.ps1`。每个定时扫描间隔为 30 秒，主试卷含 10 份 DRAFT；B 轮在观察截止前不发起学生请求。

| 轮次 | 方案 | DRAFT 总数 | `endAt+60s` 完成数 | 重复迁移数 | 零答卷试卷关闭 | 补扫结果 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 1 | A：仅定时扫描 | 10 | 10 | 0 | 已关闭 | — |
| 2 | B：仅惰性触发，无请求 | 10 | 0 | 0 | 未关闭 | — |
| 3 | C：定时扫描 + 请求兜底 | 10 | 10 | 0 | 已关闭 | — |
| 4 | 调度停扫后补扫模拟 | 10 | 10 | 0 | — | `endAt+31.0s` 首轮扫描完成 |

- A 轮在 `endAt+26.2s` 扫描完成 10 份；自动交卷 `submitted_at=endAt`，已提交控制答卷没有被条件更新改写。
- B 轮在 `endAt+60s` 检查时，10 份仍为 DRAFT，零答卷试卷仍为 PUBLISHED。
- C 轮先由请求兜底提交 1 份，定时扫描再提交 9 份；扫描在 `endAt+16.1s` 完成。
- 补扫模拟在 `endAt+31.0s` 执行首轮扫描，完成 10/10。
- 并发更新实测手动影响 1 行、自动影响 0 行，总计 1 次状态迁移。重复条件更新在 A、C、补扫轮次各影响 0 行。

原始轮次数据、扫描日志、并发结果和复核查询分别见 `evidence/rounds.csv`、`evidence/scan.log`、`evidence/concurrency.txt`、`evidence/verification.txt`。

## ADR 回填

实测建议：保留 30 秒定时扫描，学生请求只作为兜底；在本轮单实例和 10 份答卷规模下，A/C 均达到 `endAt+60s` 10/10，重复迁移为 0。当前仓库没有 `adr/ADR-002-exam-submit-idempotency.md`，本轮未新建 ADR 或代替负责人做架构决策。

## 变更记录

| 日期 | 变更 | 原因 |
| --- | --- | --- |
| 2026-11-18 | 部署 MySQL 8.0.46，执行 A/B/C、补扫模拟和交卷并发实验，记录实测结果 | 为自动交卷触发方式提供 MySQL 8 证据 |
