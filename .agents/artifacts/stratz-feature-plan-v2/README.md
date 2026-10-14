# 多轮复盘与单场攻略样例草案

2026-10-14（北京时间）。用户补充“正常多轮聊天、适当图片补充”，并提供STRATZ单场攻略截图；当前方案见[主规划](../../../Dota2Forge_STRATZ_FEATURE_PLAN.md)与[补充note](../../notes/proposed/2026-10-14-conversational-review-and-guide-sample.md)。本目录无业务实现或真实比赛数据。

截图只在用户临时附件中查看，保留的结构是比赛摘要、1–25级技能网格、分组装备时间线与装备快照；不复制原图/浏览器/昵称/账号/真实统计，不根据低清物品图猜ID或升级。截图不构成API可用性证据。任意时刻库存需额外来源，不能用购买列表模拟。

GsCore本机源码有ToolContext.parent_session_id、session registry与Agent.history，可作为当前宿主原生多轮关联的候选；本轮只读取，没有调用模型/消息API。AstrBot沿用首轮官方AI工具文档，补查当前网页遇到不可用/超时，当前conversation关联、历史记录与各执行器仍待SDK及实机验收。不能把一次性LLM回答当多轮已实现。

第二版预览使用现有Canvas/theme、固定合成内容和本地字体，展示单场攻略结构与按需数据图/对话顺序；不含Valve位图，不修改第一版历史草案。

- [加点 / 装备 / 对话顺序总览](overview.png)
- [样例升级网格](guide-sample-skills.png) / [390px](guide-sample-skills-phone.png)
- [样例购买时间线与装备快照](guide-sample-items.png) / [390px](guide-sample-items-phone.png)
- [按需经济补图](review-data.png) / [390px](review-data-phone.png)
- [多轮交互顺序](conversation.png) / [390px](conversation-phone.png)

复现：`uv run --locked python .agents/artifacts/stratz-feature-plan-v2/render_previews.py`。脚本只绘制合成内容，不读原截图/Token，不请求Provider/模型或导入宿主。四张主图780px宽，最高1680px、最大214601字节，均通过Canvas文字边界/重叠检查与人工总览/手机阅读；[QA](qa.json)列各图结果。脚本Ruff格式/lint通过。统一禁网检查另记任务，不将草案当业务或实机截图。

[统一检查](offline-check.log)exit0：2054项禁网测试通过/415.22s，聚合覆盖93.06%，Ruff/mypy与三组独立覆盖率门槛通过；详情见[完成任务](../../tasks/done/2026-10-14-conversational-review-planning.md)。[归档后治理复核](governance-final.log)单独记录；两端实际多轮、工具链、重置和图片递送仍未联调。
