# GsCore现行功能部署证据

2026-10-05用户授权适配本机GsCore部署。本目录仅记录非敏感摘要；凭据、数据库、私有日志及原始配置备份留在宿主，未进入仓库。

## 安装与保留
- 宿主D:/bot/gsuid_core，Python3.13.2，源码HEAD 87c06f11ae10c12b3bb8e76b3c6f420c831282a8；发行元数据0.11.0，SDK模块常量0.10.7。未更新GsCore框架。
- 原进程已停止、8765未监听；先备份后离线重装同次Core、Renderer、Dota2UID 0.1.0a2 wheel，明确路径并禁用旧缓存，不更改Pillow12.3.0/HTTPX0.28.1。
- 安装模块分别35/15/11文件与wheel字节一致。发现入口采用同次包内模板，README/ICON/LICENSE同步；主宰ICON哈希见[摘要](deployment.json)。
- 备份位于D:/bot/gsuid_core/data/Dota2UID/backups/current-do-v1-20261005-231445。配置、绑定/订阅库及558素材启动前后指纹均保持，原订阅开关true、回复模式image保留。

## SDK与宿主
[隔离SDK结果](sdk-validation.json)使用实际SV/Event/Trigger/APScheduler、合成配置和FIXTURE业务数据，禁止外部网络及消息发送。16查询/订阅命令、1管理命令、英雄名正则与桥接、双次初始化/停用、单个job注册/移除和客户端关闭均通过。检查中的宿主钩子注册及HTTP组合隔离，不能证明实际Web管理或平台递送。

实际已安装Renderer生成菜单780×1450、玩家780×960、出装780×1530；玩家显示传奇1星3080–3233估算及非精确提示，出装含四阶段和FIXTURE标识，已视觉查看。样图留在宿主validation-current-do-v1，不作为README实机图。

宿主随后隐藏窗口冷启动，观察两条静态Dota2UID initialized state=ready subscriptions_enabled=True job_registered=True；控制台HTTP200，匿名插件状态HTTP401。[启动与保留摘要](deployment.json)记录真实状态。本轮原宿主已退出，未执行真实关闭钩子；旧生命周期验收另见[历史记录](../gscore-image-lifecycle-v1/README.md)。

## 边界与接续
未观察到客户端连接/真实聊天。只读核实AstrBot独立插件启用、GsCore适配器关闭，其配置指纹保持；后续须明确聊天入口，避免两个插件同时处理do指令。新MMR/出装的GsCore聊天截图、管理员状态接口、真实订阅推送和其他平台尚未验证；[截图清单](../../../docs/cookbook/plugin-showcase.md)继续跟踪，未采用AstrBot图片充当GsCore证明。

[构建](build.log)、[离线安装](install.log)成功；[统一检查](offline-checks-final.log)全部通过：269文件格式、Ruff、mypy71文件、1376禁网测试/227.33s、治理工具覆盖率96%及Core93%。[首检](offline-checks.log)与[第一次修订](offline-checks-retry.log)因接入文档字数预算失败，压缩重复说明后通过。[任务](../../tasks/done/2026-10-05-gscore-current-deployment.md)已完成；真实聊天/视觉任务保持active。
