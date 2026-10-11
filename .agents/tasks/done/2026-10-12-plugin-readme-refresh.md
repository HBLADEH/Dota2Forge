# 双端 README 整理与截图计划

Status: done

## 目标
按用户要求阅读当前项目文档，更新 AstrBot 与 Dota2UID README，以简洁、准确的开源项目格式介绍安装、配置、命令和使用边界；整理用户随后提供的真实截图需求。

## 非目标
不生成或伪造功能截图，不修改业务、宿主、配置或数据；不提交、推送、发布或发送聊天消息。

## 验收
- 两端结构一致，平台前缀、配置入口、权限及更新流程各自准确；移除 README 内重复的发行历史。
- 保留已有审查图片及真实来源，未提供图片不建立空文件或失效链接。
- 截图清单覆盖当前菜单、MMR、战绩及三页比赛报告，区分共享展示与平台配置。
- 分发生成后标题、安装说明、图标/截图链接及摘要仍正确；统一离线检查通过。

## 影响模块与决策
[AstrBot README](../../../adapters/astrbot_plugin_dota2forge/README.md)、[Dota2UID README](../../../adapters/Dota2UID/README.md)、[截图清单](../../../docs/cookbook/plugin-showcase.md)、[发行生成器](../../../scripts/build_plugin_distributions.py)。遵守既有共享主题、截图来源及双端分发契约。

## 验证证据
开工时仅有两份未跟踪商店历史任务，保留不动。已读根/适配器/docs/tests规则、架构、相关契约、安装步骤、有效决策和发行/订阅任务；当前源码与历史部署证据分别处理。

`uv run --locked python scripts/check_governance.py --all` 最终退出0：2013项禁网测试通过，Ruff格式/lint、mypy87源码文件及治理/文档链接通过，聚合和scripts/Core/Assets三个独立覆盖率门槛均通过。首轮2011通过、2失败，失败来自旧分发导航断言；改为验证安装链接本地化、其他文档保留正确源码地址，补充薄分发不使用随包管理命令的断言后完整复测通过，未放宽门槛。

生成本地候选 `dist/plugin-distributions/readme-refresh-20261012-v3`；`uv run --locked python scripts/smoke_plugin_distributions.py --candidate dist/plugin-distributions/readme-refresh-20261012-v3 --wheels dist` 双端退出0，核对摘要、离线依赖、素材、首配、关闭和持久化。使用已有匹配wheel，没有启动真实宿主或发送消息。`git diff --check` 通过。

## 阻塞与下一步
本轮文档更新和截图计划已完成；[决策](../../notes/implemented/2026-10-12-plugin-readme-refresh.md)记录分发差异。新主题真实卡片待用户按清单提供，再审查脱敏、补入README并同步发行白名单和来源。英雄攻略/AI Tool未实现，订阅实际推送和其他平台仍待实机验收；本轮未提交或发布。
