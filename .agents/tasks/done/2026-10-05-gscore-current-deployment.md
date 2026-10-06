# GsCore 现行功能本机部署

Status: done

## 目标
用户授权着手适配GsCore部署：将当前do指令、预估MMR、英雄出装、README和主宰图标部署到本机Dota2UID，确认实际宿主就绪，并给后续截图提供入口。

## 非目标
不发布商店/远端，不修改凭据、绑定、订阅或平台权限，不发送测试聊天。AstrBot已有独立插件与关闭的GsCore桥接保持原状态；如需切换聊天路由另明确方案。保留工作区与宿主其他插件。

## 验收
- [x] 核实宿主版本/进程/入口、现有安装内容、配置/数据库/素材与传输状态。
- [x] 核实原宿主已停止，备份专用文件和原安装包，离线安装同次三个匹配wheel。
- [x] 更新发现桥接、README、ICON.png；核对运行库、配置和数据/素材保持。
- [x] 实际GsCore SDK验证命令/正则和渲染；冷启动ready/image，区分传输与聊天验收。
- [x] 同步部署事实和截图边界，统一离线检查通过。

## 影响模块与决策
[Dota2UID](../../../adapters/Dota2UID/)、[本机接入](../../../docs/cookbook/dota2uid.md)、[宿主契约](../../../docs/subsystems/gscore-host.md)。[本轮决策](../../notes/implemented/2026-10-05-gscore-current-deployment.md)延续停机备份/离线安装，不修改宿主框架或AstrBot路由。

## 验证证据
开工保留既有修改。原0.1.0a1已升级同次Core/Renderer/Dota2UID 0.1.0a2，35/15/11安装文件与wheel一致，发现入口匹配模板，README与主宰ICON同步。Python3.13.2，宿主发行元数据0.11.0与模块常量0.10.7分列。原宿主已退出，本轮未执行真实关闭钩子。

[本轮证据](../../artifacts/gscore-current-deployment-v1/README.md)：实际SDK的16查询/订阅命令、1管理员命令、英雄名正则/桥接通过；隔离合成数据验证两次初始化/停用、单个调度job移除、客户端关闭。安装环境菜单780×1450、含MMR玩家780×960、四阶段出装780×1530生成并查看；无外部网络或测试聊天。

冷启动观察两条ready/job_registered静态日志，控制台200、匿名状态401；实际查询pm6、管理员pm0、查询启用且无需额外前缀。配置/绑定和订阅库/558素材及AstrBot配置指纹保持；原订阅true、image保留。宿主Git只保留既有.playwright未跟踪项。

统一入口uv run --locked python scripts/check_governance.py --all通过：269文件格式、Ruff、mypy71文件、1376项禁网测试（227.33s），治理工具覆盖率96%、Core93%。初两次仅接入文档字数预算失败，修正重复说明后完整通过；[最终日志](../../artifacts/gscore-current-deployment-v1/offline-checks-final.log)及失败日志均保留。

## 阻塞与下一步
部署完成并保持运行。只读核实AstrBot独立插件开、GsCore适配器关，本轮未观察到客户端连接。未验证当前管理员状态接口、do/MMR/出装真实聊天、GsCore截图、推送和其他平台。后续明确聊天入口避免重复回复，再按[截图清单](../../../docs/cookbook/plugin-showcase.md)采集；真实聊天/视觉继续在[宿主任务](../active/2026-10-05-dota-style-host-deployment.md)跟踪，不用AstrBot图或合成卡替代。
