# Dota2UID 后台插件参数配置

Status: active

## 目标
按用户要求将 STRATZ Token 与 Dota2UID 配置接入 GsCore 现有插件参数配置页，兼容既有 TOML，保持宿主源码与 Core 边界。

## 非目标
不修改 GsCore 配置框架、不发送真实消息、不把后台保存等同运行中自动切换，不解除现有停用与冷启动约束。

## 验收
- [x] 核心未就绪时仍注册后台参数，覆盖凭据、命名空间、回复、素材、订阅与平台映射。
- [x] 旧配置兼容、来源优先级明确；非法配置显式失败，Token 不进入日志和聊天。
- [x] 后台保存后按停用/重载流程读取新值；配置项说明与操作指南一致。
- [x] 统一离线检查、分发构建与实际 SDK 隔离配置保存/加载验证。
- [ ] 沿用此前发布部署授权，公开新版本并备份/冷启动现行服务，记录未验证的真实点击和聊天。

## 影响模块与决策
[GsCore 桥接](../../../adapters/Dota2UID/src/Dota2UID/bundled_host_entry.py.template)、[配置](../../../adapters/Dota2UID/src/Dota2UID/config.py)、[发行生成器](../../../scripts/build_plugin_distributions.py)。原随包部署已完成，见[安装指南](../../../docs/cookbook/gscore-bundled-install.md)；新配置与隐私[决策](../../notes/implemented/2026-10-09-dota2uid-webconsole-config.md)。

## 验证证据
2026-10-09 开工时工作区干净。最终统一1930通过/274.38s，Ruff359、mypy83，总覆盖93.01%，三组覆盖scripts94/Core93/Assets92。五包构建、最终v3 wheel/双端 SDK-free smoke、配置与trace113定向项通过；Windows/Linux类型检查通过。

最终 v3 候选真实87c SDK四阶段验证原生配置/鉴权、旧TOML保留、保存快照、停用重载、绑定跨进程及日志归档无Token，原SDK639源码与Pillow摘要保持；SDK使用隔离副本及既有解释器。现行7f相同trace类另经stubcollector验证，[证据](../../artifacts/dota2uid-webconsole-config-v1/README.md)。初始只核对stdout遗漏原生HTTPTrace凭据预览，补查后修复并增加完整归档扫描；未降低断言或门槛。

## 阻塞与下一步
实现、验证并同步文档；真实后台点击与聊天验证须区别于离线和隔离 SDK 验证。
