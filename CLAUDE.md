# CLAUDE.md — AI 协作入口

**本文件只做入口，细则以 `agent-rules.md` 为准。** 请勿在本文件重复维护规则；规则变更只改 `agent-rules.md`。

## 项目一句话

面向高校课程的主观题考试系统：教师建题组卷并发布考试，学生在线作答，DeepSeek 完成主观题初评，教师复核定分。

## 每次会话必读（按顺序）

1. `context.md` — 业务、角色、实体、技术栈、范围边界
2. `agent-rules.md` — AI 开发契约（强制）
3. `spec/README.md` → `spec/spec-v0.1.md` → 相关模块 spec / ADR

## 本周红线（第 6 周）

- 禁止编写或提交任何正式业务代码；`src/`、`tests/` 只保留占位。
- 只允许在 `docs/spike/` 写验证性代码，且须遵守 `docs/spike/README.md`。
- 禁止修改他人模块；跨模块改动先改 spec/ADR。
- 禁止硬编码密钥、API Key、口令；不提交 `.env`。
- 不 push 远端、不直接提交 `main`。

## 关键 Non-Goals（不得扩展）

- 不做客观题与自动判分
- 不做管理员角色、自助注册、密码找回、支付、排名、监考
- 不做 AI 出题、错题讲解、自动定分
- 不做多租户、移动端、第二家模型接入

## 分支与 PR

- 一任务一分支，从 `main` 拉出：`feature/<module>-<issue>-<short-name>` 或 `docs/<issue>-<name>`。
- 提交信息：`type(scope): summary`。
- PR 必须关联 Issue、关联 spec、填写 AI 使用说明、测试证据、风险与回滚。
- 至少 1 名非作者模块 owner 评审；契约文件 PR 须集成负责人评审。

## 技术栈（不得擅自引入其他依赖）

Vue 3 · Java 21 / Spring Boot 4.1 · MySQL 8 · DeepSeek · JWT · Docker

## 遇到不确定

停止并在 Issue/PR 中列出待确认项，升级给集成负责人；不要自行补全业务规则。
