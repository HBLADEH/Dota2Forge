本版新增 STRATZ 强势英雄、详细攻略和原生多轮复盘，并改善攻略展示与 AI 建议流程。

- `do强势`：分位置展示胜率、可靠度、场次、版本与实际统计窗口。
- `do主宰攻略 1号位 详细`：装备图标复用现有素材；技能／天赋优先显示对应来源版本的中文名称，缺失模块不发送空白长图。
- `do复盘 <比赛ID> [英雄]`：同一会话可连续追问，无需重复比赛 ID；按需补充经济曲线、购买记录和团队数据图。
- 内置 `dota2-review` Skill 1.0.0：先检查数据完整度，按对线经济、出装和团队职责展开，给出事实依据、可执行调整及条件／代价。支持的 GsCore 注册原生 Skill，工具也会提供相同专题指南。
- 复盘优先 STRATZ；符合条件的来源失败或仅基础数据时，只读尝试 OpenDota 整份兜底，明确来源与原因，不拼接两源或自动提交录像解析。

运行组件：Dota2UID **0.1.0a16**、Core **0.1.0a9**、Renderer **0.1.0a8**、Assets **0.1.0a1**。四个运行 wheel 随分发提供并固定 SHA256；Assets a1 沿用原公开字节。

更新前备份插件数据，发送 `do停用`，退出 GsCore，更新插件后冷启动；用 `do核心状态` 确认实际运行版本。启用宿主 AI 模型及当前人格的复盘工具；若设置仅 @ 回复，每次追问也需要 @。无需另装 Skill。完整步骤见仓库 `INSTALL.md`。

已完成五包与两端分发的离线隔离安装；真实模型效果仍由用户测试。尚未接入死亡、团战和视野事件，不能把经济曲线当作录像或分锅依据。

固定源码：[0e3ecc0](https://github.com/HBLADEH/Dota2Forge/commit/0e3ecc0d1eda948b548feae03c7c9fa62944d52d)。复盘指南参考 [dota2-newbie-assistant](https://github.com/timzhangherenow/dota2-newbie-assistant)，MIT 归属与许可随 Core 保留。旧版 Release 与标签保留。
