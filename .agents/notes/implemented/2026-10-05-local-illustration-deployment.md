# 本机独立素材目录与停机更新

Category: operations
Related task: [部署与聊天实测](../../tasks/active/2026-10-05-dota-style-host-deployment.md)
Related code: [共享素材加载](../../../packages/dota2forge-renderer/src/dota2forge_renderer/illustrations.py)
Related docs: [素材配置](../../../docs/cookbook/illustrations.md)

## Problem
背景生成和离线QA已完成，但两端已安装包仍为旧版，配置没有illustration_path。直接引用工作区素材会使运行宿主依赖开发目录；同版本号也不能证明进程或磁盘包已经更新。

## Decision
用户10-05授权部署与聊天实测。初始GsCore/AstrBot均已退出；备份各自配置、数据库、发现桥接和三个已安装包后，分别无索引/无依赖重装明确wheel，更新桥接并冷启动。Pillow/HTTPX保持原版本，不修改凭据、绑定或订阅开关。
将manifest和543张可用PNG分别复制到GsCore data/Dota2UID/illustrations-v2和AstrBot data/plugin_data/astrbot_plugin_dota2forge/illustrations-v2；逐一验证摘要，仅改变配置illustration_path。官方图和生成背景仍为本机独立资源，不进入MIT wheel；缺图条目保留。

## Alternatives considered
引用工作区素材：减少复制，但开发目录变动会影响宿主；本轮使用各自数据目录。
只改配置或热重载：磁盘旧包缺少素材接口，进程模块缓存也可能保留旧类；使用停机明确wheel和冷启动。

## Consequences
两端各维护一份本地素材快照；后续更新须显式同步并重新实例化Renderer。备份只在宿主目录保存，含敏感配置/数据，不进入仓库。当前初始已停机，没有本轮关闭钩子执行证据；不将独立PNG验证记为聊天平台验收。

## Verification
四包构建/四份隔离wheel安装导入通过；六份安装包与两端桥接逐文件匹配。原数据库在启动前指纹不变，配置仅新增illustration_path。两端实际安装Renderer均加载背景并生成780×1450菜单，依赖版本未变；冷启动新日志均ready/image。用户确认AstrBot菜单及所测其他指令图片/图标正常；OneBot连接已建立，新增日志未见插件渲染/配置错误。GsCore桥接维持既有关闭状态，未做真实聊天验收；分页/五人详情/手机可读性也未获本轮逐项反馈。1144项禁网测试和统一静态/覆盖率检查通过；[证据](../../artifacts/dota-style-host-v2/README.md)分别记录。
