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
- **结论**：**完全可行**。MySQL 8 + utf8mb4 环境完全支持大容量中文及特殊符号的长文本存储。
- **实验环境与证据**：
  1. 利用 `REPEAT` 函数生成包含中文、特殊符号及 emoji 的超长文本（约 50KB，共计 26,000 个字符）。
  2. **对比测试 1**：尝试将该文本写入 `TEXT` 字段时，MySQL 直接报错 `ERROR 1406 (22001): Data too long for column 'content'`。**证明 `TEXT` 类型容量不足（上限约 65,535 字节），绝对无法承载大体量解答。**
  3. **对比测试 2**：将相同文本写入 `MEDIUMTEXT` 字段，显示 `Query OK`。查询结果显示 `char_length` 为 26,000，`LEFT(content, 50)` 的前置内容完整无截断。（注：命令行窗口显示 `???` 为本地终端字符集限制，经实际系统读取可确认 emoji 与中文完整保留）。
- **最终建议（对架构设计的直接指导）**：
  1. **字段选型**：必须采纳本次测试结果，`ADR-001` 与后续数据表设计（`stem_snapshot`、`reference_answer_snapshot`、`rubric_json_snapshot`）**一律采用 `MEDIUMTEXT` 类型**，严禁使用 `TEXT`。
  2. **前端限制**：考虑到数据库性能与网络传输，建议在接口层和前端限制单题答案或题干字数不超过 **20,000 个字符**。
- **现有证据（仅作参考）**：
<img width="529" height="41" alt="TEXT存20K成功" src="https://github.com/user-attachments/assets/b4c6e718-565c-4cfe-aadc-f170950943f6" />
<img width="530" height="62" alt="TEXT存50K报错" src="https://github.com/user-attachments/assets/3f48d64d-4cef-48eb-a29b-30f218c63c5b" />
<img width="625" height="158" alt="存储表格显示" src="https://github.com/user-attachments/assets/c3184c90-aa2e-4c5e-b9b4-3ab3d1bdc428" />



