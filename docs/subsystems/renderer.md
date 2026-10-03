# 共享图片展示契约

[dota2forge_renderer](../../packages/dota2forge-renderer/src/dota2forge_renderer/)依赖Core归一化模型和Pillow，禁止平台SDK、Provider请求、SQL和环境读取。Core不依赖Renderer。普通导入不加载本地字体/资源；PillowRenderer首次render才加载版本化资源，close清理缓存。

## 卡片与资源

MenuCard、PlayerCard、RecentMatchesCard、StatusCard、MatchDetailCard输出PNG ImageArtifact，包含bytes、mime、width、height；不发送消息、不创建HTTP客户端。输入玩家/比赛数据为Core不可变结果。出图宽780、最高1600px、最大2MiB，每页五场/五名参赛者；长昵称省略，未知英雄保留ID，缺图显示问号。

None/0/False区别保留；装备0显示空槽，None未知。来源、抓取时间和未知观测时间分别标识，默认北京时间UTC+8，时长分钟/秒。段位可下降，不代表精确MMR；详情卡展示parse_state、解析时间及来源标记（STRATZ isStats / OpenDota version），上游已标记解析仍不声明字段完整，解析版本不是游戏补丁。绑定账号实际参赛才高亮我方，匿名/未知账号不显示身份。

[资源v1](../../packages/dota2forge-renderer/src/dota2forge_renderer/assets/v1/README.md)附完整Noto Sans CJK SC/OFL、字体SHA256/cmap和Valve127英雄名称表来源摘要。未支持的字符降级U+编码；未打包第三方英雄/装备图像，许可未核前只用原创占位。资源读取/字体/PNG已知失败为RenderError，数据/程序错误不吞成正常卡片。

## 线程与回复

共享菜单展示玩家/指定比赛订阅入口、默认关闭及群Bot管理员提示；常规1450px、管理员1580px，仍在1600px上限内。subscription_event_text消费Core不可变比赛报告/段位/日报事件，保留详情、来源、抓取时间、事件ID、分析缺失和非官方MVP候选边界；只生成文本，不投递。

AsyncRenderer通过工作线程绘制编码，一实例最多一条线程及四个等待者。调用者取消不停止已开始线程，所有权保留；下一次绘制和close先等待旧线程。关闭任务shield，即使等待者被取消仍能继续完成；closed拒绝新请求。调用方应在宿主停用/退出时await close。

Dota2UID默认reply_mode=image，可配置text；不带该项的旧配置默认image。handle保持文本诊断，宿主dispatch返回TextReply/ImageReply并由发现桥接转换为str/PNG bytes。成功数据取得后先准备文本，再渲染整组；RenderError回退同次成功数据的全部文本，不再次调用Provider。错误保持分类文本；发送失败不重发或提交新列表。

菜单仅列已启用命令，管理员停用项依可信权限；图片是命令说明，不是按钮。MenuCard/StatusCard增加可选adapter_label，默认Dota2UID，AstrApplication显式用Dota2Forge / AstrBot；既有构造兼容。近期默认10场最多先发两页，剩余页/第N场复用已有有界结果状态。详情按实际阵营拆页，来源和字段未知仍可区分。AstrApplication及宿主桥接消费Renderer；AstrBot真实生命周期、OneBot单会话菜单/绑定/玩家/战绩分页/序号详情图片已通过用户复测且可读，见[AstrBot验收](../../.agents/artifacts/astrbot-host-v1/README.md)。其他平台及直接ID/权限场景未实机验证。

## 验证边界

[生产合成样图](../../.agents/artifacts/image-interaction-v1/production/overview.png)已通过本地文字边界和390px视觉检查；普通pytest禁网，覆盖资源/缺失/超量分页、线程取消与回退。GsCore/QQ单会话菜单、玩家、账号、分页、序号及直接ID图片已确认可读，冷启动和两轮停用/重载通过，[证据](../../.agents/artifacts/gscore-image-lifecycle-v1/README.md)。AstrBot/OneBot主流程图片的用户反馈单独记录；不保存账号/真实聊天截图。多账号、异常压缩、其他平台未实机验证；跟踪[图片任务](../../.agents/tasks/active/2026-10-01-image-interaction.md)和[详情任务](../../.agents/tasks/active/2026-10-01-historical-match-detail.md)。

原因见[共享渲染决策](../../.agents/notes/implemented/2026-10-01-shared-image-renderer.md)。
