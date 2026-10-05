# 段位 MMR 估算契约

[estimate_rank_mmr](../../packages/dota2forge-core/src/dota2forge_core/domain/ranks.py)是纯函数，返回不可变 RankMmrEstimate 或 None。lower_bound/upper_bound 为包含边界的预估整数区间，upper_bound=None 表示只知预估下界。规则名 community-medal-v1；不是 Provider 返回的实测 MMR，不修改 PlayerProfile、来源、missing_fields 或缓存载荷。

11–65按前六档每档770分、每星154分估算；71–75从4620起每星200分；80为5620+且无已知上界。例如51是3080–3233分，75是5420–5619分。11的0是区间下界，不能解释为该玩家实测0分。None、0未定级以及其他非标准编码返回None；负值/bool/非整数为ValidationError。段位下降允许预估同步下降。

依据是社区阈值模型：[GameMapa维护者公开的计算规则](https://gamemapa.com/en/dota-2/tools/mmr-calculator/)，2026-10-05核对其770/4620/5620阈值与非官方声明；历史200分/冠绝阈值调查见[原始社区调查讨论](https://dota2.fandom.com/wiki/Talk:Matchmaking/Seasonal_Rankings)。阈值可能变化，段位可能滞后；估算不保证实际MMR落在区间内。规则变更须版本化并附note，不能随抓取日期宣称阈值已实时更新。

双端 do查询 [ID] 消费同一Core函数；共享Renderer与两端文本回退显示预估区间、非精确说明和原PlayerProfile来源/时间。未知不补零，冠绝不猜排行榜名次。玩家卡为780×960，保留原段位徽章/星级；一次查询仍只请求已有玩家Provider，不额外请求或跨源补MMR。

源码及离线消费已实现；2026-10-05本机双端已同时升级Core、Renderer、适配器与桥接至0.1.0a2并恢复ready/image，新MMR合成渲染通过。新MMR真实聊天仍待验收；GsCore本轮尚无客户端连接，升级不能仅更新Renderer。改名见[决策](../../.agents/notes/implemented/2026-10-05-do-commands-rank-mmr.md)，本机升级见[AstrBot](../../.agents/artifacts/astrbot-screenshot-update-v1/README.md)与[GsCore](../../.agents/artifacts/gscore-current-deployment-v1/README.md)。
