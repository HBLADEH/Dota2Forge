# Dota2UID 复用宿主 Pillow 13.0

Category: bug-fix
Related task: [兼容候选](../../tasks/done/2026-11-19-dota2uid-pillow13.md)
Related code: [随包启动器](../../../scripts/gscore_bundled_runtime.py)、[Renderer](../../../packages/dota2forge-renderer/pyproject.toml)、[Assets](../../../packages/dota2forge-assets/pyproject.toml)
Related docs: [随包契约](../../../docs/subsystems/gscore-bundled-runtime.md)、[安装指南](../../../docs/cookbook/gscore-bundled-install.md)

## Problem
按宿主排查报告，GsCore 同步将共享 Pillow 从 12.3.0 升为 13.0.0；Dota2UID a16 随包校验正常但启动器和两个 wheel 均要求 `<13`。插件管理入口可用，业务未启动。共享环境由 GsCore 管理，插件更新不应要求宿主降级。

## Decision
Renderer a9、Assets a2、随包启动器统一 `Pillow>=11.3,<13.1`。保留下界与 12.x，新增 13.0 系列，不预先承诺 13.1。启动仍校验宿主环境、wheel 依赖和实际导入／字体渲染；分发测试对照根清单与启动约束。Dota2UID a17 更新两库最低版本，Core a9、HTTPX 范围与存储契约不变。AstrBot a15 同步本地桥接及组件版本用于共享回归，不发布。

## Alternatives considered
宿主回锁可以临时恢复，但会约束其他插件及自动更新。只放宽启动器仍会被 wheel 元数据拒绝；直接移除上限则让未验证的版本通过。本轮兼容无需修改 Core，也不引入独立工作进程。

## Consequences
候选只替换项目轮包与插件目录，不附带、不重装 Pillow；不兼容仍显式失败。公开 a16／AstrBot alpha.14 不重写。目标宿主冷启动和真实查询单独验收。

## Verification
实施前，真实 Pillow 13.0.0 下双端渲染、素材与图片回复专项通过 298 项。候选验收环境、构建与结果见[任务记录](../../tasks/done/2026-11-19-dota2uid-pillow13.md)。
