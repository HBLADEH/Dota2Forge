# Dota2UID 原生后台参数与配置来源

Category: architecture
Related task: [后台配置任务](../../tasks/done/2026-10-09-dota2uid-webconsole-config.md)
Related code: [配置](../../../adapters/Dota2UID/src/Dota2UID/config.py)、[管理桥接](../../../adapters/Dota2UID/src/Dota2UID/bundled_host_entry.py.template)
Related docs: [后台配置](../../../docs/cookbook/gscore-configuration.md)

## Problem
现行随包 a6 已部署，但 Token 只从 TOML 读取，GsCore 插件参数页为空。配置应由现有后台管理，同时保持核心缺失时的管理入口、身份分区和客户端关闭边界。

## Decision
在发现目录内使用 GsCore StringConfig 与已有参数控件；不修改宿主源码。凭据使用 secret 字段，平台映射由 JSON 字符串控件呈现。首次原生 JSON 不存在时导入旧 TOML，补兼容默认值并保留原文件；原生 JSON 存在后为唯一运行配置来源，空 Token 不回退到旧凭据。

配置桥接只依赖标准库与 SDK，早于项目运行库注册。读取已有文件先严格检查，避免宿主修复逻辑静默重置错误配置。映射进入现有业务校验器，数据目录、数据库与相对素材路径规则保持。Runtime 注入配置读取器，只在新实例启动读取快照；不将宿主 SDK 引入 Core。

后台保存不切换活跃客户端、身份或调度，必须先停用再重载；运行库升级仍冷启动。SDK 的批量保存逐项执行，不提供整组事务；本插件字段校验拒绝非法写入，启动继续做完整校验。secret 只影响控件显示，原生管理 API 与本地文件保持宿主原有凭据访问语义。

实际SDK响应追踪对配置 value/default 未脱敏，合成验收在归档中复现泄露。插件仅在 Dota2UID detail/config 路由外包装原生 trace 节点，目标请求调用其内层，其他请求仍调用原 trace；不改 SDK 源文件或类方法、请求、响应、鉴权及其它中间件。冷启动与已有 ASGI stack 均幂等安装，停用不解除保护。

## Alternatives considered
继续手工 TOML 无法满足后台操作。双向同步 TOML/JSON 会产生来源漂移及额外写入风险。新增自有页面或修改宿主框架扩大维护边界。运行中刷新会改变请求、调度与身份分区。另比较自有掩码 GET 路由：需要覆盖原生动态路由优先级与所有别名，改变管理 API 响应；专用 trace gate 保留现有参数 UI 契约。

## Consequences
升级后修改保留的旧 TOML 不再改变后台配置；回退 a6 须核对旧 TOML 是否符合当前需求。后台仍受宿主管理员鉴权和文件权限保护，密码控件不等同加密存储。新桥接必须配套新 Dota2UID wheel，不能只更新根入口而混用 a6。

## Verification
实现与a7发行部署完成；配置/trace113定向检查、SDK-free构建与双端分发通过，统一禁网1930通过/274.38s，总覆盖93.01%。真实87c SDK验证原生配置/鉴权、冷热stack、停用重载、绑定保留及全部归档canary；原7f同trace类另经隔离验证。18文件/11资产匿名校验、私有恢复与现行备份冷启通过。

宿主随后按原03:40更新/04:40重启配置升到fb/0.11.1/Pillow12.3；原基线失败保留，精确当前审计通过，没有改SDK源码或该设置。新fb源码隔离保存/重载及真实归档canary通过，使用继承SDK元数据0.11.0/Pillow11.3，不能称生产同构；[证据](../../artifacts/dota2uid-webconsole-config-v1/README.md)区分范围。真实后台点击、有效Token与QQ联调仍待验收。
