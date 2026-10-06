# 本地段位徽章与星级

Category: data
Related task: [官方段位图标](../../tasks/done/2026-10-05-official-rank-icons.md)
Related code: [素材加载](../../../packages/dota2forge-renderer/src/dota2forge_renderer/illustrations.py)
Related docs: [本地素材](../../../docs/cookbook/illustrations.md)

## Problem
玩家卡仅有段位文字，用户要求下载官方段位素材并增加其他有明确语义的官方图标。已有manifest仅支持英雄、装备和背景；Valve官网/CDN的候选段位地址实际返回404。

## Decision
沿用version=1本地清单，增加可选ranks（0–8）、rank_stars（1–5）和ui.gold。使用OpenDota维护的Valve游戏PNG素材镜像，明确记录source_kind=valve_game_art_mirror、mirror、实际URL、抓取时刻、SHA256与Valve版权；不把镜像称为Valve托管地址，不声明获得再分发许可。游戏公开资源目录中存在rank_tier_icons/rankN_psd和pipN_psd，镜像公开展示同类徽章/星级；不推断原游戏当前文件与镜像PNG字节等同。

显式下载工具新增--only-ui，保留原英雄/装备/catalogs/decor和自定义清单字段，只更新段位/星级/金币；默认完整下载也包括新图标。所有请求完成后再发布文件和清单，沿用仅404缺图、其他失败中止规则。Renderer只读本地，沿用路径/摘要/像素/缓存边界；旧v1清单缺新节仍有效，两端共享行为，无新增Core字段或适配器依赖。

rank_tier为11–75且星数1–5时组合徽章与同尺寸透明星级；0只用未定级图，80只用冠绝一世图。None/其他编码不画已知段位，文字保留未知和编码；不使用排行榜专属徽章，Core没有名次。缺徽章不单独画星级；缺星级仍显示真实段位文字。金币图标仅辅助已有GPM指标，不推断经济数据。

## Alternatives considered
生成徽章或绘制近似段位：不满足用户的真实素材要求。把镜像当官方CDN：来源表述不实，因此逐条记录实际镜像。将PNG打入MIT wheel：无已核实再分发许可，继续独立下载。每次回复下载：破坏离线边界，使用预下载和新Renderer缓存。

## Consequences
旧配置无须新增字段。镜像可变化，下载摘要与缺图可追溯；本地无新资源仍保留段位文字。图标不替代文字、星级或未知状态。宿主需要同步素材并升级共享wheel，源码预览不等于部署/聊天验收。

## Verification
15张PNG实际下载并验证SHA256/PNG，原英雄/装备/catalogs/背景字段保留，558张可用图逐一复核；129条旧装备缺图不变。68项相关禁网测试通过；41种段位与九类卡片的390px人工QA通过。统一入口最终1195项测试、Ruff/mypy62源文件通过，聚合覆盖率92.74%，scripts97%、Core92%；初次格式失败日志保留，修正格式后重跑通过，未改门槛。

四包构建/独立wheel检查通过。两端先确认插件资源关闭、退出旧宿主，备份后仅重装Renderer wheel、同步15张图；六份安装包和双端桥接逐文件匹配。原543张图、配置和安装期间数据库指纹保持不变，Pillow12.3.0/HTTPX0.28.1未改。宿主Python均生成相同780×850段位卡并实际解码徽章/星级/金币/背景；两端冷启动ready、AstrBot恢复启用且OneBot已连接，GsCore桥接仍关闭。新图真实聊天等待用户确认，不用上一轮菜单反馈替代。详见[证据](../../artifacts/rank-icons-v1/README.md)。
