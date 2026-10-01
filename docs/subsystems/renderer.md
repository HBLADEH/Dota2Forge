# 共享图片展示契约

[dota2forge_renderer](../../packages/dota2forge-renderer/src/dota2forge_renderer/)依赖Core归一化模型和Pillow，禁止平台SDK、Provider请求、SQL和环境读取。Core不依赖Renderer。普通导入不加载本地字体/资源；PillowRenderer首次render才加载版本化资源，close清理缓存。

## 卡片与资源

MenuCard、PlayerCard、RecentMatchesCard、StatusCard、MatchDetailCard输出PNG ImageArtifact，包含bytes、mime、width、height；不发送消息、不创建HTTP客户端。输入玩家/比赛数据为Core不可变结果。出图宽780、最高1600px、最大2MiB，每页五场/五名参赛者；长昵称省略，未知英雄保留ID，缺图显示问号。

None/0/False区别保留；装备0显示空槽，None未知。来源、抓取时间和未知观测时间分别标识，默认北京时间UTC+8，时长分钟/秒。段位可下降，不代表精确MMR；详情卡展示 `parse_state`、解析时间和 `isStats`，上游已标记解析仍不声明字段完整。绑定账号实际参赛才高亮我方，匿名/未知账号不显示身份。

[资源v1](../../packages/dota2forge-renderer/src/dota2forge_renderer/assets/v1/README.md)附完整Noto Sans CJK SC/OFL、字体SHA256/cmap和Valve127英雄名称表来源摘要。未支持的字符降级U+编码；未打包第三方英雄/装备图像，许可未核前只用原创占位。资源读取/字体/PNG已知失败为RenderError，数据/程序错误不吞成正常卡片。

## 线程与回复

AsyncRenderer通过工作线程绘制编码，一实例最多一条线程及四个等待者。调用者取消不停止已开始线程，所有权保留；下一次绘制和close先等待旧线程。关闭任务shield，即使等待者被取消仍能继续完成；closed拒绝新请求。调用方应在宿主停用/退出时await close。

Dota2UID默认reply_mode=image，可配置text；不带该项的旧配置默认image。handle保持文本诊断，宿主dispatch返回TextReply/ImageReply并由发现桥接转换为str/PNG bytes。成功数据取得后先准备文本，再渲染整组；RenderError回退同次成功数据的全部文本，不再次调用Provider。错误保持分类文本；发送失败不重发或提交新列表。

菜单仅列已启用命令，管理员停用项依可信权限；图片是命令说明，不是按钮。近期默认10场最多先发两页，剩余页/第N场复用已有有界结果状态。详情按实际阵营拆页，来源和字段未知仍可区分。AstrApplication 已在无宿主 SDK 的离线组合层消费Renderer；AstrBot平台注册/生命周期/真实消息仍未验证，不宣称双端图片闭环。

## 验证边界

[生产合成样图](../../.agents/artifacts/image-interaction-v1/production/overview.png)已通过本地文字边界和390px视觉检查；普通pytest禁网，覆盖资源/缺失/超量分页、线程取消与回退。用户提供的真实群聊截图确认玩家概况卡可读，并代验菜单、战绩第二页和第1场序号详情；截图不入库。QQ压缩、直接 ID 成功响应、会话取页和宿主重载的完整场景尚未验证；跟踪[图片任务](../../.agents/tasks/active/2026-10-01-image-interaction.md)和[详情任务](../../.agents/tasks/active/2026-10-01-historical-match-detail.md)。

原因见[共享渲染决策](../../.agents/notes/implemented/2026-10-01-shared-image-renderer.md)。
