# Core 离线绑定与查询公共契约

Category: architecture
Related task: [Core 最小业务闭环](../../tasks/done/2026-09-30-core-mvp.md)
Related code: [Core](../../../packages/dota2forge-core/src/dota2forge_core/)
Related docs: [Core 契约](../../../docs/subsystems/core.md)

## Problem
M0 仅有包骨架。绑定和查询需要框架无关的公开入口、严格身份隔离和可区分的失败语义；尚无已验证的 STRATZ schema、凭据或宿主环境，不能将合成数据当真实战绩。

## Decision
采用不可变领域值、异步 Protocol 端口、Dota2Service 用例和标准库 SQLite 基础设施，保持 Core 无运行依赖。账号部分与 SteamID64 分型校验，仅接受明确支持的十进制输入。平台身份通过 namespace/platform/bot_id/user_id 联合键隔离；namespace 由适配器部署固定，不接收用户任意选择。

绑定作为查询偏好，不宣称 Steam 所有权。相同绑定幂等，改绑需显式 replace=True，冲突检查与 SQL 写入在同一事务。宿主负责构造可信身份，Core 不接收平台事件或实现宿主认证。

归一化结果保留来源、抓取/观察时间与可缺省版本；None、有效空结果与各类 ProviderError 分离。仅实现有合成 fixture 支撑的公开用例，不添加未经核实的 HTTP Provider、静默 fallback、缓存或重试。

SQLite 专用文件以应用 ID/版本识别，不接管外部库；未知版本和损坏数据失败。每次操作开关连接，经工作线程避免阻塞事件循环；宿主负责目录、文件权限和部署资源管理。

## Alternatives considered
- 仅用 platform/user_id：不足以隔离不同机器人及部署，增加显式 namespace/bot_id。
- 默默覆盖旧绑定：并发请求易丢失用户选择，改为事务冲突与显式替换。
- 直接用同步 sqlite3 调用异步宿主：会阻塞事件循环；选择标准库 to_thread，暂不引入长期连接池或第三方数据库依赖。
- 依据规划猜测 STRATZ 响应：无法验证隐私与空数据含义，先固定端口并隔离合成 fixture。

## Consequences
离线可重放完整账号流程，平台接入只消费公开用例。绑定无需联网，但不能证明目标账号存在或属调用者所有；多个身份可选择相同账号。两个适配器都只有骨架，无已实现的业务消费者可做宿主契约测试。

取消协程不保证线程事务取消；显式改绑遇到不确定结果应先重新读取。数据库暂不含迁移策略、加密或跨进程长连接管理；新增版本必须另作迁移决策。

## Verification
账号边界、归一化缺失值、错误保真、SQLite 重开/隔离/并发/故障及完整用例均有离线测试。实际命令和最终结果记录在关联任务；真实数据源与宿主联调未验证。
