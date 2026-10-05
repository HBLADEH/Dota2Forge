# AstrBot 截图前更新证据

2026-10-05，用户授权先更新本机AstrBot，再自行截图。仅更新AstrBot，不更新GsCore或发布远端，不发送测试聊天。

- [开工摘要](preflight.json)：原安装三个运行库0.1.0a1；现有配置合法、image模式、Token已配置、订阅开关原为true、558张素材。
- [构建日志](build.log)：同次构建四包0.1.0a2；本机仅安装Core、Renderer、AstrBot三个wheel。
- [部署摘要](deployment.json)：wheel摘要及逐文件核对（35/15/14个模块文件）；桥接来自同次wheel，另同步README、LICENSE和主宰logo.png。
- [宿主SDK](sdk-validation.json)：AstrBot4.28.2 / 自带Python3.12.12，18个静态do命令及动态/do主宰出装捕获，GreedyStr参数，重复初始化/关闭且client_closed；httpx0.28.1、Pillow12.3.0保留。

插件停用后日志确认client_closed=True，停止核实路径的桌面与后端，再备份和离线安装。先前开工时宿主未运行，准备期间启动，故另取停机一致备份。两个备份位于宿主专用data/plugin_data目录；配置、数据库和素材清单指纹留在本机，不复制到仓库。

冷启动后在原桌面插件页启用Dota2Forge，实见0.1.0a2及主宰图标。只抽取固定生命周期/连接日志标志：ready/image、initialized ready、OneBot已连接，无已知初始化/类型错误；6185/6199监听。配置字节保持、宿主全局配置语义与初始状态一致，绑定与订阅数据库各表行保持，558张素材与清单摘要保持。

本机SDK验证使用临时ASTRBOT_ROOT、合成Token和FIXTURE数据，不接触真实绑定或发送平台消息。合成PNG在宿主专用validation-screenshot-update-v1目录：菜单780×1450、MMR玩家卡780×960、四阶段出装卡780×1530；仅证明本机渲染可解码，不作为README实机截图。

[统一离线检查](check-governance.log)退出0：治理、Ruff格式/lint、mypy71文件通过，1374测试通过（220.73秒），整体覆盖93.30%，治理工具96%、Core93%。新do入口、MMR与出装的真实聊天、图片上传和手机可读性待用户按[截图清单](../../../docs/cookbook/plugin-showcase.md)验证；旧基础查询验收不冒充新功能验收。
