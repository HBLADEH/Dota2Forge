# 双端 README 预发行证据

[发行任务](../../tasks/active/2026-10-12-plugin-readme-release.md)、[发行决策](../../notes/implemented/2026-10-12-plugin-readme-release.md)。

用户授权复核后分别发布两端。新版本为 AstrBot 0.1.0a11／host alpha.11 与 Dota2UID 0.1.0a13；公开操作尚未执行。

[隐私复核](privacy-validation.json)确认七张图片与审查摘要一致：40个身份遮挡矩形、原分辨率和遮挡外像素均符合记录，原件未改变，无文本元数据。[共享包复核](shared-packages-validation.json)确认Core a7、Renderer a6、Assets a1的三份wheel及三份sdist与公开UID a12字节一致。

[五包构建](build.log)、[五包隔离安装／导入](wheel-smoke.log)退出0；[统一离线检查](offline-check.log)2013项通过，覆盖率92.52%，Ruff/mypy及scripts、Core、Assets门槛通过。最终文案精简后[分发专项](distribution-tests-final.log)89项通过，文档治理与格式/lint再次通过，[最终五包重建](build-final.log)退出0。真实宿主和聊天未操作。

专项首轮两项失败为旧断言仍要求已移除的拍摄待办／生成器链接，保留[原日志](distribution-tests.log)，改为对实际订阅／后台配置指南验证同样的固定源码引用与非安装链接隔离。两种source_ref、安装页、许可和来源断言均保留。第一次尝试重复传uv build的--package参数失败，见[参数错误](adapter-build-final.log)；改用既有五包命令成功，未跳过构建。

[Cloud基线](cloud-baseline.json)为2026-10-12浏览器实读：alpha.10 Published，更新日志非空。前次发行的Cloud待确认项已完成，新版待GitHub发行后提交。
