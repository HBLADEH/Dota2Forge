# 共享图片展示契约

[dota2forge_renderer](../../packages/dota2forge-renderer/src/dota2forge_renderer/)依赖Core归一化模型和Pillow，禁止平台SDK、Provider请求、SQL和环境读取。Core不依赖Renderer。普通导入不加载本地字体/资源；PillowRenderer首次render才加载版本化资源，close清理缓存。

0.1.0a3支持Pillow>=11.3,<13；为兼容GsCore锁定fastembed的<12约束，Pillow11.3下共享Renderer与双端消费者424检查通过。运行安装器保留宿主约束并执行pip check，见[发行决策](../../.agents/notes/implemented/2026-10-06-gscore-public-release.md)。

## 卡片与资源

MenuCard、PlayerCard、RecentMatchesCard、StatusCard、MatchDetailCard、HeroItemsCard输出PNG ImageArtifact，包含bytes、mime、width、height；不发送消息、不创建HTTP客户端。输入为Core不可变结果。出图宽780、最高1800px、最大2MiB，近期每页五场，比赛按阵营每页最多三名参赛者（标准十人四页）；长昵称省略，未知英雄保留ID，缺图显示问号。

HeroItemsCard高1674px，四阶段各展示购买次数前5项，以对应本地装备图、两行名称和次数横排；标题展示英雄图片。本地Valve物品名称未知则保留ID，0/空/缺失明确区分。位置/补丁/窗口/总样本未知，注明热门不等于最优或顺序；来源与时间保留，双端文字共享同一结果。见[出装契约](hero-items.md)。

现行入口使用do前缀，玩家为do查询；玩家卡780×960显示[Core段位MMR估算](ranks.md)区间/冠绝下界及非精确提示，未知/未定级不估算。图片与双端文本一致；本机双端已升级0.1.0a2并完成新卡合成渲染验证，[GsCore](../../.agents/artifacts/gscore-current-deployment-v1/README.md)本轮尚无客户端连接，新MMR真实聊天待验收，历史聊天证据仍为旧指令。

None/0/False区别保留；装备0显示空槽，None未知。来源、抓取时间和未知观测时间分别标识，默认北京时间UTC+8，时长分钟/秒。段位可下降，不代表精确MMR；详情卡展示parse_state、解析时间及来源标记（STRATZ isStats / OpenDota version），上游已标记解析仍不声明字段完整，解析版本不是游戏补丁。绑定账号实际参赛才高亮我方，匿名/未知账号不显示身份。

[资源v1](../../packages/dota2forge-renderer/src/dota2forge_renderer/assets/v1/README.md)附完整Noto Sans CJK SC/OFL、字体SHA256/cmap和Valve127英雄名称表来源摘要。未支持的字符降级U+编码。深色卡片使用铜金分隔/天辉夜魇色；PillowRenderer新增可选illustration_path，双端同名配置显式注入本地Valve下载包，英雄横幅/六装备槽按Core ID映射，详情装备名支持两行；玩家区步长340px，三人页1706px。长名使用审核简称（A杖、臂章等），文字保留全名；整个名称表严格检查两行容纳，图纸/变体保留区别。详情新增等级、补刀、反补、净资产、英雄伤害、建筑伤害与治疗量，缺失仍为未知，0保留；两端文字回退包含相同字段与完整装备名/ID。常见模式显示中文，未知枚举保留原值。当前包不含第三方图像，MIT不重新许可Valve美术；[下载指南](../cookbook/illustrations.md)记录清单和版权边界。未知ID/缺图占位，槽位展示装备名称、空与未知，未知物品保留ID；超长装备ID回退文本，避免隐藏ID。可选decor.header只作标题背景；本地已接入1536×512原创生成图，中心裁切为780×174并叠加60%深色遮罩，模型未由工具返回，未打包进wheel。manifest版本/路径/SHA256验证，48张解码缓存、单图8MiB/2048²像素；close释放。资源/字体/PNG已知失败为RenderError，数据/程序错误不吞成正常卡片。

## 线程与回复

可选本地ranks(0–8)/rank_stars(1–5)/ui.gold使用下载的Valve游戏图标（OpenDota镜像来源，非Valve托管URL）。玩家卡按rank_tier展示徽章和透明星级：0未定级、80冠绝一世；None/其他编码不推断，段位文字/编码保留。缺徽章不画星级，缺星级保留文字；金币仅辅助近期/详情GPM。旧v1清单兼容，公共卡片/适配器接口未变；来源与下载见[素材指南](../cookbook/illustrations.md)，原因见[段位决策](../../.agents/notes/implemented/2026-10-05-official-rank-icons.md)。

10-05段位/金币图已部署本机双端，宿主合成玩家卡、资源关闭及冷启动ready验证通过；41种段位/九类卡片手机预览与1195项禁网检查通过。新徽章真实聊天尚待用户反馈，见[段位验收](../../.agents/artifacts/rank-icons-v1/README.md)。

共享菜单展示玩家/指定比赛订阅入口、默认关闭及群Bot管理员提示；常规1450px、管理员1580px，仍在1600px上限内。subscription_event_text消费Core不可变比赛报告/段位/日报事件，保留详情、来源、抓取时间、事件ID、分析缺失和非官方MVP候选边界；只生成文本，不投递。

AsyncRenderer通过工作线程绘制编码，一实例最多一条线程及四个等待者。调用者取消不停止已开始线程，所有权保留；下一次绘制和close先等待旧线程。关闭任务shield，即使等待者被取消仍能继续完成；closed拒绝新请求。调用方应在宿主停用/退出时await close。

Dota2UID默认reply_mode=image，可配置text；不带该项的旧配置默认image。handle保持文本诊断，宿主dispatch返回TextReply/ImageReply并由发现桥接转换为str/PNG bytes。成功数据取得后先准备文本，再渲染整组；RenderError回退同次成功数据的全部文本，不再次调用Provider。错误保持分类文本；发送失败不重发或提交新列表。

菜单仅列已启用命令，管理员停用项依可信权限；图片是命令说明，不是按钮。MenuCard/StatusCard增加可选adapter_label，默认Dota2UID，AstrApplication显式用Dota2Forge / AstrBot；既有构造兼容。近期默认10场最多先发两页，剩余页/第N场复用已有有界结果状态。详情按实际阵营拆页，来源和字段未知仍可区分。AstrApplication及宿主桥接消费Renderer；AstrBot真实生命周期、OneBot单会话菜单/绑定/玩家/战绩分页/序号详情图片已通过用户复测且可读，见[AstrBot验收](../../.agents/artifacts/astrbot-host-v1/README.md)。其他平台及直接ID/权限场景未实机验证。

## 验证边界

[生产合成样图](../../.agents/artifacts/image-interaction-v1/production/overview.png)已通过本地文字边界和390px视觉检查；普通pytest禁网，覆盖资源/缺失/超量分页、线程取消与回退。GsCore/QQ单会话菜单、玩家、账号、分页、序号及直接ID图片已确认可读，冷启动和两轮停用/重载通过，[证据](../../.agents/artifacts/gscore-image-lifecycle-v1/README.md)。AstrBot/OneBot主流程图片的用户反馈单独记录；不保存账号/真实聊天截图。多账号、异常压缩、其他平台未实机验证；跟踪[图片任务](../../.agents/tasks/active/2026-10-01-image-interaction.md)和[详情任务](../../.agents/tasks/active/2026-10-01-historical-match-detail.md)。

原因见[共享渲染决策](../../.agents/notes/implemented/2026-10-01-shared-image-renderer.md)。

2026-10-04深色卡片与本地官方插图、10-05生成标题背景经[九张合成卡片QA](../../.agents/artifacts/dota-style-v2/README.md)，禁网测试另记录于[已完成插图任务](../../.agents/tasks/done/2026-10-04-dota-style-illustrations.md)。10-05已部署本机双端并冷启动ready，新背景实际加载；[本轮宿主/聊天验收](../../.agents/artifacts/dota-style-host-v2/README.md)单独记录，历史浅色验收不等同新主题验收。[本地素材决策](../../.agents/notes/implemented/2026-10-04-local-dota-illustrations.md)延续无HTTP渲染边界。

本轮卡片优化的[合成预览与边界](../../.agents/artifacts/readable-cards-v1/README.md)、[字段与存储决策](../../.agents/notes/implemented/2026-10-06-readable-cards-and-detail-stats.md)已记录，尚未发布运行包或部署生产。

0.1.0a4增加长名留白，图片上限1800px，2MiB不变；[发行决策](../../.agents/notes/implemented/2026-10-06-a4-layout-and-astrbot-release.md)。
