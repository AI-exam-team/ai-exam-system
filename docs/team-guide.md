# 团队协作指南：仓库架构与 GitHub 流程

> 面向六人小组与所有 AI 工具。目标：让每个人知道“文件放哪、任务怎么流转、PR 怎么合并”，避免版本分裂和口头安排。
>
> 仓库：<https://github.com/AI-exam-team/ai-exam-system>  
> 看板：<https://github.com/orgs/AI-exam-team/projects/2>  
> 当前阶段：第 6 周「上下文搭建」，禁止正式业务代码。

---

## 一、仓库是什么

仓库不是只放代码，它是项目的**唯一真相源**：

| 信息 | 位置 |
| --- | --- |
| 项目边界、Non-Goals、技术约束 | `context.md` |
| AI 行为规则 | `agent-rules.md` |
| 功能需求、接口契约、验收标准 | `spec/` |
| 架构取舍与理由 | `adr/` |
| 任务拆解、看板规则、分工 | `plans/` |
| 正式业务代码 | `src/` |
| 测试 | `tests/` |
| 技术探针 | `docs/spike/` |
| 原始资料 | `docs/reference/` |

原则：**所有人和 AI 都按这个结构找信息，不随意新建文件夹。**

---

## 二、当前目录结构

```text
AI智能考试系统/
├── README.md                  # 新人入口：项目简介、目录导航
├── context.md                 # 项目“法律”：目标、2角色、3模块、Non-Goals、技术栈
├── agent-rules.md             # AI 协作契约：能做什么、不能做什么
├── CLAUDE.md                  # Claude Code 入口，只指向 agent-rules.md
│
├── spec/                      # 需求规格
│   ├── README.md              # spec 编写、评审、冻结规则
│   └── spec-v0.1.md           # 当前规格骨架
│
├── adr/                       # 架构决策记录
│   └── 0000-template.md
│
├── plans/                     # 计划与协作
│   ├── github-projects.md     # 看板规则
│   ├── week6-issues.md        # 本周 Issue 清单
│   └── module-ownership.md    # 六人三组分工（待周会确认）
│
├── src/                       # 当前只有 .gitkeep，第 6 周禁止业务代码
├── tests/                     # 当前只有 .gitkeep
│
├── docs/
│   ├── reference/             # 原始 SRS、PPT、基本信息模板
│   ├── spike/                 # 技术探针，禁止合入 src/
│   ├── pr-rehearsal.md        # 空 PR 演练说明
│   ├── team-guide.md          # 本文件
│   └── week6-acceptance.md    # 第 6 周验收报告
│
└── .github/
    ├── CODEOWNERS             # 目录负责人（用户名待替换）
    ├── pull_request_template.md
    └── ISSUE_TEMPLATE/
        ├── task.md
        └── bug.md
```

### 后续代码结构（第 7 周以后）

```text
src/
├── frontend/                  # Vue 3
└── backend/                   # Spring Boot
    └── modules/
        ├── qbank/             # 题库与组卷
        ├── exam/              # 在线考试与答卷
        └── grading/           # AI 阅卷与教师复核
```

三个模块对应三个组，目录不混。

---

## 三、每个目录放什么、不放什么

| 目录/文件 | 放什么 | 不放什么 |
| --- | --- | --- |
| `context.md` | 项目目标、角色、MVP、Non-Goals、技术约束 | 详细功能设计、代码 |
| `spec/` | 功能需求、接口契约、验收标准 | 会议记录、临时想法 |
| `adr/` | 架构取舍、备选方案、后果 | 教程、代码片段 |
| `plans/` | 看板规则、Issue 清单、分工 | 代码、需求正文 |
| `src/` | 正式业务代码 | 技术探针、草稿 |
| `tests/` | 单元测试、集成测试 | 手动测试截图 |
| `docs/spike/` | 技术探针、接口草稿 | 正式业务代码 |
| `docs/reference/` | 原始资料副本 | 修改后的版本 |
| `.github/` | PR/Issue 模板、CODEOWNERS | 业务逻辑 |

---

## 四、新人阅读顺序

```text
README.md
  → context.md
  → agent-rules.md
  → plans/module-ownership.md
  → spec/spec-v0.1.md
  → 自己模块的目录
```

---

## 五、目录所有权

| 目录 | 负责人 |
| --- | --- |
| `src/modules/qbank/` | 题库与组卷组 |
| `src/modules/exam/` | 在线考试与答卷组 |
| `src/modules/grading/` | AI 阅卷与复核组 |
| `context.md`、`spec/`、`agent-rules.md` | 集成与契约负责人 |
| `.github/CODEOWNERS` | 集成负责人 |

> 具体人员映射见 `plans/module-ownership.md`，最终以周会确认为准。

**可以读别人的目录，但不要直接改**；跨模块改动先在 Issue/PR 里说明。

---

## 六、三条铁律

1. **先上下文，后代码**：没有 `context.md`，不启动开发。
2. **先契约，后生成**：先写清 `spec/` 与接口，再让 AI 写代码。
3. **评审不过，先改 spec**：不要用临时补丁绕过契约。

---

## 七、GitHub 协作总流程

```text
① 建 Issue
      │
      ▼
② 看板排期：Backlog → This Week
      │
      ▼
③ 从 main 拉任务分支
      │
      ▼
④ 本地开发/写文档
      │
      ▼
⑤ 提交并 push
      │
      ▼
⑥ 开 PR（base=main，head=任务分支）
      │
      ▼
⑦ 非作者评审
      │
   ┌──┴──┐
   ▼     ▼
打回    Approve
   │      │
   └──▶ ⑧ 合并到 main
           │
           ▼
      ⑨ Issue 关闭
           │
           ▼
      ⑩ 看板 Done
```

### 六人泳道图

```text
任务负责人            评审人              集成负责人           看板
   │                    │                    │                 │
建 Issue ──────────────────────────────────────────────────▶ Backlog
   │                    │                    │                 │
周会排期 ──────────────────────────────────────────────────▶ This Week
   │                    │                    │                 │
拉分支 ────────────────────────────────────────────────────▶ In Progress
   │                    │                    │                 │
写代码/文档            │                    │                 │
   │                    │                    │                 │
提交 + push            │                    │                 │
   │                    │                    │                 │
开 PR ───────────────▶ 评审                  │                 │
   │                    │                    │                 │
   │                 Approve                 │                 │
   │                    │                    │                 │
   │                    └──────▶ 合并 ──────▶ main              │
   │                                         │                 │
   │                                         ▼                 │
   │                                    Issue 关闭 ──────────▶ Done
```

---

## 八、Issue 规范

- 标题：**动词 + 对象**，例如「实现主观题评分点录入」。
- 内容：业务背景 + 验收标准 + 关联 spec + 负责人。
- 标签：`spec` / `feature` / `test` / `bug` + `qbank` / `exam` / `grading`。
- 一个 Issue 只对应一个可验收成果。
- Issue 先建，再进看板；禁止“先干活后补 Issue”。

---

## 九、分支规范

```text
feature/qbank-12-add-rubric
feature/exam-18-autosave
feature/grading-23-ai-review
docs/30-update-spec
fix/35-score-rounding
```

规则：

- 一任务一分支。
- 从最新 `main` 拉出。
- 不直接提交 `main`。
- 合并后删除任务分支。
- 不强制推送共享分支。

创建分支：

```bash
git switch main
git pull
git switch -c feature/qbank-12-add-rubric
```

---

## 十、提交信息规范

格式：

```text
type(scope): summary
```

示例：

```text
feat(qbank): 新增评分点录入接口
fix(grading): 处理 AI 超时转人工
docs(spec): 补充发布时间规则
test(exam): 增加自动保存用例
chore(repo): 更新 PR 模板
```

要求：

- 一次提交只做一件事。
- 不提交 `.env`、token、密码、`target/`、`node_modules/`。
- 不提交与任务无关的格式化改动。

---

## 十一、PR 规范

- `base`：`main`
- `head`：任务分支
- 标题：与提交信息同风格
- 描述必须包含：
  - `Closes #Issue编号`
  - 变更摘要
  - 关联 spec
  - AI 工具使用说明
  - 测试证据
  - 风险与回滚
- 至少 1 名**非作者** Approve。
- 契约文件（`context.md`、`spec/`、`agent-rules.md`）还需要集成负责人评审。
- 作者不能批准自己的 PR。

---

## 十二、评审人检查清单

- [ ] 改动是否只在本模块目录
- [ ] 是否违反 `context.md` 的 Non-Goals
- [ ] 是否擅自修改契约文件
- [ ] 是否包含密钥、硬编码、隐私
- [ ] 是否有测试或可验证证据
- [ ] AI 生成内容是否经过人工核对
- [ ] PR 是否绑定 Issue

评审结果：

- **Approve**：同意合并
- **Request changes**：要求修改，作者在同一分支继续提交
- **Comment**：只评论，不表态

---

## 十三、合并规则

- 默认 **Squash and merge**：一个任务一个提交，`main` 干净。
- 需要保留分支拓扑时用 **Merge commit**。
- 合并后：PR 关闭 → Issue 自动关闭 → 看板卡片移到 `Done`。
- 合并前确认：评审通过、无冲突、无敏感信息、范围未越界。

---

## 十四、看板规则

| 列 | 进入条件 |
| --- | --- |
| Backlog | Issue 建好，还没排期 |
| This Week | 周会确认本周做 |
| In Progress | 已从 `main` 拉任务分支 |
| Review | PR 已创建并绑定 Issue |
| Done | PR 已合并、验收通过 |

规则：

- 一张卡同一时间只能在一列。
- 没合并的“本地做完了”不算 Done。
- 阻塞时留在原列加评论，不偷偷退回 Backlog。
- 看板是进度唯一依据；群里说“做完了”不算。

---

## 十五、新成员第一次协作

```bash
git clone https://github.com/AI-exam-team/ai-exam-system.git
cd ai-exam-system
git switch main
git pull

git switch -c feature/qbank-12-add-rubric

# 先读 README.md、context.md、agent-rules.md
# 再改自己模块

git add .
git commit -m "feat(qbank): 新增评分点录入接口"
git push -u origin HEAD
```

然后到 GitHub 开 PR，绑定 Issue，找一名非作者评审。

---

## 十六、常见错误

- 直接 push `main`
- 一条分支做多个 Issue
- PR 不绑定 Issue
- 改别人模块不打招呼
- 提交 `.env`、token、密码
- 本周写正式业务代码
- 忘了更新看板
- 自己批准自己的 PR
- 对共享分支 `force push`
- 把压缩包发到群里代替 Git 协作

---

## 十七、本周（第 6 周）红线与待办

**红线：**

- 不写正式业务代码，只允许 `docs/spike/` 技术探针。
- 空 PR #1 只改 `README.md` 一行。
- 不直接 push `main`。

**待办：**

- 组员接受组织邀请，clone 仓库。
- 阅读 `context.md` 与 `agent-rules.md`。
- 一名非作者评审 PR #1：<https://github.com/AI-exam-team/ai-exam-system/pull/1>
- 周会确认六人三组分工与 `CODEOWNERS` 用户名。
- 继续完善看板字段、Workflows 与成员访问权限。

---

## 十八、相关链接

| 内容 | 链接/路径 |
| --- | --- |
| 仓库 | <https://github.com/AI-exam-team/ai-exam-system> |
| 看板 | <https://github.com/orgs/AI-exam-team/projects/2> |
| 空 PR | <https://github.com/AI-exam-team/ai-exam-system/pull/1> |
| 项目边界 | [`context.md`](../context.md) |
| AI 规则 | [`agent-rules.md`](../agent-rules.md) |
| 看板方案 | [`plans/github-projects.md`](../plans/github-projects.md) |
| 本周 Issue | [`plans/week6-issues.md`](../plans/week6-issues.md) |
| 模块分工 | [`plans/module-ownership.md`](../plans/module-ownership.md) |
| 第 6 周验收 | [`docs/week6-acceptance.md`](./week6-acceptance.md) |

---

## 变更记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| v0.1 | 2026-10-31 | 建立团队协作指南：仓库架构、目录职责、分支/PR/评审/看板流程、新人清单 |
