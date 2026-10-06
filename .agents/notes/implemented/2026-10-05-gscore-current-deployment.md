# GsCore现行功能停机部署

Category: operations
Related task: [本机部署](../../tasks/done/2026-10-05-gscore-current-deployment.md)
Related code: [发现桥接](../../../adapters/Dota2UID/src/Dota2UID/host_entry.py.template)
Related docs: [本机接入](../../../docs/cookbook/dota2uid.md)、[宿主基线](../../../docs/subsystems/gscore-host.md)

## Problem
用户要求适配GsCore部署。原本机插件为0.1.0a1，do前缀、MMR和英雄出装尚未进入该宿主；AstrBot已升级，不能用其聊天结果证明GsCore。

## Decision
延续[停机恢复](2026-10-02-gscore-wheel-recovery.md)。核实GsCore原已退出/8765未监听后备份插件安装目录、发现入口、配置与两库；同次构建并用明确路径、offline/no-index/no-deps/no-cache离线重装三个匹配0.1.0a2 wheel。更新包内发现模板、独立README、LICENSE和主宰ICON；逐文件匹配wheel，配置/数据库/558素材指纹核对后冷启动。

保持现有手动wheel安装方式，宿主使用自己的虚拟环境直接启动gsuid_core.core，避免uv同步改变依赖。Pillow12.3.0/HTTPX0.28.1保留，不修改SDK源码。原订阅开关保留为true；未新增订阅或发送测试聊天。AstrBot原配置保持，独立Dota2Forge启用、GsCore适配器关闭，不自动切换入口。

## Alternatives considered
- 只更新桥接或Renderer：共享Core/Renderer类及新命令消费可能不一致；拒绝。
- 热重载旧进程：旧共享模块可能常驻，过去已发生类型不匹配；采用冷启动。
- 直接套用商店ZIP及自动依赖流程：未公开发行，本次手动部署不验证商店guard；保留既有安装方式。
- 同时开启AstrBot两插件：do指令存在冲突，本次保留路由，聊天联调另明确入口。

## Consequences
私有备份留在宿主data/Dota2UID/backups，仓库只留静态命令、状态和校验布尔值。启动恢复原调度器，不以ready或合成图证明平台递送、真实推送或客户端可读性。原宿主已退出，本轮没有执行真实shutdown钩子；隔离SDK的关闭检查另列。

## Verification
[本轮证据](../../artifacts/gscore-current-deployment-v1/README.md)：安装文件与三个wheel一致；实际SV/Event/Trigger验证16查询/订阅命令、1管理员命令与英雄正则。无外部网络的合成配置验证初始化/关闭幂等、单一调度job注册/移除、菜单780×1450、玩家780×960含MMR、出装780×1530。生命周期注册和HTTP组合在该检查隔离，真实启动另外观察两条ready/job_registered标记。

宿主发行元数据0.11.0、模块常量0.10.7分别记录；8765控制台200、匿名状态401。启动后配置/两库/558素材与AstrBot配置均保持，尚无客户端连接。统一离线1376测试、Ruff/mypy及独立覆盖门槛通过，不宣称新功能聊天、管理员状态接口、推送或GsCore截图已验收。
