# GsCore商店上架前置条件复核

Status: done

## 目标
按用户要求排查当前Dota2UID是否具备GsCore商店上架前置条件，复核最新本地候选、公开分发/依赖取得、索引要求与实际宿主验收，列出明确阻塞项。

## 非目标
不创建/推送远程仓库、不发布包、不提交索引PR、不发送聊天或更改宿主；不把本机预装wheel、AstrBot截图或SDK桩当作干净商店安装。保留所有已有修改和候选。

## 验收
- [x] 核对候选根入口/依赖/版本/许可/图标/截图/摘要、源码匹配与隔离安装证据。
- [x] 公开只读核实索引来源/收录路径、目标仓库/原图可达性及锁定项目包发布状态。
- [x] 核对本机手动升级与商店新装/升级/卸载/聊天的证据范围，不混用版本。
- [x] 记录已满足、硬阻塞、未验证和建议下一步，同步事实文档及统一检查。

## 影响模块与决策
[发行契约](../../../docs/subsystems/plugin-distribution.md)、[发行步骤](../../../docs/cookbook/plugin-release.md)、[先前前置条件](../../notes/proposed/2026-10-05-plugin-store-readiness.md)、[本机GsCore](../done/2026-10-05-gscore-current-deployment.md)。本次仅复核，不改变架构或发布策略。

## 验证证据
开工保留已有修改。[本轮记录](../../artifacts/gscore-store-readiness-v1/README.md)和[核查文档](../../../docs/cookbook/gscore-store-readiness.md)已同步。0.1.0a2-shared-showcase-v1全部来源/输出摘要匹配，GsCore ZIP1915995 bytes；根入口/依赖清单/guard/许可/主宰ICON/共享截图齐全，README标明AstrBot来源，没有真实配置/数据库。

uv build --offline --all-packages --out-dir .tmp/gscore-store-readiness-wheels退出0，四包文件匹配当前源码，重建与已有dist wheel SHA256一致。uv run --offline --locked python scripts/smoke_plugin_distributions.py --candidate dist/plugin-distributions/0.1.0a2-shared-showcase-v1 --wheels dist退出0：两端独立Python3.12.9环境离线从本地wheel安装，SDK不存在、HTTP全部拒绝，版本guard/空Token/配置ready/绑定重启保留通过。

匿名核实目标仓库及main入口/清单/ICON均404，三个项目PyPI均404；HTTPX/Pillow有匹配版本。运行索引200、42条无Dota2UID，与vp固定0b04c49字节相同；已合并PR#39支持vp索引条目/分类收录路径，不推定完整审核规范。

GsCore master固定87c06f1：AST提取并执行真实check_pyproject/process_dependencies/flush_pending_installs/reload_plugin和候选guard，自动安装开启但缺三个项目库时，热路径收集依赖未安装即导入被拦；显式flush对照通过，探针退出0。SDK注册表/路径组合/安装效果合成且禁网，未改宿主，不代替实际商店安装。

本机0.1.0a1→0.1.0a2停机预装wheel升级/冷启动ready/数据保持沿用先前证据；公开源新装/商店升级/卸载回退、当前GsCore聊天与其他平台未验证。

uv run --offline --locked python scripts/check_governance.py --all退出0：[最终日志](../../artifacts/gscore-store-readiness-v1/offline-checks.log)，275文件格式、Ruff、mypy71文件、1377禁网测试（168.20s），治理工具覆盖率96%/Core93%。归档后再复核文档链接与仓库治理，见证据目录。

## 阻塞与下一步
核查结论已明确：本地候选准备完成，上架前仍需公开分发仓库和三个匹配运行包，处理并实际验证热安装或明确冷启动流程，然后验收公开源实际宿主新装/更新/数据保留并提交vp索引PR。PyPI为当前方案，不是官方唯一渠道；不因索引草稿完整、手动ready或共享截图推定已上架。本次未发布包/推送仓库/提交PR/发送聊天。
