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

- **结论**：**可行**。MySQL 8 + utf8mb4 完全支持大容量中文及 4 字节 emoji 的存储。
- **字符完整性（HEX 底层验证）**：
  1. 由于本地 Windows CMD 终端使用 GBK 编码，直接粘贴包含 emoji 的 SQL 会触发 `ERROR 1366 (Incorrect string value)`。这属于终端传输限制，并非 MySQL 数据库限制。
  2. 为绕过终端限制，实验采用 `CHAR(240, 159, 152, 138)` 在 MySQL 服务端直接生成 emoji（😊）并写入 `MEDIUMTEXT` 字段。
  3. 通过 `SELECT HEX(content)` 查证，结果显示尾部编码为 **`F09F988A`**（即 😊 的标准 UTF-8 十六进制）。**证明 MySQL 8 在 utf8mb4 下已完整、无损地存储了 4 字节的 emoji，解决了“终端显示为 ???”的疑虑。**
- **容量边界验证**：实测 `TEXT` 字段存 50KB 文本会触发 `ERROR 1406: Data too long`，正式确定快照字段选用 **`MEDIUMTEXT`**。
- **字段设计建议**：对于题干快照（`stem`）、参考答案快照（`referenceAnswer`）、评分点 JSON 快照（`rubric`），**必须采用 `MEDIUMTEXT` 类型**；建议前端限制输入上限为 20000 字符。
- **JSON 快照字段补测**：额外创建了 `test_json` 表验证 MySQL 8 原生 `JSON` 类型。成功插入包含中文和评分数据的 JSON 数组，并使用 `JSON_EXTRACT(rubric_json, '$[0].description')` 成功解析出 `"答出核心概念"`。**结论**：完全支持 `ADR-001` 中要求的 `rubric_json_snapshot` 结构存取需求。（注：因本地 CMD 终端编码限制，该测试中 emoji 被终端转码为 `?`，但在 `MEDIUMTEXT` 测试中已通过 `HEX()` 底层证据证明 MySQL 支持 4 字节 emoji 存储）。
- **验证截图**：
<img width="529" height="41" alt="TEXT存20K成功" src="https://github.com/user-attachments/assets/b4c6e718-565c-4cfe-aadc-f170950943f6" />
<img width="530" height="62" alt="TEXT存50K报错" src="https://github.com/user-attachments/assets/3f48d64d-4cef-48eb-a29b-30f218c63c5b" />
<img width="625" height="158" alt="存储表格显示" src="https://github.com/user-attachments/assets/c3184c90-aa2e-4c5e-b9b4-3ab3d1bdc428" />
<img width="653" height="95" alt="表情的HEX编码" src="https://github.com/user-attachments/assets/93c2d71d-45d2-4365-aeb8-250931ff98bf" />
<img width="902" height="241" alt="JSON" src="https://github.com/user-attachments/assets/31f19d6c-86f4-40b6-b177-cbfbe961fca0" />





