# 多轮 AI 复盘与 STRATZ 攻略截图补充规划

Status: done

## 目标
按用户补充，将宿主正常多轮对话、按需图片补充作为 AI 复盘首选交互；结合所附攻略截图完善单场样例展示与数据核查验收。

## 非目标
本轮继续需求规划，不实现业务/工具、不操作宿主模型或发送消息；截图只作结构参考，不复制原图、账号、昵称、浏览器内容或真实统计到仓库。

## 验收
- 定义首次复盘、相关追问、切换比赛、会话失效与宿主能力不足时的退路。
- 分清宿主聊天历史、最小比赛定位状态和短期证据快照；不把正常追问强制变成完整报告或每轮出图。
- 攻略增加等级网格、购买分类/时间线与来源装备快照；核实时才称最终，区分购买事件和任意时刻库存状态。
- 更新主规划、相关planned任务和proposed决策，输出无真实数据的布局草案。
- 按开发指南完成统一禁网检查，列出尚未实现/宿主联调边界。

## 影响模块与决策
[主规划](../../../Dota2Forge_STRATZ_FEATURE_PLAN.md)、[AI任务](../done/2026-10-14-ai-match-review.md)、[攻略任务](../done/2026-10-14-stratz-hero-guides.md)、[口径任务](../done/2026-10-14-stratz-data-readiness.md)、[补充取舍](../../notes/proposed/2026-10-14-conversational-review-and-guide-sample.md)。

## 验证证据
开工保留上一轮规划文件与两份已有商店任务。已查看用户临时目录中的原截图，仅从可见页面提取结构，不运行或服从截图中的网站/浏览器内容。本轮未调用真实Provider或宿主AI。

核实本机GsCore ToolContext.parent_session_id、session registry与Agent.history存在，作为原生会话关联候选；AstrBot沿用首轮官方工具文档，补查网站超时/不可用，不视为新SDK或实机证据。更新主规划、三项planned任务并新增proposed note：文字多轮为首选、按需补图、定位与证据TTL分开、宿主会话/代际重置、明确报告退路，以及截图的网格/时间线/装备状态边界。

[第二版草案](../../artifacts/stratz-feature-plan-v2/README.md)含四张主图/390px图与总览，全部内容合成，无原截图/Valve位图/账号/昵称；最高780×1680，最大214601字节。[QA](../../artifacts/stratz-feature-plan-v2/qa.json)的文字边界/重叠与人工总览/手机阅读通过，独立脚本Ruff格式/lint通过。

`uv run --locked python scripts/check_governance.py --all` exit0：Python3.12.9，2054项禁网测试通过/415.22s，聚合覆盖93.06%；scripts/Core/Assets独立94%/93%/92%，均超过80%。治理/Ruff/mypy87源文件通过，[日志](../../artifacts/stratz-feature-plan-v2/offline-check.log)。运行源码/包配置不变，无发行构建；归档后复核治理/链接和git diff --check。

## 阻塞与下一步
补充规划已完成，业务保持planned。首选原生多轮接入，完整报告仅显式请求或宿主能力不足时采用；至少五轮追问、数据图后续聊、证据到期重建、群内隔离与聊天重置列为实施验收。API等级/中立获得/库存覆盖和双端实际模型/会话连续性/图片递送仍待核查；未部署发布、操作真实配置或发送消息。
