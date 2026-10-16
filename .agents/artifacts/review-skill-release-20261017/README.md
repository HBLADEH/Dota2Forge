# 双端复盘 Skill 发行证据

用户于2026-10-17授权分别整理并发布GsCore和AstrBot，随后自行测试；本轮不部署宿主、不发送真实消息。

目标为Dota2UID0.1.0a16／AstrBot0.1.0-alpha.14，Core0.1.0a9、Renderer0.1.0a8、Assets0.1.0a1。开工远端源码main为dde3e97，GS main为50a3898，Astr main为915396d；两端目标版本无既有标签或Release。前轮源码292c84a及cc591cc推送CI均success；两份既存未跟踪任务保留。

本轮整理双端README、新指令／连续复盘、宿主唤醒和工具权限、独立升级流程、AstrBot根CHANGELOG，清除仍称未实现的旧提示。业务源码沿用[Skill实施](../review-skill-20261016/README.md)，参考项目的MIT许可随Core提供。

[统一入口](check-all.log)exit0：2150项禁网测试／524.59秒，聚合覆盖91.11%，scripts／Core／Assets分别94%／90%／92%；Ruff与mypy103源文件通过。首次仅因发行指南超过4000字符预算被拒绝，缩短历史段落后原门槛通过，保留[初始记录](check-initial-budget.log)。

[五包构建](build-wheels.log)、[五包隔离安装](smoke-wheels.log)、[双端离线分发](smoke-distributions.log)均exit0；安装检查使用本地依赖，无宿主／凭据／真实消息。首个wheel检查指定的临时根缺少脚本要求的dist子目录，修正暂存布局后运行原脚本通过，保留[失败记录](smoke-wheels-initial-path.log)，未改断言或源码。

[候选校验](candidate-validation.json)核实十份wheel／sdist、版本／源码摘要、ZIP完整目录、七张既有审查截图及Core中的六份Skill资源；未加入真实聊天图或配置／数据库。[Assets原字节](reused-assets.json)从公开UID a14下载后核对，未覆盖旧版。验证辅助代码仅用于本次显式发行，不进入运行包。

固定源码0e3ecc0d1eda948b548feae03c7c9fa62944d52d，[四项CI](source-ci.json)全部success，[PR #23](https://github.com/HBLADEH/Dota2Forge/pull/23)合并为3e24e5b0616b56af664a7ac463c5cbce556a7da0。GitHub连接器写权限不足，改用既有已登录gh创建；不改变账号权限。

双端分发PR已合并：GS [#7](https://github.com/HBLADEH/Dota2UID/pull/7)→8cfcfce5630f14135b0362d337e7dfd417b4a024，Astr [#1](https://github.com/HBLADEH/astrbot_plugin_dota2forge/pull/1)→c885bbfa6fac4f3a4863a08d868413722b55ae8e。[提交](committed-candidates.json)与[合并后main](main-candidates.json)分别核对25／20文件与生成候选逐字节一致。

双端先核对draft全部11附件的大小／GitHub SHA256、main和固定tag，再公开为预发行；见[GS](Dota2UID-draft-validation.json)和[Astr](astrbot_plugin_dota2forge-draft-validation.json)。上传大附件较慢，完成前未开放不完整发行；draft按tag读取返回404，改按已创建ID读取，保留[原响应](gscore-draft-tag-lookup.json)，未重复创建。

| 插件 | 公开发行 | main／tag提交 | 匿名下载核对 |
| --- | --- | --- | --- |
| GsCore | [v0.1.0a16](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a16) | 8cfcfce5630f14135b0362d337e7dfd417b4a024 | [25文件／ZIP／11附件](Dota2UID-public-validation.json) |
| AstrBot | [v0.1.0a14／alpha.14](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a14) | c885bbfa6fac4f3a4863a08d868413722b55ae8e | [20文件／ZIP／11附件](astrbot_plugin_dota2forge-public-validation.json) |

首次匿名API请求因共享出口限流403失败，保留[GS](gscore-anonymous-api-403.log)／[Astr](astrbot-anonymous-api-403.log)；仅发行元数据改用已登录gh API，codeload仓库与全部附件仍匿名完整下载。两份报告明确anonymous=false、assets_anonymous=true，不把已登录元数据写成全匿名。实际文件逐字节／SHA256与候选一致，[汇总](publication-summary.json)确认原GS11／Astr7个tag和Release及其附件ID／大小／摘要均未变。

Cloud[本轮基线](cloud-baseline.json)已确认alpha.12 Published且原账号有发布权限。新的Skill真实模型效果与AstrBot真实多轮仍待用户测试；本轮不操作宿主、模型或真实消息。

## Cloud

在原发布空间／市场ID单次点击更新alpha.14，返回版本页；初次刷新未出现新行，保留[当时记录](cloud-submission-attempt.json)。仅做只读复核：作者后台仍为原插件，重新解析仓库后提示“当前版本为v0.1.0-alpha.14”，相较提交前alpha.12已改变，确认接收；没有第二次提交。

版本列表仍只见alpha.12 Published，alpha.14的审核行／结论未可见；原因未证实，不推断缓存，也不记为Waiting或Published。[最终回执](cloud-submission.json)、[页面截图](cloud-versions-after-submit.png)明确published=null。GitHub两端已完成，用户可先按固定发行安装测试；Cloud可见状态后续独立确认。

[完成任务](../../tasks/done/2026-10-17-review-skill-release.md)列出升级与测试接续。另项README、架构和平台映射文档工作保持原状，不纳入本轮发行记录提交。
