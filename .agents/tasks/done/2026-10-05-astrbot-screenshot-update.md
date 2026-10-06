# AstrBot 截图前本机更新

Status: done

## 目标
用户授权先更新本机 AstrBot 插件，之后由用户截图。部署现行 do 命令、预估 MMR、英雄热门出装以及 README / 主宰图标，确认宿主重新加载后就绪。

## 非目标
不更新 GsCore、不发布商店或远端，不代替用户发送聊天或截图；不修改凭据、账号绑定、订阅开关或其他插件配置。保留已有工作区修改。

## 验收
- [x] 核实 AstrBot 宿主 / 运行根、版本、安装包、配置及现有素材。
- [x] 备份专用配置、数据库、发现桥接和原安装包；关闭插件并停机更新共享库。
- [x] 离线安装同次构建的三个匹配 wheel；同步当前桥接、说明及 logo.png。
- [x] 核对安装内容、配置 / 数据 / 素材保留，冷启动后插件 ready / image，OneBot 连接恢复。
- [x] 记录真实验证与待用户截图项，运行统一离线检查。

## 影响模块与决策
[AstrBot 接入](../../../docs/cookbook/astrbot.md)、[截图清单](../../../docs/cookbook/plugin-showcase.md)、[插件说明](../../../adapters/astrbot_plugin_dota2forge/README.md)。延续[停机部署](../../notes/implemented/2026-10-05-local-illustration-deployment.md)、[平台接入](../../notes/implemented/2026-10-02-astrbot-platform.md)与[说明 / 图标](../../notes/implemented/2026-10-05-plugin-readmes-icon.md)。

## 验证证据
开工保留既有工作区修改。本轮同次构建四包，仅向AstrBot离线安装三个0.1.0a2 wheel；模块35/15/14个文件逐一核对。AstrBot4.28.2 / 自带Python3.12.12 SDK注册18个静态do命令，GreedyStr及动态/do主宰出装捕获正常；临时根目录中重复初始化/关闭，client_closed，菜单/MMR玩家/出装合成PNG分别780×1450、780×960、780×1530，目视无裁切。

桌面实见0.1.0a2、主宰logo与已打开；日志ready/image、OneBot已连接。配置字节、绑定/订阅数据库行及558张素材保持；全局配置语义恢复原状态。[完整摘要](../../artifacts/astrbot-screenshot-update-v1/README.md)。未发送测试聊天；新入口/MMR/出装真实聊天与手机可读性待用户截图，不冒充离线验收。

`uv run --locked python scripts/check_governance.py --all`退出0：治理、Ruff格式/lint、mypy71文件通过，1374测试通过（220.73秒），整体覆盖93.30%，治理工具96%、Core93%。部署文件以本轮构建内容核对，未发布商店或远端。

## 阻塞与下一步
部署已就绪，无部署阻塞。用户按截图清单采集真实图片；GsCore本轮未更新。原数据目录两个停机备份保留，不入Git。完整平台实测另由接入任务跟踪。
