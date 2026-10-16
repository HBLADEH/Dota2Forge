本版新增 STRATZ 强势英雄、详细攻略和原生多轮复盘；复盘工具携带与 GsCore 共用的 Skill 指南。

- `/do强势`：分位置展示胜率、可靠度、场次、版本与实际统计窗口。
- `/do主宰攻略 1号位 详细`：装备图标复用现有素材；技能／天赋优先显示对应来源版本的中文名称，缺失模块不发送空白长图。
- `/do复盘 <比赛ID> [英雄]`：开始后在同一会话正常追问，并按需要补充经济、购买和团队数据图。
- 工具内置共享 `dota2-review` Skill 1.0.0 的当前专题指南，先检查数据完整度，再按对线经济、出装和团队职责给出事实依据、调整候选及条件／代价，无需另装终端 Skill。
- 复盘优先 STRATZ；符合条件的来源失败或仅基础数据时，只读尝试 OpenDota 整份兜底，明确来源与原因，不拼接两源或自动提交录像解析。

运行组件：AstrBot 插件 **0.1.0-alpha.14**（Python 包 **0.1.0a14**）、Core **0.1.0a9**、Renderer **0.1.0a8**、Assets **0.1.0a1**。四组件依赖指向本版 Release 的固定 wheel URL 与 SHA256；Assets a1 沿用原公开字节。

升级须先停用并退出 AstrBot，备份配置和数据，更新插件目录后，用**运行 AstrBot 的 Python**重新执行 `install_runtime.py --host-python <相同解释器>`，成功后冷启动。只更新桥接或点击热重载不能证明四个组件已更新，完整步骤见仓库 `INSTALL.md`。

复盘需要宿主已配置可用 AI 模型，并允许当前会话／人格使用插件工具。斜线和 @ 按宿主唤醒设置使用，设置仅 @ 回复时，每次追问也需要 @。

已完成五包与两端分发的离线隔离安装；AstrBot 真实多轮会话和新 Skill 的模型效果仍由用户测试。尚未接入死亡、团战和视野事件，不能把经济曲线当作录像或分锅依据。GitHub 发布与 Cloud 商店审核分别记录。

固定源码：[0e3ecc0](https://github.com/HBLADEH/Dota2Forge/commit/0e3ecc0d1eda948b548feae03c7c9fa62944d52d)。复盘指南参考 [dota2-newbie-assistant](https://github.com/timzhangherenow/dota2-newbie-assistant)，MIT 归属与许可随 Core 保留。旧版 Release 与标签保留。
