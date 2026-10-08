# Dota2UID a6 随包发行与部署

Status: active

## 目标
用户授权整理发布部署：将[已实现随包方案](../done/2026-10-08-dota2uid-bundled-bootstrap.md)发布到 HBLADEH/Dota2UID，并在确认的现行 GsCore 实例备份、部署及验证；不修改 GsCore 原逻辑。

## 非目标
不发布 AstrBot a8，不改聊天路由、凭据、身份或订阅归属，不发送真实消息，不覆盖旧发行资产，不合并需维护者评审的治理变更。

## 验收
- [ ] 匹配四 wheel、许可证、分发清单与摘要，来源提交可审查；旧 a4 资产保留。
- [ ] 分发 main 与 a6 Release 一致，匿名下载、缺 wheel 的真实公开恢复与冷启动验证。
- [ ] 确认现行宿主目标；停用/停止、专用备份、部署、冷启动与数据/素材保留证据。
- [ ] 管理状态及业务 ready/awaiting_config、客户端关闭与权限边界明确；真实 QQ 验收不冒充完成。
- [ ] 源码/文档/任务整理与必要检查，公开链接和当前部署事实同步。

## 决策与范围
[生成器](../../../scripts/build_plugin_distributions.py)、[安装契约](../../../docs/subsystems/gscore-bundled-runtime.md)。共享 Core/Renderer a4 wheel 与旧发行逐字节相同，Assets a1 与 Dota2UID a6 首次公开；恢复 URL 固定 v0.1.0a6，四 wheel 均须在此 Release 提供。保留全局旧项目包，冷进程只加载匹配私有模块。

## 开工证据
已保留大量既有 workspace 修改，统一检查1740项已通过。GitHub已登录发布账号，Dota2UID main仍a4，a6未存在。原本机宿主 D:/bot/gsuid_core 已停止；8765由SSH转发监听，不能当作本机宿主，部署目标正在只读核查并向用户询问。

## 接续
独立发行审查、宿主只读预检、公开恢复验证已并行分配；根代理负责外部发布和生产变更。[证据目录](../../artifacts/dota2uid-bundled-release-v1/README.md)将记录结果与未验证项。
