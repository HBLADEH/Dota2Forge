# AstrBot 根目录更新日志随发行打包

Category: feature
Related task: [主题发行](../../tasks/active/2026-10-11-forge-theme-release.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [分发契约](../../../docs/subsystems/plugin-distribution.md)

## Problem
用户要求双端发版，并提供AstrBot Cloud“暂无更新日志”截图。实际页面确认为空；原生成器只携带README，Release说明不能代替插件根目录日志。

## Decision
AstrBot适配器根维护CHANGELOG.md，生成器按原文规范化换行复制到分发根和ZIP，源文件与输出均进入SHA256清单。记录alpha.10相对公开alpha.7的新主题、宽报告、素材准备与升级步骤；保留已公开版本历史，不把未发布a8／a9写成公开发行。

## Alternatives considered
只补GitHub Release正文不能确保宿主更新日志入口读取成功。[AstrBot上游实现](https://github.com/AstrBotDevs/AstrBot/pull/4337)读取插件根目录CHANGELOG.md；手工添加到分发目录又会绕过既有可复现摘要，因此纳入生成器。

## Consequences
仅AstrBot增加文档载荷；GsCore及业务接口不变，不带新权限／网络／运行时依赖。两端旧用户升级边界不放宽；Cloud抓取和审核结果单独验收。

## Verification
分发契约检查源文件、根目录、ZIP及源摘要一致；统一离线检查、实际候选smoke和公开下载／Cloud日志显示记录于发行任务。
