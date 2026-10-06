# 双端薄桥接候选与首次配置状态

Category: architecture
Related task: [发行阶段一](../../tasks/done/2026-10-05-plugin-distribution-stage1.md)
Related code: [分发生成器](../../../scripts/build_plugin_distributions.py)、[版本检查](../../../scripts/plugin_bootstrap.py)
Related docs: [发行步骤](../../../docs/cookbook/plugin-release.md)

## Problem

用户授权按分发建议逐步推进。开发workspace根不被商店直接发现，手动桥接要求预装wheel；两端缺Token被当作初始化失败。GsCore仅自动安装开启时会跳过已有依赖的新版约束，桥接更新可能配旧库。本机已有大量其他源码/资源修改，不能用同一个0.1.0a1标识新的发行快照。

## Decision

沿用[分发建议](../proposed/2026-10-05-plugin-store-readiness.md)，先实现本地候选，不改变共享业务边界。四包及workspace升到0.1.0a2，最低依赖、锁文件、宿主模板和自动参考同步；不修改policy、CI或治理脚本。

显式生成两端根发现目录、锁定三项目库的清单、许可/README、配置示例、校验与索引草稿。目标仓库参数必须是对应名称的HTTPS GitHub仓库，参数不创建远端；GsCore默认main需与未来仓库默认分支一致。商店入口只引用对应适配器和共享包，不包含另一个适配器、不复制业务源码。第三方约束从当前包元数据提取，漂移时拒绝生成。

采用标准库版本guard，先检查Python>=3.12和release.json，再比较Core/Renderer/适配器发行版本，失败阻止SDK注册及资源创建。GsCore独立宿主pyproject生成gscore_auto_update_dep，兼容既有总开关；仍要求停机更新运行库。手动安装器保留原用途，商店guard只附加到生成的分发入口。

两端新增ConfigurationPending及awaiting_config。仅其他字段合法而Token为空时等待；空白/非法Token、结构/路径/存储错误仍失败。GsCore显式Runtime启动独占创建完整空配置，已有配置不覆盖；load_config单独调用仍不默默写默认值。等待期间不创建客户端/数据库/业务调度。配置填写后经停用/重载的新实例恢复，保留既有关闭/权限/身份语义。

输出按固定顺序/时间戳压缩并检查大小，完整暂存后就位；相同内容重建无写入，变更/缺项/额外内容拒绝覆盖。原始Valve美术/生成背景仍在可选外部素材目录，未配置时占位出图。README明确这是候选和有限已实现能力，不宣传未完成实测的订阅。

## Alternatives considered

- 直接上传主仓或adapters链接：宿主不执行workspace与安装器，保持拒绝。
- 本阶段自动携带Core/Renderer源码：会引入额外命名空间/重载和资源问题；先复用已有wheel边界，公开依赖取得是下一阶段条件。
- 缺Token放宽全部配置校验：会隐藏非法配置，采用单独待配置异常且其他校验优先。
- 命令自动轮询配置并重新初始化：会改变凭据和调度生命周期，选择明确重载。
- 已有依赖不满足但继续加载：可能造成契约混用，生成清单配合早期版本检查，冷启动仍必需。

## Consequences

新增发行脚本与元数据，不拆开发仓库。薄桥接本身很小，Renderer字体仍在wheel；商店真正安装依赖公开可取得的包。标准版本guard不验证旧进程模块内容或代码签名，不能替代关闭/重启；原生GsCore卸载资源释放保证不因此扩大。

新状态属于适配器生命周期契约，两个消费者均覆盖；公共Core/Renderer接口未改变。0.1.0a2为候选，真实平台、公开包索引和商店验证必须分别记录。

## Verification

44项发行/首配/双端桥接桩测试通过；最终统一入口退出0，Ruff、mypy71文件和1372项禁网测试通过，综合覆盖率93.28%，scripts96%/Core93%门槛通过。四包sdist/wheel构建、四个无SDK安装/导入环境及两个候选清单的干净离线安装通过；首次配置、新实例恢复、绑定持久化和关闭通过。

首次smoke创建两份bootstrap缓存，重复生成明确失败；加入-B并只清理本任务缓存，复验两端安装/原样重建通过。GsCore ZIP5497 bytes、AstrBot ZIP6960 bytes，资源未塞入桥接。SHA256和完整门禁见[证据](../../artifacts/plugin-distribution-stage1-v1/README.md)。本机只更新workspace环境；公开包可达、真实a2宿主/升级/卸载/跨平台及商店未验收。
