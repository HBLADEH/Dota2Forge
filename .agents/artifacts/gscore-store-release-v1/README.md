# GsCore 公开发行执行证据

已发布[0.1.0a3](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a3)，提交[索引PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)，待审核。[执行记录](../../../docs/cookbook/gscore-store-publish.md)、[交付任务](../../tasks/done/2026-10-06-gscore-store-release.md)。

- [public-checks-a3.json](public-checks-a3.json)：匿名public/main及12个文件200，匹配a3发行候选。三个项目PyPI仍404，运行包通过GitHub Releases提供。
- [public-checks-final.json](public-checks-final.json)：main仅同步SDK验收与待审核说明后，12文件匿名200、匹配0.1.0a3-public-runtime-v2；入口/guard/清单/资源与发行v1不变，已发布ZIP/tag保留原快照。
- [store-pr.json](store-pr.json)：PR #40为OPEN/MERGEABLE，目标vp，只有索引一文件+17/-1，已附加当前任务。
- [package-manifest-a3.json](package-manifest-a3.json)、[release-assets-a3.json](release-assets-a3.json)：六个包与七个公开资产的版本、Python、依赖、大小和SHA256；全部匿名下载匹配，uploaded=true。a3发行ZIP来自0.1.0a3-public-runtime-v1；已公开资产和tag不改写。
- [build-a3.log](build-a3.log)、[isolated-install-a3.log](isolated-install-a3.log)：四包离线构建及双端无SDK/禁网候选安装通过，不作为真实平台证明。
- [pillow-11.3-checks.log](pillow-11.3-checks.log)：Pillow11.3下共享Renderer、两端消费者、安装器及分发检查424项通过。
- [offline-checks-a3.log](offline-checks-a3.log)：统一入口退出0，1398 passed；282文件格式、Ruff、mypy72源文件通过，总覆盖率93%，治理工具96%、Core93%，未放宽门槛。
- [document-checks-final.log](document-checks-final.log)：最终文档/架构/决策/生成漂移检查通过；文档同步后发行生成器36项再验证通过。
- [sdk-a3-exercise.json](sdk-a3-exercise.json)：真实SDK首次配置、hook与原生重载恢复、Trigger/SV/Bot图片编码、文字与失败、未认证管理拒绝、权限、任务唯一注册/移除和全部客户端关闭均通过。PNG仅保留合成输入产物摘要，没有发布合成战绩截图。
- [sdk-a3-upgrade.json](sdk-a3-upgrade.json)：公开a2冲突复现，a3安装器将Pillow12.3修复为11.3，三包来源URL/hash匹配公开清单，pip check通过；配置/两个库摘要不变。
- [sdk-a3-cold.json](sdk-a3-cold.json)：实际SDK冷加载新进程ready，绑定恢复，数据摘要不变。
- [sdk-a3-uninstall.json](sdk-a3-uninstall.json)、[sdk-a3-absent.json](sdk-a3-absent.json)：实际SDK卸载只删除发现目录；新进程不再注册Dota2UID，数据摘要仍一致。

环境固定GsCore0.11.0/87c06f1、Python3.13.2、Windows。SDK源码/函数未改；无生产数据复制、生产路由修改或QQ消息。未启动HTTP/WS监听服务，管理拒绝经ASGI原生认证依赖检查；Provider/出站分别为合成HTTP与内存帧采集，不证明真实平台递送。真实QQ新指令由用户后续测试。

早期a2的[初始公开](public-checks-initial.json)、[运行包摘要](package-manifest.json)、[资产下载](release-assets.json)与[sdk-preflight.json](sdk-preflight.json)保留历史。a2安装退出0但存在fastembed/Pillow冲突，不是兼容通过；原资产/tag保留并已添加发行提醒。

尚未验证维护者合并、真实商店界面、Linux/其他SDK或订阅真实推送；直接热安装缺包路径仍需要公开CLI与冷启动。生产a2及现有聊天路由保持原状。
