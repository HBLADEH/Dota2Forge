# Dota2UID 商店更新后应用新改动的可行性调研

Status: done

## 目标
阅读项目契约、有效决策及 GsCore 加载器，解释商店更新后重载不能应用新运行库的原因，比较无需宿主冷启动的可行方案与实施边界。

## 非目标
本轮不实现热更新、不发布版本、不修改或重启生产宿主，不进行真实聊天发送。

## 验收
- 将磁盘更新、项目模块缓存、旧资源关闭与业务就绪分别说明，并给出源码证据。
- 比较受控同进程切换、插件命名空间隔离与独立进程方案，明确建议和需要冷启动的情况。
- 记录实际只读核查、隔离实验和离线检查；未实施方案只进入 proposed。

## 影响模块与决策
[随包契约](../../../docs/subsystems/gscore-bundled-runtime.md)、[既有决策](../../notes/implemented/2026-10-08-dota2uid-bundled-bootstrap.md)、[管理入口](../../../adapters/Dota2UID/src/Dota2UID/bundled_host_entry.py.template)、[私有加载器](../../../scripts/gscore_bundled_runtime.py)、[调研提案](../../notes/proposed/2026-10-09-dota2uid-hot-update.md)。

## 验证证据
开始时工作区已有两个未跟踪的商店 PR 任务记录，保留。本机 GsCore checkout HEAD 为 87c06f11ae10c12b3bb8e76b3c6f420c831282a8，仅做只读源码核查；不是现行 Linux/Docker 0.11.1 的完整实机证明。

只读 GitHub API 核对已记录部署提交 fb80b874533c23b565a74ebd8549ce09e4742a55：reload_plugin.py 与 _plugins.py 字节等于本机；server.py 不同，另读目标提交的发现/加载相关逻辑。

CPython3.12.9/uv --locked --offline 的 SDK-free 临时进程使用本地 a6/a7 wheel 复现 module_conflict。新路径前置仍导入旧模块；实验中移除59个项目模块后，新59模块均来自新代际，字体菜单 PNG 各174035 bytes；旧 AccountId 对象与新类型不兼容。没有活跃 Runtime、真实配置/数据库或聊天。初次实验的禁网 hook 阻止了 Windows asyncio 内部 loopback 创建；修正为先创建单个事件循环再启用 hook，两次隔离实验退出0，后端 probe 保持禁网。

另一临时禁网 Runtime 实验退出0：发送回调取消后等待清理时，close 返回 stopped/client_closed=true，dispatch_count 仍1；释放回调后归0。未连接 SDK/聊天，使用合成配置、Token 和临时库。

追加本地公开 a7→a9 四 wheel 的禁网隔离导入实验退出0，Core a4→a6/Renderer a4→a5/Dota2UID a7→a9，正常激活仍拒绝 module_conflict；完整移除旧59模块后新60模块均来自新代际，菜单PNG/字体成功。只验证导入机制，无活跃Runtime。

首轮统一入口治理/Ruff/mypy通过，pytest为1979 passed/6 failed（500.88s），全部为开发.venv旧项目元数据与源码版本不符；覆盖率92.61%，统一入口因此未执行独立报告。按开发指南离线同步全部workspace包后，两端桥接/包版本12项均通过；该局部pytest仍因全局覆盖率31.86%退出1，未降低门槛。

2026-10-10最终 `uv run --locked --offline python scripts/check_governance.py --all` 退出0：1985 passed/498.27s；Ruff格式380文件、lint、mypy85源文件均通过，总覆盖92.61%；scripts94/Core93/Assets92独立80%门槛通过。文档补记与归档后另核查治理/链接及git diff --check。

## 阻塞与下一步
调研已完成，推荐 bundled 独占四包受控切换；完整请求排空/消费者归属/失败恢复需实施。本轮未实现/发布/部署热切换；实际 Windows/Linux/Docker 更新重载、旧版交接及聊天验收留给后续实施任务。现行公开版仍须完整冷启动。
