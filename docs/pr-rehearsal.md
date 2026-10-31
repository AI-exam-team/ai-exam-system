# 空 PR 协作演练

> 目的：在没有任何业务代码的情况下，完整走通「分支 → 提交 → PR → 评审 → 合并」协作链路，验证模板、看板与 CODEOWNERS 是否可用。
> **当前远端未连接**：本周只允许在本地创建分支和草稿，**不执行 `git push`，不创建远端仓库**。下文带“接远端后”的步骤暂不执行。

## 一、演练前置条件

- 仓库：`D:/AI智能考试系统`（独立仓库，分支 `main`，本地尚无远端）。
- `Issue-104 执行空 PR 协作演练` 已登记，看板卡片已从 `This Week` 移到 `In Progress`。
- 评审人已约定（1 名非作者），测试环境无需启动。
- 工作区干净：`git status` 无未提交改动。

## 二、本地操作步骤（本周执行范围）

### 1. 确认基准并建分支

```bash
cd "D:/AI智能考试系统"
git status
git switch main
git switch -c feature/issue-104-empty-pr
```

> 分支名固定为 `feature/issue-104-empty-pr`，与 Issue 规划编号对应；接远端后即使 GitHub 实际编号不同，也不改分支名。

### 2. 只改 README.md 一行

在 `README.md` 末尾追加一行演练标记：

```markdown
第 6 周空 PR 演练：仅文档变更，无业务代码。
```

要求：

- 只允许改这一行，不得顺带格式化、改标题、动其他文件。
- `git diff` 必须恰好是 1 行新增。

### 3. 本地提交

```bash
git add README.md
git diff --cached
git commit -m "docs(repo): 演练空 PR 流程（Issue-104）"
```

- 提交信息遵循 `type(scope): summary`，`type` 用 `docs`，`scope` 用 `repo`。
- 不添加 `Co-authored-by` 之外的无关信息。

### 4. 自检后进入 Review

- 看板卡片从 `In Progress` 移到 `Review`。
- 本地检查：
  ```bash
  git log --oneline -1
  git diff main...HEAD --stat
  ```
- **本周到此为止**，不 push。

## 三、接远端后的操作步骤（暂不执行）

### 5. 添加远端并推送

```bash
git remote add origin <仓库地址>
git push -u origin feature/issue-104-empty-pr
```

### 6. 创建 PR

用 `gh` 或网页创建，默认分支 `main`，标题：`docs(repo): 演练空 PR 流程（Issue-104）`。

PR 描述必须完整填写 `.github/pull_request_template.md`，示例见第四节；首行写 `Closes #<GitHub 实际编号>`。

### 7. 绑定 Issue 与看板

- PR 描述关联 Issue，GitHub 会自动在 Issue 时间线留下引用。
- 确认看板自动化把卡片置为 `Review`；未自动则手动移动。
- 指定至少 1 名非作者评审人；涉及 `.github/` 或 `README.md` 时 CODEOWNERS 会请求集成负责人。

### 8. 同行评审

评审人检查：

- [ ] 变更范围与 Issue 一致，只有 README 一行。
- [ ] 提交信息、分支名符合约定。
- [ ] PR 模板各栏填写完整，无敏感信息。
- [ ] 测试证据写明“无业务代码，仅文档”。
- [ ] 风险与回滚方案可执行。

评审通过后由评审人（或作者按团队约定）执行 **Squash merge**，删除远端分支。

### 9. 合并后验收

- 看板卡片自动移入 `Done`；未自动则手动移动。
- Issue 因 `Closes #N` 自动关闭；若未关闭，手动核对验收标准后关闭。
- 本地同步并删除分支：
  ```bash
  git switch main
  git pull
  git branch -d feature/issue-104-empty-pr
  ```
- 截图或链接留档到演练记录（可选，不新增业务文件）。

## 四、完整 PR 描述示例

以下内容可直接粘贴到 PR 描述框（把 `#12` 换成实际编号）：

```markdown
## 关联 Issue

Closes #12

## 关联 Spec

- spec：无（本次为协作流程演练，不涉及需求与规格）

## 变更摘要

- 在 README.md 末尾新增一行演练标记，用于验证 PR 模板、评审与合并流程。
- 不修改任何业务代码、配置、模板或目录结构。

## AI 工具使用说明

- 使用的 AI 工具：Claude Code
- 用途：根据 `docs/pr-rehearsal.md` 生成 PR 描述草稿与自检清单
- 人工修改与复核：作者逐条核对模板字段，确认无敏感信息；评审人复核变更范围
- 是否涉及生成代码/文档的敏感信息：否

## 测试证据

- [ ] 单元测试：不适用（无业务代码，仅文档）
- [ ] 集成测试：不适用（无业务代码，仅文档）
- [ ] 手动验证：`git diff main...HEAD --stat` 确认仅 README.md 1 行变更
- [ ] 证据链接/截图：本地 diff 输出（见 PR 评论）

## 评审清单

- [ ] 变更范围与关联 Issue 一致，未夹带无关修改
- [ ] 符合 `context.md` 锁定的角色、题型、模块与范围边界
- [ ] 未引入 Non-Goals 中的能力
- [ ] 相关 `spec/` 已同步更新（本次不适用）
- [ ] 架构取舍已记录到 `adr/`（本次不适用）
- [ ] 无密钥、Token、个人隐私等敏感信息
- [ ] 命名与提交信息符合 `agent-rules.md` 约定
- [ ] 已指定至少 1 名非作者评审人

## 风险与回滚方案

- 风险：极低。仅新增一行 HTML 注释，不影响文档渲染与构建。
- 影响面：README.md 渲染；无运行时影响。
- 回滚方案：在 `main` 上执行 `git revert <merge-commit>`，或删除该行后另提修复 PR；演练分支可直接删除。
```

## 五、演练完成标准

- [x] 本地分支 `feature/issue-104-empty-pr` 存在且仅 1 行变更（本周目标）。
- [ ] 接远端后 PR 创建成功并绑定 Issue。
- [ ] 至少 1 名非作者评审通过。
- [ ] 合并后看板卡片进入 Done、Issue 自动关闭。
- [ ] 无业务代码、无敏感信息进入仓库。

> 本周结论：完成本地分支与文档演练，**未推送远端**。远端接入后按第三、四节补做并记录结果。
