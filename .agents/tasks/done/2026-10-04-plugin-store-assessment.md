# 双平台插件商店与拆分评估

Status: done

## 目标
依据当前文档、实现和公开宿主安装流程，评估 Dota2Forge 是否适合拆分，给出 AstrBot 与 GsCore 插件商店一键下载安装的实施顺序。

## 非目标
本次为建议与记录，不迁移源码、不创建远程仓库、不发布包、不提交商店申请、不修改或重启实际宿主。

## 验收
- [x] 阅读架构、包配置、双端契约、有效决策与任务，区分实现和真实验收。
- [x] 核对公开宿主安装流程，说明现有安装产物为何尚不满足一键安装。
- [x] 比较统一开发、发布仓库拆分和多仓独立开发，提出可执行的推荐与发布前置条件。
- [x] 保存 proposed 决策建议，运行统一离线检查并记录真实结果及未验证项。

## 影响模块与决策
[架构](../../../docs/architecture.md)、[AstrBot 安装](../../../docs/cookbook/astrbot.md)、[Dota2UID 安装](../../../docs/cookbook/dota2uid.md)、[工程决策](../../notes/implemented/2026-09-30-workspace-foundation.md)、[分发建议](../../notes/proposed/2026-10-04-plugin-store-distribution.md)。仅新增评估记录。

## 验证证据
2026-10-04 开始时工作区干净。已阅读 README、架构、开发检查、四包元数据、双端发现安装器、宿主契约、现存任务及订阅最新安装证据。四包仍为 0.1.0a1；普通安装仍依赖手动 wheel 和桥接准备。

公开只读核查 AstrBot 项目固定 commit 的 updater/star_manager，以及 GsCore 项目固定 commit 的 server/插件安装流程和当前公开索引。核实根发现入口、依赖声明与 GsCore 更新开关边界；AstrBot 官方集合页已指向 cloud，GsCore 收录申请方式未核实。没有调用安装或发布 API。

本次运行 `uv run --locked python scripts/check_governance.py --all`，退出码 0；Ruff 格式/lint、mypy 60 源文件、1123 项禁网测试通过，聚合覆盖率 92.68%、Core 独立 92%、治理工具 97%。新增决策后调用同一检查器的 check_repository 复核预算、链接和参考漂移通过；`git diff --check` 通过。仅新增文档，未重建 wheel，也未把历史构建/实机证据当成本次商店验收。

## 阻塞与下一步
评估完成；建议优先统一开发、双端独立分发并提供自动依赖安装，再做干净宿主安装、升级/卸载和商店验收。建议仍为 proposed，实施应另建任务。真实订阅/权限验收保留原任务；未进行商店安装、外部发布或实际聊天验收。
