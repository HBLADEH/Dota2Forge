# GsCore 随包运行库契约

随包 a7 已公开并部署，新增后台配置；[薄分发](plugin-distribution.md)保留旧安装路径。业务仍维护于共享 wheel，平台 SDK 只进入宿主桥接；[验收](../../.agents/artifacts/dota2uid-webconsole-config-v1/README.md)区分发行、隔离SDK、生产与宿主自更新。

## 分发与准备

生成器的 `--gscore-bundled` 要求四个匹配的标准项目 wheel，按 SHA256、Name/Version/Python、纯 Python 标签、解压限额、文件路径与跨包碰撞校验。运行库含字体/OFL许可，禁止 SDK、原生库、游戏 PNG、配置和数据库；复制完整 wheel 并记录来源摘要，不维护第二份业务源码。deployment.json 固定随包模式及 runtime-wheels.json 摘要，不改变薄模式清单。根 pyproject 仅声明宿主共享的 HTTPX/Pillow，不对项目包执行全局 pip。

标准库/SDK 管理入口先注册 `do安装核心`、`do核心状态` 和帮助菜单 fallback。安装 handler 复核主人权限且拒绝参数；启动只用本地 wheel，恢复命令才允许固定仓库/版本的 Release URL。带文件锁的准备任务验证依赖与离线子进程导入/字体渲染，原子发布 data/Dota2UID/runtime 内不可变代际；失败或关闭保留旧指针、配置与绑定。共享第三方不兼容时保留管理入口并要求维护。

## 加载与生命周期

a7 管理入口在项目包可用前注册宿主原生插件参数。首次将旧 TOML 导入 data/Dota2UID/config.json，原文件保留；JSON 存在后单一读取，不回退旧 Token。配置映射经共享的适配器校验器进入 Runtime，只在启动读取快照。后台保存后停用再重载，不自动改变活跃客户端或调度；参数、凭据访问语义及回退见[后台配置](../cookbook/gscore-configuration.md)。Core 不引入 SDK，薄入口和本地桥接安装器同样携带配置模块。

公开a6–a9仅允许干净启动加载四组件，拒绝来源不符的已加载模块；运行库更新仍冷启动。本地a10/Core a7已实现protocol=1的受控热切换，未发布：deployment.json固定桥接摘要与存储兼容标识，入口冻结清单/源码/纯值配置，管理owner与串行锁跨原生reload保留。Core SQLite取消等待线程结束；Runtime排空查询、排队发送、订阅、素材及绘图任务后，才整组移除自己独占旧代际四包并导入新包。30秒关闭超时不换模块，保留旧关闭任务并要求重启。

私有目录的源码加载器忽略未验证的 pyc，并禁止向不可变代际写入字节码缓存；其他宿主路径继续使用原加载器与缓存设置。文件完整性不因正常导入变化，同代际可重用。

热切换检查唯一owner租约、模块来源、可见外部消费者、wheel内schema及兼容标识；任意外部闭包/容器引用不能全面枚举，支持契约要求项目包由Dota2UID独占。current.json是准备指针；active.json仅在ready/awaiting_config启用后记录运行版本。状态区分期望/准备/活跃版本与switching/retained/rolled_back；宿主reload返回不等于业务ready。恢复命令只准备，再原生重载。准备失败恢复旧SV/调度；新业务失败先关闭，数据schema/摘要不变才重建旧Runtime，否则诊断并要求冷启动。

旧a6–a9首次升级a10需一次冷启动；之后兼容bundled更新可重载，AutoReloadPlugins开启时更新自动触发。薄模式、第三方/Python/SDK升级、未知来源与数据迁移仍冷启动。卸载前停用，不把删目录等同资源关闭。[实施决策](../../.agents/notes/implemented/2026-10-10-dota2uid-hot-update.md)、[SDK隔离证据](../../.agents/artifacts/dota2uid-hot-update-v1/README.md)和[操作指南](../cookbook/gscore-bundled-install.md)区分本地a10与已公开a9；Linux/Docker和真实商店/QQ热更新未验收。
