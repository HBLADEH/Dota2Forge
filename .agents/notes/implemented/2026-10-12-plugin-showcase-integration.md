# 双端当前主题截图与分发

Category: operations
Related task: [截图整合任务](../../tasks/done/2026-10-12-plugin-showcase-integration.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [截图来源](../../../docs/assets/screenshots/README.md)

## Problem
用户提供七张当前主题卡片，旧 README 只有一张历史出装图。玩家、近期战绩及三页比赛报告含身份字段，原件不能直接收录。并排缩略图使用 HTML img 时，AstrBot Cloud 同样需要完整图片 URL。

## Decision
用户确认全部来自 GsCore，授权 AstrBot 复用，并明确选择本地精确遮挡。菜单与出装保留原字节，其余五图只遮挡昵称、账号/比赛ID及来源URL的比赛ID，共40个矩形；通过Pillow解码对比验证其他像素完全一致，原件不变。两端复用同一套文件，玩家/战绩并排，菜单/三页报告/出装分别展开并附原图链接；不把身份值写入仓库、测试或记录。

文件存放在真实宿主 GsCore 日期目录，双端注明来源，未知宿主/插件/Renderer版本留在来源记录；不推断版本。历史 AstrBot 原图保留。

发行仍使用显式白名单，源图与目标图均入 SHA256 清单及 ZIP；Markdown 和 HTML 图片引用都适配目标仓库，Cloud 使用 raw URL。缺图、摘要、大小及禁止覆盖规则不变。

## Alternatives considered
直接收录原件不符合仓库隐私规则；重绘卡片会削弱实机证据。整张拼接或仅存缩略图会损失细节，因此保留独立原比例 PNG，通过 README 展开查看。

## Consequences
仅更改截图、文档与分发呈现，不改业务、版本、权限或真实配置。共享画面不证明另一平台聊天验收；配置截图和主动推送仍独立待补。本任务没有提交、推送或公开发布。

## Verification
已逐张目视检查七图，菜单/出装与源文件字节一致，其余五图的遮挡外像素完全一致；尺寸不变且无身份文本元数据。处理记录只存文件名、摘要、坐标与检查结果。最终统一离线2013项测试、Ruff/mypy、治理及所有覆盖率门槛通过；双端七图候选生成、SDK-free离线安装、白名单/ZIP字节/两份摘要和Cloud引用检查通过，完整结果见关联任务。本任务未运行真实宿主或公开发布。
