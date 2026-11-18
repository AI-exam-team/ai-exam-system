# SP-04 长文本答案与 utf8mb4 存储探针

## 1. 验证问题
> MySQL 8 + utf8mb4 下，单题 20KB / 50KB 中文答案、含 emoji 与换行的文本能否完整往返？字段类型选 `TEXT` 还是 `MEDIUMTEXT`？

## 2. 假设
- utf8mb4 下 20KB 中文答案可完整存取；50KB 需要 `MEDIUMTEXT` 或明确限制输入长度。
- 换行、引号、emoji、特殊符号不发生截断或乱码。

## 3. 实验步骤（本地验证，代码不传仓库）
1. 在本地数据库建最小表，分别用 `TEXT` 与 `MEDIUMTEXT`（或对应的大文本类型）存储长中文样本（含 emoji、换行、引号）。
2. 写入后读回，逐字节比较长度与内容摘要；记录报错或截断情况。
3. 在接口层建议输入上限（与前端字数限制保持一致）。

## 4. 结论
- **结论：有条件可行（待 MySQL 8 验证）**。
- **环境说明**：当前证据来自 **SQL Server**（`NVARCHAR(MAX)`），只能作为“长文本需要大文本类型”的初步参考；**不能直接回答本探针的 MySQL 8 + utf8mb4 问题**。
- **初步建议**：MySQL 侧优先使用 `MEDIUMTEXT`；`TEXT` 上限约 65,535 字节，20,000 个中文字符在 utf8mb4 下可能超出，必须在 MySQL 实测确认。
- **字符完整性（初步）**：SQL Server 下包含中文、特殊符号及 emoji（😊📚）的长文本写入并读取后无乱码、无截断；该结果不能外推到 MySQL。
- **待补实验（MySQL 8 + utf8mb4）**：
  1. 建 utf8mb4 表，分别用 `TEXT` / `MEDIUMTEXT` 存 20KB、50KB 中文样本（含 emoji、换行）；
  2. 记录写入结果、`CHAR_LENGTH()` / `LENGTH()`、读取一致性；
  3. 验证 `JSON` 快照列（`rubric_json_snapshot`）的字符保留；
  4. 复查通过后，再把状态改为“可行 / 不可行”。
- **建议输入上限**：20000 字符仅为提案，需进契约/需求评审确认，不由本探针单独定案。
- **现有证据（仅作参考）**：
<img width="1075" height="542" alt="屏幕截图 2026-11-17 181204" src="https://github.com/user-attachments/assets/ded0ee7f-3b47-4d97-8184-5c2bcd34b589" />
