# Dota2UID 宿主 Pillow 13.0 兼容候选

Status: done

## 目标
生成 Dota2UID 0.1.0a17 随包候选，复用 GsCore 已安装的 Pillow 13.0.0，保留原有 11.3 和 12.x 兼容，不改宿主依赖。

## 非目标
不修改 Core 业务或存储，不安装宿主共享包，不发布 Dota2UID 或 AstrBot，不操作生产容器或发送真实消息。

## 验收
- [x] Renderer、Assets、Dota2UID 宿主约束和两端分发清单一致；已公开版本内容不变。
- [x] 启动器接受 Pillow 11.3.0、12.3.0、13.0.0，拒绝范围外版本并保留既有环境校验。
- [x] wheel 构建和使用真实旧版／13.0.0 的双端隔离分发检查通过。
- [x] 统一离线检查通过。

## 影响模块与决策
[兼容决策](../../notes/implemented/2026-11-19-dota2uid-pillow13.md)、[GsCore 随包契约](../../../docs/subsystems/gscore-bundled-runtime.md)、[共享渲染契约](../../../docs/subsystems/renderer.md)。

## 验证证据
实施前用隔离的 Windows / Python 3.12 和真实 Pillow 13.0.0 运行两端渲染、素材及回复专项：298 项通过。现行启动器仍报告 `dependency_incompatible`。

五包构建和 Pillow 13.0.0 下五 wheel 独立安装通过。Windows / Python 3.12 上，分别只提供 Pillow 11.3.0、12.3.0、13.0.0 的三次双端离线分发检查均通过；Python 3.13 / Pillow 13.0.0 双端分发复验通过。无真实宿主 SDK、凭据或消息。

同一个预装 Pillow 13.0.0 的隔离进程，a16 拒绝准备；a17 成功准备和激活、生成可解码 PNG，沿用同一 Pillow 模块且原生库摘要不变。随包复用原公开 Core a9 wheel。

最终包 `dist/dota2uid-pillow13-20261119/final/Dota2UID.zip` 的 25 个条目逐一匹配清单，SHA-256 `37d715696fc81b20ba3ef1dcc80395340e7773dcf02b16caef0679cfe2587171`。两页文档字符预算和旧安装链接文案回归均已修正，保留原门槛与断言。

`uv run --offline --locked --no-sync python scripts/check_governance.py --base main` 退出 0：2159 项禁网测试，总覆盖 91.14%，scripts／Core／Assets 分别为 94%／90%／92%，Ruff、mypy 与治理检查通过。

## 阻塞与下一步
本地候选完成，未发布或部署。生产同构 Linux/GsCore 冷启动及真实查询需单独验证；保持宿主 Pillow 13.0.0，只替换 Dota2UID 分发目录，确认 `do核心状态` 为 a17／`ready` 后验证一次只读查询。
