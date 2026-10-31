# 第 6 周集成与验收报告

| 项目 | 内容 |
| --- | --- |
| 验收日期 | 2026-10-31 |
| 验收人 | 集成与契约负责人（integrator） |
| 仓库 | `D:/AI智能考试系统`（本地独立仓库） |
| 当前分支 | `main` |
| 远端 | 已接入 `AI-exam-team/ai-exam-system`；`main` 与四条分支已推送 |
| 业务代码 | 无（`src/`、`tests/` 仅 `.gitkeep`） |

---

## 一、交付物清单

| 交付物 | 路径 | 状态 |
| --- | --- | --- |
| 项目上下文 | `context.md` | 已合入 `main` |
| 小组项目基本信息表（已填写） | `docs/小组项目基本信息_已填写.docx` | 已合入 `main` |
| 原始资料归档 | `docs/reference/`（SRS v1.3、基本信息模板、第 6 周 PPT + README） | 已合入 `main`，MD5 与原件一致 |
| AI 协作规则 | `agent-rules.md` | 已合入 `main` |
| AI 协作入口 | `CLAUDE.md` | 已合入 `main` |
| 规格骨架与规范 | `spec/README.md`、`spec/spec-v0.1.md` | 已合入 `main`（状态：草稿，待冻结） |
| ADR 模板 | `adr/0000-template.md` | 已合入 `main` |
| 看板方案 | `plans/github-projects.md` | 已合入 `main` |
| Issue 清单 | `plans/week6-issues.md` | 已合入 `main` |
| 模块分工与合并规则 | `plans/module-ownership.md` | 已合入 `main` |
| 空 PR 演练文档 | `docs/pr-rehearsal.md` | 已合入 `main` |
| 技术探针规范 | `docs/spike/README.md` | 已合入 `main` |
| 仓库骨架与模板 | `README.md`、`.gitignore`、`.github/`、各目录 `.gitkeep` | 初始提交 |
| 空 PR 演练分支 | `feature/issue-104-empty-pr` | **保留未合并**，模拟等待评审 |
| 本验收报告 | `docs/week6-acceptance.md` | 本文件 |

原始资料 MD5 复核（与 `D:/Vibe coding/AI智能考试系统` 下原件一致）：

- `06 AI原生项目管理与上下文构建.pptx` → `1bda1b51c07e66138932a5696d02a55a`
- `AI智能考试系统_SRS_v1.3_架构导读优化稿.docx` → `2e77d50fff3a7243c8a25e5b1c05d9d6`
- `小组项目基本信息.docx` → `3e4ebd0976b7889920312ac10767c217`

---

## 二、一致性校验结果

| # | 校验项 | 结果 | 说明 |
| --- | --- | --- | --- |
| 1 | 角色口径 | ✅ 通过 | `context.md`、`README.md`、`agent-rules.md`、`CLAUDE.md`、`spec/*`、`plans/*`、`docs/*`、基本信息表均为 **2 个业务角色（学生、教师）**；无“管理员是业务角色”表述。 |
| 2 | 管理员冲突表述 | ✅ 通过 | “三角色/管理员”仅出现在两处允许场景：① Non-Goals 的“不做管理员角色”；② 与旧 SRS v1.3 的差异说明（`context.md` §2.5/§8、`spec/spec-v0.1.md` §6），并明确“已收敛、并入教师”。 |
| 3 | 客观题关键字 | ✅ 通过 | “单选/多选/判断/客观题”仅出现在 Non-Goals、“本期不做”、SRS 差异说明中；MVP 范围内无客观题。“判断依据/单选项”等为普通词义，非题型。 |
| 4 | Non-Goals 数量与可判定性 | ✅ 通过 | 统一 4 条：① 客观题与自动判分；② 管理员角色与账号自助/考务外围；③ AI 出题/错题讲解/自动定分；④ 多租户/移动端/第二家模型。每条均可用“是否出现对应功能”直接判定。 |
| 5 | `src/`、`tests/` 占位 | ✅ 通过 | 仅有 `.gitkeep`，无源码、无测试实现。 |
| 6 | 密钥 / 内网地址 / 隐私 | ✅ 通过 | 未发现 `sk-`、硬编码 password/secret、内网 IP、localhost 端口；未发现学号、手机号等个人敏感信息；成员姓名仅用于分工建议。 |
| 7 | 文档内业务代码 | ✅ 通过 | 文档仅含 Markdown、目录说明、git 命令示例与模板占位，无业务实现代码。 |
| 8 | 分支命名与提交格式 | ✅ 通过（已修正） | 见第三节“本次修正”。 |

### 本次修正（仅改 `D:/AI智能考试系统`，未触碰 `D:/Vibe coding` 原件）

| 文件 | 修正内容 | 原因 |
| --- | --- | --- |
| `README.md` | 贡献方式中的分支示例由 `feat/<模块>-<简述>` 等改为 `feature/<module>-<issue>-<short-name>` / `docs/<issue>-<name>` | 与 `agent-rules.md` AR-3.2 统一，消除 `feat/` 别名歧义 |
| `agent-rules.md` | AR-3.2 增补：“`feature/issue-104-empty-pr` 为唯一例外” | 与课程指定的空 PR 分支名一致 |
| `plans/module-ownership.md` | spec 路径 `spec/0X-*.md`、`spec/00-overview.md` 改为 `spec/<module>-spec-*.md`、`spec/spec-v*.md` | 与 `spec/README.md` 的命名规范一致 |
| `plans/week6-issues.md` | 同步 spec 路径；增加“本地提交口径”说明（规划编号与实际分支映射） | 消除 Issue 规划编号与本地历史分支号的歧义 |
| `docs/pr-rehearsal.md` | 演练行改为“第 6 周空 PR 演练：仅文档变更，无业务代码。”；提交/PR 标题改为 `docs(repo): …` | 与验收脚本及提交格式 `type(scope): summary` 对齐 |

> 未删除任何既有文档；未修改角色、题型、模块、Non-Goals 等锁定决策。

---

## 三、本地 Git 历史

提交顺序（全部为本地提交，**未 push**）：

1. `main`：`chore(repo): 初始化仓库骨架`
2. `docs/issue-101-context` → `--no-ff` 合入 `main`
3. `docs/issue-102-rules` → `--no-ff` 合入 `main`
4. `docs/issue-103-plans` → `--no-ff` 合入 `main`
5. `feature/issue-104-empty-pr`：仅 README 追加 1 行，**保留未合并**

`git log --oneline --graph --all` 摘要：

```text
* <报告提交> docs(repo): 编写第 6 周集成与验收报告
* 4d6768f docs(repo): 调整演练标记为单行变更（Issue-104）
* 842308a docs(repo): 演练空 PR 流程（Issue-104）
*   cf8cf62 docs(plans): 合入看板与协作方案（Issue-103）
|\
| * f9a2e03 docs(plans): 编制看板方案、Issue 清单、分工与演练文档
|/
*   3dcbea6 docs(rules): 合入 AI 规则与规格骨架（Issue-102）
|\
| * 2f7fe0b docs(rules): 制定 AI 协作规则、spec 骨架与 ADR 模板
|/
*   ea6a3f2 docs(context): 合入上下文与基本信息表（Issue-101）
|\
| * adb1037 docs(context): 编写项目上下文与基本信息表
|/
* 5e737e4 chore(repo): 初始化仓库骨架
```

### 分支列表

| 分支 | HEAD | 状态 |
| --- | --- | --- |
| `main` | 以 `git log -1 main` 为准 | 主分支，已含三次 `--no-ff` 合并及本报告提交 |
| `docs/issue-101-context` | `adb1037` | 已合并，保留 |
| `docs/issue-102-rules` | `2f7fe0b` | 已合并，保留 |
| `docs/issue-103-plans` | `f9a2e03` | 已合并，保留 |
| `feature/issue-104-empty-pr` | `4d6768f` | **未合并**，模拟等待评审（净变更 1 行） |

### 规划编号与实际分支映射

| 本地分支（实际） | 提交内容 | 对应规划 Issue |
| --- | --- | --- |
| 初始提交（`main`） | 仓库骨架、README、`.gitignore`、`.github/`、目录占位 | Issue-101（骨架部分） |
| `docs/issue-101-context` | `context.md`、基本信息表、`docs/reference/` | Issue-102、Issue-103 |
| `docs/issue-102-rules` | `agent-rules.md`、`CLAUDE.md`、`spec/`、`adr/` | Issue-105、Issue-106、Issue-109 |
| `docs/issue-103-plans` | `plans/`、`docs/spike/`、`docs/pr-rehearsal.md` | Issue-107、Issue-108、Issue-110 |
| `feature/issue-104-empty-pr` | README 空 PR 演练行 | Issue-104 |

> 分支号按第 6 周集成验收脚本执行；接入 GitHub 后以实际 Issue 编号重新映射，不因编号变化改分支名（仅空 PR 分支为固定命名）。

---

## 四、仍未完成事项

1. **远端未接入**：未创建 GitHub 仓库、未添加 `origin`、未 push 任何分支。
2. **Projects 看板未实建**：`plans/github-projects.md` 仅为方案，5 列、字段、标签、自动化均待远端创建。
3. **真实 PR 未创建**：Issue-104 仅完成本地分支与文档；PR、评审、合并、看板流转待远端接入后补做。
4. **Issue 编号未落地**：`Issue-101`～`110` 为规划编号，需在 GitHub 创建后补实际编号映射。
5. **spec 未冻结**：`spec/spec-v0.1.md` 仍为草稿；FR 编号与模块 spec 待评审后分配。
6. **分工待小组确认**：`plans/module-ownership.md` 的人员映射、前端归属、集成负责人兼任仍需周会确认。
7. **CODEOWNERS 为占位**：`@TODO-replace-*` 未替换，规则尚未生效。
8. **无 CI**：本周无流水线，评审依赖人工核对。

---

## 五、下周建议

1. **接入远端并固化流程**：创建 GitHub 私有仓库，push `main` 与四条分支；启用分支保护（PR + 1 名非作者评审 + CODEOWNERS），替换 CODEOWNERS 占位符。
2. **实建看板与 Issue**：按 `plans/week6-issues.md` 批量创建 Issue、标签与 Project，补实际编号映射；用 Issue-104 走通一次真实 PR 全流程。
3. **冻结 spec v0.1**：集成负责人完成评审，关闭或指派 8 个 TBD，随后分配 FR 编号并拆分 `qbank/exam/grading` 模块 spec。
4. **确认分工与评审归属**：周会敲定 6 人映射、前端归属与集成负责人兼任；更新 `plans/module-ownership.md` 的“待确认”勾选项。
5. **启动技术探针**：优先验证 DeepSeek OpenAI 兼容接口的鉴权、超时、重试与评分点结构化输出，结论回写 `adr/`，探针代码不得进入 `src/`。
6. **守住范围红线**：第 7 周业务代码解禁后，第一个 PR 前再次对照 `context.md` 的 2 角色、3 模块、2 题型与 4 条 Non-Goals；客观题、管理员角色、自动定分一律拒收。

---

## 六、验收结论

第 6 周文档类交付物齐全，锁定决策在全仓库一致；本地 Git 历史符合“骨架 → 三次文档分支 `--no-ff` 合并 → 空 PR 分支保留”的要求；`main` 工作区干净，`src/`、`tests/` 无业务代码，未连接远端、未 push。**第 6 周集成验收通过。**

遗留项（看板实建、PR 评审、spec 冻结、分工确认）已列入第四节，转入第 7 周执行。

---

## 七、远端落地记录（2026-10-31 补记）

| 项目 | 结果 |
| --- | --- |
| 远端仓库 | <https://github.com/AI-exam-team/ai-exam-system> |
| 推送分支 | `main`、`docs/issue-101-context`、`docs/issue-102-rules`、`docs/issue-103-plans`、`feature/issue-104-empty-pr` |
| 空 PR | PR #1：`feature/issue-104-empty-pr` → `main`，已绑定 Issue #5，待非作者评审 |
| Issues | #2～#11，对应规划 Issue-101～110；已完成项已关闭，Issue #5（空 PR）与 Issue #8（看板）保持 open |
| 标签 | 已创建 spec / feature / test / docs / infra / qbank / exam / grading（bug 为仓库默认标签） |
| Projects 看板 | **未创建**：当前 token 仅含 `gist, repo, workflow`，缺少 `project` 权限；需组长在网页端创建，或提供带 project 权限的 token |
| 评审要求 | PR 合并前需至少 1 名非作者评审；合并后 Issue #5 关闭 |
