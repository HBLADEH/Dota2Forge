# 图片菜单与基础查询回复

Status: in_progress

## 目标
在已验证的 Dota2UID QQ 闭环上，实现以图片为主的帮助菜单、玩家概况、近期战绩和账号状态交互，参考 StarRailUID 的命令 → 数据 → 卡片 → 图片发送方式。

## 非目标
首个切片不新增单局详情/IMP/经济数据、按钮回调、订阅、自动重试或跨源回退。图片中的菜单项是命令说明，点击交互需后续平台能力验证。

## 验收
- [x] 先生成合成样图、390 px 手机预览和离线复现原型，记录字体授权、缺图占位和初步分页参数。
- [x] 采用已完成样图的浅色主题、完整 OTF、780px 手机布局和每页5场基线；菜单只列已启用功能，管理员项按可信权限控制。
- [x] 实现独立共享包 dota2forge-renderer（导入 dota2forge_renderer），不依赖平台 SDK；Core 领域/用例不依赖绘图库或浏览器，适配器共用结果。
- [x] 以 Pillow 完成 MenuCard、PlayerCard、RecentMatchesCard、StatusCard、MatchDetailCard；错误和必要提示保留可读文本。
- [x] dota菜单/dota帮助、dota玩家、dota战绩、dota比赛 返回图片优先；文本模式可配置，展示比赛 ID 及详情查询方式。
- [x] 使用北京时间并标明时区，时长为分钟/秒；维护版本化完整字体、cmap、英雄名称来源/摘要与缺图占位，未知英雄保留 ID。
- [x] 不把 None 画成零，0/False 有效；段位可下降，不承诺精确 MMR/完整历史，区分抓取时间与未知观测时间。
- [x] Renderer 接收结构化数据与本地资源，不发 Provider 请求；绘制/编码经工作线程并限制并发、尺寸和文件大小，取消/停用等待资源关闭。
- [x] 规范 TextReply/ImageReply；RenderError 回退同次数据文本，不二次请求、不吞数据源失败，发送失败不得盲目重复发送。
- [x] 已接 Dota2UID 代码与离线桥接测试（包含 PNG bytes 转换）；四包锁定/build/wheel/治理路径已更新。
- [x] 用户已确认授权群聊中基础图片可正常显示；AstrApplication 已离线消费共享 Core/Renderer。
- [ ] 真实压缩、停用/重载和 AstrBot 平台注册仍待验；用户已实测菜单、战绩10、第二页和第1场详情，直接ID本次因STRATZ不可用。policy/scripts/workflow 改动需维护者评审。
- [x] 禁网合成测试覆盖长昵称、中文字体、未知字段、无战绩、100场分页、缺资源、线程取消和回退；生产卡片 QA 检查裁切/重叠。真实单会话验收另列且不入库聊天截图。

## 影响模块与决策
[项目规划](../../../Dota2Forge_PROJECT_PLAN.md)、[Dota2UID 展示](../../../adapters/Dota2UID/src/Dota2UID/presentation.py)、[Core 模型](../../../packages/dota2forge-core/src/dota2forge_core/domain/models.py)、[待实施决策](../../notes/proposed/2026-10-01-image-history-interaction.md)、[详情接续](2026-10-01-historical-match-detail.md)。

## 验证证据
2026-10-01 用户要求逐步执行决策。样图已按浅色主题/完整字体/780px/5场基线技术采用；生产共享包和图片命令已实现。样图与资源记录见 [样图](../../artifacts/image-interaction-v1/README.md)，生产契约见 [Renderer契约](../../../docs/subsystems/renderer.md)，原因见 [Renderer决策](../../notes/implemented/2026-10-01-shared-image-renderer.md)。参考StarRailUID只承接调用方式，不复制代码/资产。

共享包实际生成9张合成卡片及390px预览，覆盖菜单/管理员、玩家、状态、近期两页/空列表、详情两队；QA检查字体cmap、边界/重叠、尺寸/2MiB、缺图和100条布局。生产字体/英雄资源来源见Renderer资源README，图像资源未授权前使用占位。

AstrBot-neutral application layer added under `adapters/astrbot_plugin_dota2forge`; it injects Core/MatchDetailService/Renderer without importing AstrBot. 19 offline consumer/command tests pass, and package smoke asserts the public export. Platform registration/lifecycle/real-message delivery remain unverified.

最终统一入口通过：813项禁网测试，Ruff、mypy 36源文件；综合96.27%，scripts约97%、Core约99%，Dota2UID约95%、Renderer约98%，AstrApplication/commands 纳入聚合覆盖，独立80%门槛通过。四包build与无索引隔离wheel smoke通过；Pillow wheel由显式stage脚本准备。真实宿主图片发送和图标授权扩展未验证。

2026-10-01 本机 CPython 3.13.2 GsCore 已安装四包 wheel（Pillow cp313），更新 config.toml 为 `reply_mode = "image"`，替换发现桥接并保存旧桥接副本；进程冷启动后保持响应，宿主 Python 独立导入 Dota2UID/Renderer、读取 OFL 资源并生成780px菜单图通过。WebConsole session 已过期，状态接口返回401，未冒充管理员；日志显示宿主依赖安装失败/其他插件错误，但没有 Dota2UID 导入错误证据。未发送 QQ 图片。

用户随后提供群聊截图，确认玩家概况卡可读；本轮又确认菜单、战绩分页和序号详情成功。截图不入库，不记录身份；压缩/停用/重载仍未全场景通过。

用户已提供群聊截图并授权联调；Computer Use 无窗口，不能从 SQLite/日志猜身份。窗口不可操作时用户代执行命令并反馈视觉结果，Runtime 日志只核对生成/发送/列表提交；验证图片收发/压缩、分页、详情、序号、停用/重载和回退。

## 阻塞与下一步
共享Renderer、Dota2UID图片/文本模式、同次回退与离线QA已完成。下一步是重启后日志核对、压缩/停用/重载和 STRATZ 恢复后的直接ID重试，再由AstrBot消费同一Renderer；IMP/经济序列仍不阻塞首轮卡片。
