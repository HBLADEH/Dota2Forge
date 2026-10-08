# GsCore 随包运行库契约

本契约为 Dota2UID 0.1.0a6 源码候选，尚未发布；[薄分发](plugin-distribution.md)保留公开 a4 路径。业务仍维护于共享 wheel，平台 SDK 只进入宿主桥接。

## 分发与准备

生成器的 `--gscore-bundled` 要求四个匹配的标准项目 wheel，按 SHA256、Name/Version/Python、纯 Python 标签、解压限额、文件路径与跨包碰撞校验。运行库含字体/OFL许可，禁止 SDK、原生库、游戏 PNG、配置和数据库；复制完整 wheel 并记录来源摘要，不维护第二份业务源码。deployment.json 固定随包模式及 runtime-wheels.json 摘要，不改变薄模式清单。根 pyproject 仅声明宿主共享的 HTTPX/Pillow，不对项目包执行全局 pip。

标准库/SDK 管理入口先注册 `do安装核心`、`do核心状态` 和帮助菜单 fallback。安装 handler 复核主人权限且拒绝参数；启动只用本地 wheel，恢复命令才允许固定仓库/版本的 Release URL。带文件锁的准备任务验证依赖与离线子进程导入/字体渲染，原子发布 data/Dota2UID/runtime 内不可变代际；失败或关闭保留旧指针、配置与绑定。共享第三方不兼容时保留管理入口并要求维护。

## 加载与生命周期

干净启动从私有路径加载四组件，拒绝来源不符的已加载项目模块；不清理 sys.modules 强行切换。运行中恢复只准备目录，激活需完整冷启动。bootstrap 拥有生命周期与业务注册，失败或取消仅回滚业务 SV 并关闭业务资源。启动、准备和关闭均使用插件自己拥有的任务，关闭等待这些任务退出。

私有目录的源码加载器忽略未验证的 pyc，并禁止向不可变代际写入字节码缓存；其他宿主路径继续使用原加载器与缓存设置。文件完整性不因正常导入变化，同代际可重用。

完成显式停用后同代际配置重载可用；活跃重载保留旧实例，管理指令要求重启。原生宿主卸载前必须停用，不推断其删除目录等同关闭客户端。[操作指南](../cookbook/gscore-bundled-install.md)明确源码候选与公开 a4 的边界；[实施任务](../../.agents/tasks/done/2026-10-08-dota2uid-bundled-bootstrap.md)记录真实检查和联调未验证项。
