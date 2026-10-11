# 双端 README 与截图发布

Status: in_progress

## 目标
按用户“整理好以后，过一遍没什么问题就分别进行发布操作”的授权，复核并发布 AstrBot alpha.11 与 Dota2UID a13，包含专业化 README、七张脱敏截图及 AstrBot 居中导航；提交 AstrBot Cloud 更新并如实记录平台状态。

## 非目标
不操作生产宿主、凭据、配置、数据库或真实聊天；不覆盖旧 Release，不改变共享业务或 GsCore 索引 PR #40。

## 验收
- 双端说明符合实际命令、配置、数据与升级边界，截图来源明确、身份脱敏、链接有效。
- 统一离线检查、五包构建、独立 wheel 安装与双端分发 smoke 通过，共享组件版本和字节不变。
- 源码经 PR/CI 合并；分发固定源码 SHA，main、tag、ZIP 和每端 11 个公开附件一致，匿名下载核对摘要。
- AstrBot 根 CHANGELOG 包含本次更新；Cloud 提交与审核状态分别记录。

## 影响模块与决策
[发行指南](../../../docs/cookbook/plugin-release.md)、[README 任务](../done/2026-10-12-plugin-readme-refresh.md)、[截图任务](../done/2026-10-12-plugin-showcase-integration.md)、[导航任务](../done/2026-10-12-readme-navigation-center.md)、[发布决策](../../notes/implemented/2026-10-12-plugin-readme-release.md)。

## 验证证据
开工时主仓 main 为 372b108c，AstrBot 最新 v0.1.0a10、UID 最新 v0.1.0a12；公开发行均为预发行。已有三个文档任务修改全部保留；两份 2026-10-09 未跟踪任务不纳入本次提交。新分支从当前远端 main 建立，源树与原工作分支相同。

统一离线入口exit0，2013项通过，覆盖率92.52%；Ruff/mypy和三组覆盖率门槛通过。最终文案后分发专项89项通过，文档治理及格式/lint复核通过；五包构建、独立安装、七图隐私/像素、三组共享wheel/sdist字节一致均通过，[证据](../../artifacts/plugin-readme-release-20261012/README.md)。Cloud alpha.10 Published且日志非空，前次任务已完成。

## 阻塞与下一步
复核版本与说明、运行检查、合并源码，再生成并发布双端固定 SHA 候选。Cloud alpha.10 前次提交已接收，先读取平台当前状态再更新，避免重复提交旧版。
