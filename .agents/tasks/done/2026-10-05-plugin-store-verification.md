# 双商店上架机制与当前分发核查

Status: done

## 目标
阅读当前文档与实现，核实 AstrBot、GsCore 当前商店收录及安装机制，补充已有分发评估，判断当前架构与仓库产物是否支持上架。

## 非目标
不迁移业务源码、不创建远程仓库、不发布包、不提交商店申请、不操作实际宿主或发送聊天消息。

## 验收
- [x] 阅读包配置、发现安装器、双端宿主契约及有效决策与任务，保留工作区已有修改。
- [x] 核实 GsCore 索引源码、MingChaoBQ PR #39 和宿主克隆/更新/依赖路径。
- [x] 核实 AstrBot 官方发布入口、仓库发现布局及安装约束。
- [x] 记录当前兼容性、阻塞项、推荐分发方案与真实检查结果，明确未验证项。

## 影响模块与决策
[当前架构](../../../docs/architecture.md)、[已有分发建议](../../notes/proposed/2026-10-04-plugin-store-distribution.md)、[已有评估](2026-10-04-plugin-store-assessment.md)、[事实核查](../../../docs/subsystems/plugin-distribution.md)、[补充建议](../../notes/proposed/2026-10-05-plugin-store-readiness.md)。仅文档调研；不改变公共契约。

## 验证证据
2026-10-05 开始时存在大量已修改和未跟踪源码、文档及资源，全部保留。本次只新增三份调研记录；联网仅用于公开资料，普通验证继续禁网。

git ls-remote核实GsCore master=87c06f1、文档vp=0b04c49、AstrBot master=42972e9；核查对应固定源码与PR补丁。GsCore在线索引HTTP200、42项、含MingChaoBQ/不含Dota2UID，与固定源码解析结果一致；PR #39在2026-09-27合并且只改索引。四个项目包PyPI JSON接口均404。AstrBot官方指南指向Cloud发布页、ZIP上限16MB；规范允许分支/HTTPS ZIP，禁止子目录repo。

运行 `uv run --offline --locked python scripts/check_governance.py --all`，退出码0：治理预算/链接/边界/生成参考、Ruff格式/lint、mypy 68源文件、1333项禁网测试通过（133.04秒）；聚合覆盖率92.99%、治理工具97%、Core93%，均通过独立80%门槛。任务归档后同一检查器的check_repository通过，正常git diff --check退出0，三份新增文档无行尾空白。额外使用core.autocrlf=false的差异检查误报现存CRLF；撤去该临时参数复核，不修改文件或仓库设置。未重建wheel；已有文件大小仅作体积风险参考，不冒充本次构建验证。

## 阻塞与下一步
调研完成，GsCore收录方式已补证。架构支持双端发布，当前主仓/桥接不能直接满足商店安装。下一步另建发行工程任务，生成根发现入口和依赖清单、首次配置引导，取得干净首次安装与旧版升级/卸载/数据保留证据后再提交两端收录。方案仍为proposed；没有外部发布、登录商店、申请收录、实际宿主操作或聊天验收，权限/订阅/新命令实测继续留在原任务。
