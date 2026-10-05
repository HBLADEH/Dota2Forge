# 深色卡片与标题背景部署及聊天实测

Status: in_progress

## 目标
用户授权将已认可的共享深色卡片、官方素材和v2标题背景部署到本机既有GsCore/AstrBot，并完成真实聊天及客户端视觉检查。

## 非目标
不发布仓库或包索引，不创建新订阅，不修改绑定/凭据，不向猜测会话发送消息；保留现有工作区修改和宿主数据。

## 验收
- [x] 核实两端路径、运行状态、现有配置与素材包；构建和wheel隔离检查。
- [x] 初始两端已退出，备份配置/发现桥接/数据与原安装包，复核停机后安装明确wheel；只配置素材目录。
- [x] 两端发现资源与安装包逐文件一致，冷启动ready；初始无存活旧实例，本轮未执行关闭钩子验收。
- [ ] 真实Bot会话收到新背景与官方图；菜单、账号/玩家、分页、五人详情手机可读，分别记录客户端和服务端证据。
- [x] AstrBot菜单及用户测试的其他指令正常返回图片/图标；用户反馈与脱敏日志分别记录，未逐项确认的专项检查保留。
- [x] 同步文档、脱敏记录和统一离线检查；列出真实未验证项。

## 影响模块与决策
[Renderer](../../../packages/dota2forge-renderer/)、[Dota2UID](../../../adapters/Dota2UID/)、[AstrBot](../../../adapters/astrbot_plugin_dota2forge/)；延续[本地素材决策](../../notes/implemented/2026-10-04-local-dota-illustrations.md)和[停机安装决策](../../notes/implemented/2026-10-02-gscore-wheel-recovery.md)。

## 验证证据
背景任务已完成，1144项禁网测试及Ruff/mypy/覆盖率检查通过；[生成与QA](../../artifacts/dota-style-v2/README.md)保留。本轮四包构建和隔离wheel检查通过，六份安装包与双端桥接逐文件匹配；各复制543张可用图，原配置仅新增illustration_path，启动前数据库指纹不变。实际安装Renderer均加载背景并生成780×1450菜单；冷启动新日志两端ready/image，监听8765/6185/6199。详见[部署证据](../../artifacts/dota-style-host-v2/README.md)。不存真实聊天截图、身份、凭据或业务数据。

## 阻塞与下一步
用户已确认AstrBot /dota菜单及所测其他指令图片/图标正常。基线后日志仅保留静态命令名dota帮助/战绩/玩家与错误标记摘要，OneBot反向WS连接已建立，未见插件渲染/配置错误。统一入口本轮1144项测试及Ruff/mypy/覆盖率均通过；初次文档预算失败与修正后通过日志保留。

GsCore已部署ready，但既有AstrBot GsCore桥接关闭，本轮未改变开关；8765无连接或真实Dota命令，聊天仍未验收。分页、五人详情及手机可读性未获本轮逐项反馈。为这些未验证项保留active任务，部署与AstrBot已确认结果不受影响；不把历史验收或独立菜单PNG算作本轮真实聊天结果。

10-05随后完成[段位/金币图标](../done/2026-10-05-official-rank-icons.md)实现与双端部署，两端资源关闭及新安装Renderer/冷启动ready验证通过，原配置/安装期间数据库/543张素材保留，OneBot重新连接。1195项统一禁网检查通过，新的/dota玩家徽章客户端反馈仍待用户确认；后续从[段位部署记录](../../artifacts/rank-icons-v1/README.md)核对，不重复下载或覆盖原素材。

随后用户提供五张图，仅无身份信息的完整AstrBot主宰出装卡进入README，并检查780/390px展示可读；[筛选与分发](../done/2026-10-05-plugin-screenshots.md)。其他图为旧dota版本或含身份信息，不算现行do/MMR验收，未进入仓库。分页/五人详情、真实客户端手机可读性及GsCore实测仍待补，保持active。

10-05 GsCore另轮部署匹配0.1.0a2运行库、do桥接/README/ICON并冷启动ready/image，配置/两库/558素材保持；[证据](../../artifacts/gscore-current-deployment-v1/README.md)。既有GsCore桥接仍关，本轮无客户端连接，真实聊天与视觉验收继续留在本任务。
