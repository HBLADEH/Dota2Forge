# 段位徽章与金币图标

2026-10-05用户要求/dota玩家显示下载的段位图标，并增加合适的官方素材。使用Valve游戏美术的OpenDota PNG镜像；真实下载地址、摘要和版权写入清单，不把镜像称为Valve官网/CDN。英雄/装备仍来自此前的Valve datafeed及Steam CDN。

新增9个徽章（0未定级、1–8八档段位）、5个透明星级和金币共15张PNG。`--only-ui`仅更新这些图标，保留英雄、装备、catalogs、生成背景及其他清单字段；不替换已有图字节。素材和预览留在被忽略的.dota2forge-assets，不进入MIT wheel；[下载证据](download-verification.json)记录来源与验证。

玩家卡保留段位文字/编码，右侧组合184px徽章与同尺寸星级。rank_tier 11–75仅接受1–5星；0/80不加星，None/未知编码不猜图或排行榜名次。缺图保留文字，损坏摘要触发同次数据RenderError回退。近期与详情GPM添加金币；英雄/装备与已有标题背景保留。

[合成预览脚本](render_samples.py)生成41种段位情况及390px预览，包括全部35个普通段位、未定级、冠绝一世和未知/非法编码。实际共享Renderer的九类卡片也复核；[QA摘要](qa.json)仅包含合成数据统计。PNG在.dota2forge-assets/previews-rank-icons-v1和previews-with-rank-icons-v1，没有真实账号、聊天截图或Provider响应。人工查看全段位总览、完整玩家卡、近期/五人详情手机图：徽章/星级对应正确，金币清晰，文字未遮挡；详情金币与末装备槽留4px间距后复核。

相关68项禁网测试通过；统一入口1195项测试、Ruff格式/lint、mypy62源文件通过，聚合覆盖率92.74%、scripts97%、Core92%。初次engine格式检查失败，修正格式后重跑全绿；失败和通过日志保留，见[检查摘要](checks.json)。四包构建与独立wheel安装/导入通过；没有改测试、policy、治理脚本或门槛。

两端完成受控更新：GsCore收到限定目标控制台的SIGINT并记录stopping/stopped；AstrBot插件停用记录terminated state=stopped，桌面关闭按钮实际隐藏到托盘，确认插件终止后退出桌面与后端旧进程。停止后在各数据目录backups/rank-icons-v1-20261005-142516备份配置/数据库/三个包/发现资源/素材清单，只重装Renderer wheel并同步15张PNG。六份包与双端桥接逐文件匹配；原543张图、原配置和安装期间数据库指纹不变，依赖版本不变。

实际宿主Python均生成相同780×850段位卡（227624 bytes）并解码徽章/星级/金币/背景；隐藏冷启动后两端ready/image，AstrBot恢复启用且OneBot已连接，既有GsCore桥接保持关闭。宿主合成PNG留在各自validation-rank-icons-v1目录。[部署证据](deployment.json)不含真实聊天数据；新图聊天尚未确认，上一轮菜单图片反馈不作为本轮证据。

实现与部署已完成，见[任务](../../tasks/done/2026-10-05-official-rank-icons.md)；本轮新的聊天反馈接续于[宿主聊天任务](../../tasks/active/2026-10-05-dota-style-host-deployment.md)。
