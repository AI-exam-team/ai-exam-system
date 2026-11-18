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

- **结论**：**可行（推荐 MEDIUMTEXT）**。
- **实验步骤与证据说明**：
  1. **小容量测试**：将 `REPEAT` 参数设为 300，写入 `TEXT` 字段时提示 `Query OK, 1 row affected`，证明 `TEXT` 字段承载短文本正常。
  2. **容量边界测试**：将 `REPEAT` 参数设为 1000，尝试写入 `TEXT` 字段时，MySQL 直接报错 `ERROR 1406 (22001): Data too long for column 'content'`。这证明 `TEXT` 容量（约 65,535 字节）无法满足大体量答案存储需求。
  3. **大容量（MEDIUMTEXT）测试**：同样的 1000 次循环长文本，成功写入 `MEDIUMTEXT` 字段。查询结果显示 `CHAR_LENGTH` 为 `26000`，数据未发生截断。
  4. **字符完整性说明**：由于使用 MySQL CLI（CMD 终端）进行测试，终端编码不支持 emoji 显示，导致 `preview` 查出的表情变为 `???`。但 `CHAR_LENGTH` 统计与写入数据一致，表明数据库层面已完整存储；实际显示效果需第 9 周应用层（如网页前端）最终复验。
- **字段设计建议**：对于题干快照（`stem`）、参考答案快照（`referenceAnswer`）、评分点 JSON 快照（`rubric`），**必须采用 `MEDIUMTEXT` 类型**。
- **验证截图**：
<img width="529" height="41" alt="TEXT存20K成功" src="https://github.com/user-attachments/assets/b4c6e718-565c-4cfe-aadc-f170950943f6" />
<img width="530" height="62" alt="TEXT存50K报错" src="https://github.com/user-attachments/assets/3f48d64d-4cef-48eb-a29b-30f218c63c5b" />
<img width="625" height="158" alt="存储表格显示" src="https://github.com/user-attachments/assets/c3184c90-aa2e-4c5e-b9b4-3ab3d1bdc428" />



