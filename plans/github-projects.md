# GitHub Projects 看板方案

> 状态：仓库已于 2026-10-31 接入 GitHub；看板已创建：<https://github.com/orgs/AI-exam-team/projects/2>，5 个状态列已配置。其余字段、自动化、仓库关联与成员权限按第六节继续确认。
> 看板是**进度唯一依据**；口头同步、聊天记录、文档里的“已完成”都不算数，以看板卡片状态为准。

## 一、看板列（Status）

| 列 | 含义 | 进入条件 | 退出条件 |
| --- | --- | --- | --- |
| Backlog | 已建 Issue、尚未排期 | Issue 创建完成并通过模板自检 | 被排入本周 |
| This Week | 本周承诺完成 | 周会确认排期、有负责人 | 开始动手 |
| In Progress | 正在实现/编写 | 已从 `main` 拉出任务分支 | 自检完成、准备提 PR |
| Review | 等待评审 | 分支已提交、PR 已创建并绑定 Issue | PR 合并或打回 |
| Done | 已合并/验收通过 | PR 合并、验收标准全部勾选 | — |

规则：

- 一张卡片同一时间只能处于一列，禁止“一张卡拆成多条进度评论”代替状态流转。
- `Done` 只由 PR 合并（或明确验收结论）触发；未合并的“本地做完了”不算 Done。
- 阻塞时保留在原列并加 `blocked` 标记/评论，不回退到 Backlog，避免进度失真。

## 二、自定义字段

| 字段 | 类型 | 取值 | 说明 |
| --- | --- | --- | --- |
| Status | 内置单选项 | Backlog / This Week / In Progress / Review / Done | 看板列，见上表 |
| Module | 单选项 | `qbank` / `exam` / `grading` / `docs` / `infra` | 与目录、CODEOWNERS 路由一致 |
| Owner | 文本 | 1 名主负责人（真名或角色名） | 与 Issue 的 Assignee 保持同一人 |
| Issue | 文本 | `Issue-101` 等规划编号 | 兼作与 Issue 的交叉引用；GitHub 原生关联仍以实际 `#编号` 为准 |
| Priority | 单选项 | `P0` / `P1` / `P2` | P0 阻塞本周交付；P1 本周应完成；P2 有余力再做 |

可选补充：`Start date` / `Target date`（本周排期用），不要引入工时估算字段，避免把看板做成甘特图。

## 三、标签体系

### 3.1 核心标签（本周强制）

| 类别 | 标签 | 用途 |
| --- | --- | --- |
| 类型 | `spec` | 需求/规格/契约文档变更 |
| 类型 | `feature` | 功能或工程能力建设 |
| 类型 | `test` | 测试、验收、演练验证 |
| 类型 | `bug` | 可复现缺陷 |
| 模块 | `qbank` | 题库与组卷 |
| 模块 | `exam` | 在线考试与答卷 |
| 模块 | `grading` | AI 主观题阅卷与教师复核 |

### 3.2 扩展标签（按需）

`docs`（上下文、协作制度）、`infra`（仓库、CI、看板）、`priority:p0/p1/p2`（与看板 Priority 字段同步，便于按标签筛选）。

### 3.3 与现有 Issue 模板的兼容

`.github/ISSUE_TEMPLATE/` 当前默认标签为 `type:task` / `type:bug`。接入远端时二选一，不要长期并存：

- 方案 A（推荐）：把模板默认标签改为 `feature` / `bug`，与本文对齐。
- 方案 B：保留 `type:*`，在接入时建立映射 `type:task → feature|spec|docs|infra`、`type:bug → bug`，并同步更新模板说明。

一条 Issue 至少 1 个类型标签 + 1 个模块标签（纯文档/基础设施任务可用 `docs`/`infra` 代替模块标签）。

## 四、强制规则

1. **Issue 先行**：所有任务（含文档、演练）必须先建 Issue，再进看板。禁止“先干活后补 Issue”。
2. **PR 必须绑定 Issue**：PR 描述首行使用 `Closes #<实际编号>`；一个 PR 只解决一张主 Issue，关联其他 Issue 用 `Refs #N`。
3. **只有 Review 列的任务才允许提 PR**：实现或文档完成并自检后，先把卡片移到 `Review`，再创建 PR。未进 Review 就提 PR 视为流程违规，评审可要求撤回。
4. **看板是进度唯一依据**：周报、站会、验收均以看板为准；Issue 关闭但卡片未动的，由 Owner 当天修正。
5. **Owner 唯一**：每张卡只有 1 名 Owner；Reviewer 通过 PR 指定，不占用 Owner 字段。
6. **不跨列跳步**：允许 Backlog → This Week → In Progress → Review → Done，不允许跳过 Review 直接 Done（紧急回滚除外，需在卡片注明原因）。

## 五、自动化（接远端后配置）

在 Project → Workflows 中启用：

| 触发 | 动作 |
| --- | --- |
| Issue opened | 加入项目，Status = Backlog，按标签填 Module |
| Issue assigned | 建议提示（不自动改列，排期仍由周会决定） |
| PR opened / linked | 关联 Issue 卡片移到 Review |
| PR merged | 卡片移到 Done |
| Issue closed | 若未合并，提醒 Owner 核对验收结论 |
| 卡片在 In Progress 超过 3 天无更新 | 打 `stale` 标记并在周会复盘 |

自动化只做“机械流转”，不替代人工排期与验收。

## 六、接入远端与创建步骤

### 6.0 实际落地记录（2026-10-31）

| 项目 | 状态 |
| --- | --- |
| 远端仓库 | <https://github.com/AI-exam-team/ai-exam-system> |
| 看板 | <https://github.com/orgs/AI-exam-team/projects/2>，名称「AI 智能考试系统」 |
| 5 个状态列 | 已配置：`Backlog / This Week / In Progress / Review / Done` |
| Issues | #2～#11 已创建，对应规划 Issue-101～110 |
| 标签 | spec / feature / test / docs / infra / qbank / exam / grading 已创建 |
| 待确认 | 仓库关联、Module/Priority 字段、Workflows、成员访问、Issue 在列中的摆放 |

> 以下 1～8 步保留为操作指南；已完成部分以 6.0 表为准。

前置：仓库已推到 GitHub，6 名成员有写权限，CODEOWNERS 占位符已替换。

1. **创建 Project**
   - 仓库页 → Projects → New project → 选择 **Board** 模板（或 Table 模板后切换 Board 视图）。
   - 命名：`AI 智能考试系统 · 第 6 周及以后`；可见性按课程要求（建议 Private）。
2. **创建列**
   - 编辑内置 `Status` 字段，依次设置为：`Backlog`、`This Week`、`In Progress`、`Review`、`Done`；删除模板自带的 `Todo`/`In Progress`/`Done` 默认项后重建，确保名称完全一致。
3. **创建字段**
   - 按第二节新增 `Module`、`Owner`、`Issue`、`Priority`；`Status` 使用内置字段。
4. **创建标签**
   - 在仓库 Issues → Labels 中创建第三节标签；颜色建议：类型蓝/紫、模块绿、优先级红黄灰。
   - 同步修改 `.github/ISSUE_TEMPLATE/task.md` 与 `bug.md` 的默认标签（见 3.3）。
   - 也可用 CLI 批量创建：
     ```bash
     gh label create spec --color 1D76DB --description "规格与契约"
     gh label create feature --color 0E8A16 --description "功能与工程能力"
     gh label create test --color FBCA04 --description "测试与验收"
     gh label create bug --color D73A4A --description "缺陷"
     gh label create qbank --color 006B75 --description "题库与组卷"
     gh label create exam --color 006B75 --description "在线考试与答卷"
     gh label create grading --color 006B75 --description "AI 阅卷与复核"
     ```
5. **接入仓库**
   - Project → Settings → Manage access，添加 6 名成员；
   - 仓库 → Projects → 将本项目设为默认项目，新 Issue 自动加入。
6. **配置自动化**
   - 按第五节启用 Workflows，并用两张测试 Issue 验证流转。
7. **分支保护**
   - `main` 要求：必须 PR、至少 1 名非作者评审、CODEOWNERS 评审、对话解决、禁止强推与直推。
8. **验收**
   - 用 `Issue-104` 空 PR 演练走通 Backlog → … → Done 全流程；截图留档到 `docs/`（不提交业务代码）。

## 七、本周落地状态

- 远端仓库已接入，`main` 与四条分支已推送。
- Issues #2～#11 已创建并打标签；已完成项已关闭，Issue #5（空 PR）与 Issue #8（看板）保持 open。
- 看板已创建并配置 5 列：<https://github.com/orgs/AI-exam-team/projects/2>。
- 空 PR：PR #1（`feature/issue-104-empty-pr` → `main`），已绑定 Issue #5，待非作者评审。
- 待完成：把 Issue 放入看板并设置状态、关联仓库、配置字段与 Workflows、组员访问权限、CODEOWNERS 占位符替换。
