# 用户授权双端共用截图

Category: feature
Related task: [共用展示](../../tasks/done/2026-10-06-shared-plugin-screenshot.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)、[分发验证](../../../tests/test_plugin_distributions.py)
Related docs: [GsCore说明](../../../adapters/Dota2UID/README.md)、[来源](../../../docs/assets/screenshots/README.md)

## Problem
用户明确要求GsCore也使用此前截图。[原筛选决策](2026-10-05-plugin-screenshots.md)仅向AstrBot分发已审查出装图；原图来自AstrBot，但其卡片由双端共享Renderer生成，适合跨端展示。其他四图仍有旧指令/MMR缺项或身份信息。

## Decision
按用户授权让两端README共用既有主宰出装PNG，GsCore明确标注来自AstrBot、仅展示共享卡片。保留源端路径docs/assets/screenshots/astrbot/hero-items.png和原图字节，新增GsCore白名单指向同一源文件，分发后两端均为screenshots/hero-items.png。来源摘要记录原文件，产物摘要分别覆盖两端副本。

这取代旧决策中“GsCore不携带AstrBot图片”的展示限制；旧决策中的隐私、旧版本筛选、缺图失败和真实验收边界继续适用。同步本机GsCore README/图片时备份旧说明，不更新运行包/桥接/配置或重启。

## Alternatives considered
重新拍摄全部GsCore图增加用户工作且违背本次复用要求；重复建立gscore源图目录会模糊真实出处。采用单一AstrBot源图、明确展示归属和两端打包副本。含身份或旧指令图片继续留本机，不改图制造新版本证据。

## Consequences
GsCore ZIP增加一张已审查图片，仍核对本地链接、摘要、大小和重复构建。共用截图不证明GsCore连接、指令捕获、权限或消息递送；真实联调仍由宿主任务跟踪，不将AstrBot结果扩展为GsCore通过。

## Verification
将现有截图分发测试扩展为双端：逐端核对README本地引用、原图字节、ZIP条目和双摘要，并验证GsCore来源文字；缺图失败及候选防覆盖保持。新候选重复生成一致，两端全部摘要匹配；本机README/图片同步，入口/配置/两库保持。统一离线1377测试、Ruff/mypy及独立覆盖门槛通过，[证据](../../artifacts/shared-plugin-screenshot-v1/README.md)与[任务](../../tasks/done/2026-10-06-shared-plugin-screenshot.md)记录真实范围。
