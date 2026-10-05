# AstrBot 截图前停机更新

Category: operations
Related task: [本机更新](../../tasks/done/2026-10-05-astrbot-screenshot-update.md)
Related code: [发现桥接](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host/main.py.template)
Related docs: [AstrBot](../../../docs/cookbook/astrbot.md)、[截图清单](../../../docs/cookbook/plugin-showcase.md)

## Problem
用户要求先更新AstrBot再截图。原运行库和桥接是0.1.0a1，不能用旧dota入口验收现行do、预估MMR与出装；README及主宰图标也未安装到宿主。

## Decision
同次构建四包，仅向本机AstrBot的data/site-packages离线安装Core、Renderer、AstrBot三个0.1.0a2 wheel；不更新GsCore。停用插件确认client_closed=True，退出已核实路径的桌面/后端进程，二次停机备份后安装，保持现有手工桥接方式并同步说明、许可和logo.png。通过桌面插件页重新启用，保留原订阅开关和所有配置。

## Alternatives considered
仅替换桥接或热重载共享库不能保证新类型/资源生效；商店专用入口含依赖引导，与当前手工安装路径不同。本轮采用匹配wheel和模板桥接，避免同时改变安装模式。

## Consequences
有短暂停机。宿主、依赖版本和现有配置不升级；两个备份位于宿主专用数据目录，包含敏感文件，不进入Git。原订阅开关为true，恢复原状态，但不新增订阅或发送测试聊天。新功能图片、上传及手机可读性需用户实测；本机SDK和合成PNG不能替代真实聊天。

## Verification
[证据](../../artifacts/astrbot-screenshot-update-v1/README.md)记录安装内容逐文件一致、配置/数据库/558张素材保留、宿主4.28.2与Python3.12.12的18个静态命令及动态捕获、菜单/MMR/出装合成图，以及冷启动后ready/image、OneBot已连接、桌面新图标和0.1.0a2启用。统一离线检查退出0，Ruff/mypy通过，1374测试通过，治理工具/Core覆盖96%/93%；最终任务归档后的链接与文档治理另复核。
