# 订阅比赛卡发行与服务器运行验收

用户已授权发布与部署；2026-10-13双端GitHub预发行公开且匿名验证通过，现行服务器a14目标运行已验收。候选固定源码 SHA `425fc9f66b489778f35f2690427a5d8b60f40df3`，源码[PR #19](https://github.com/HBLADEH/Dota2Forge/pull/19)合并至`1cacecde3eb041af05e7de8ce53189e5a46742cf`，四项CI通过：[检查](source-ci.json)、[合并](source-merge.json)。

目标运行组件：Renderer 0.1.0a7、Dota2UID 0.1.0a14、AstrBot 0.1.0a12；Core 0.1.0a7、Assets 0.1.0a1 不变。原卡片开发验收为 2054 项禁网测试通过、五包构建及隔离导入通过，见[合成验收](../subscription-match-cards-v1/README.md)。

[payload-preparation.json](payload-preparation.json)记录十份项目 wheel/sdist 的完整摘要。Core/Assets 四份文件从公开 UID a13 匿名下载，并与前次公开大小和 SHA256 一致；新版本三包取本地构建，原 dist 未修改。临时二进制保存在被忽略的 wheels/candidate/assets，既有公开 Release 不覆盖。

准备流程：固定最终源码 SHA，运行仓库分发生成器；[validate_candidate.py](validate_candidate.py)核对版本、source_ref、源与候选摘要、ZIP 完整目录、七张既有审查截图、包内私有文件与用户样本边界；执行双端 SDK-free 离线分发 smoke。真实配置、凭据、聊天、数据库不进入发行候选。

[最终生成](distribution-build-final.log)、[双端离线 smoke](distribution-smoke.log)均退出 0；[候选复核](candidate-validation.json)通过，包含十份 wheel/sdist 解包与 12 个用户身份/比赛/事件样本排除验证，仅记录数量与结果，不保存样本。新三包最终重建后旧未公开暂存保存在 wheels/previous-local-build；稳定 Core/Assets 不变。

首个生成器 CLI 调用退出 1，仅返回通用错误，见[原日志](distribution-build.log)；相同输入直接调用成功，再以原 CLI 命令复跑通过并核对完整源码及输出摘要。未修改源码、断言或门槛，原因未证实，未将推测记为结论。

公开流程：将候选完整同步到两个独立分发仓库并记录提交；[release_assets.py](release_assets.py) stage 每端 ZIP、四个 wheel、四个 sdist，加 release-assets.json/SHA256SUMS。先上传至 draft，核对附件数量、大小和 GitHub 摘要，再公开为 prerelease；最后匿名完整下载 API/codeload/全部 11 附件，与本地候选逐字节核对。源码及分发标签固定，不覆盖旧发行。

双端发布正文见[AstrBot](astrbot-release-notes.md)、[Dota2UID](gscore-release-notes.md)。主任务单独记录服务器实际运行代际及配置/数据核验范围；真实聊天发送、客户端图片压缩、Cloud 审核与商店收录分别报告。

## 公开验证

| 插件 | 预发行 | 分发main/tag提交 | 匿名结果 |
| --- | --- | --- | --- |
| AstrBot | [v0.1.0a12 / alpha.12](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a12) | `915396d6b8e137045874f21195eb6e9347852b2f` | [20仓库文件、ZIP、11附件](astrbot_plugin_dota2forge-public-validation.json) |
| Dota2UID | [v0.1.0a14](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a14) | `85b878e95651676b10e85c407450770bc0188c0b` | [24仓库文件、ZIP、11附件](Dota2UID-public-validation.json) |

附件先在draft核对大小与GitHub SHA256，再公开；全量匿名下载逐字节与候选一致。新main/tag正确，旧Astr6个与UID10个tag/Release全部保留，见[refs](public-refs-validation.json)与[汇总](publication-summary.json)。一次重复UID普通push被拒绝，最终目标只读确认；没有force push、覆盖旧附件或改写原门槛。

## Cloud

[实时基线](cloud-baseline.json)确认alpha.11已Published；alpha.12现按原市场ID、HBLADEH仓库和发布空间单次更新提交，UI显示Waiting／等待安全检查，见[提交](cloud-submission.json)。INSTALL及CHANGELOG均解析alpha.12，未新增插件或重复提交；安全审核和上架由平台处理。

## 现行服务器

[预检](deploy-preflight.json)确认现行GsCore为Dota2UID a13/image/订阅启用，AstrBot只有GsCore适配器而无Dota2Forge独立插件，Windows宿主停止。SSH目标摘要与历史授权目标相同；未输出原目标、凭据、路由或聊天。

固定公开候选通过[暂存核验](deploy-staging.json)。原冷安装validate-only因previous_plugin_drift被拒绝，[失败原件](deploy-candidate-validation-failed.json)保留，未放宽门禁：服务已在02:18快进到a14并重启，执行者未知，本轮没有stop/apply。

[独立当前状态](deployment-already-current.json)确认24插件文件和96私有运行文件与公开提交/清单匹配，active为UID a14/Renderer a7/Core a7/Assets a1；关闭及新ready/job标记、容器重启有时间证据。配置及服务JSON摘要、SDK源码摘要/库版本与预检一致；1绑定/1订阅/0事件/0attempts，schema1/3保留。旧数据库行/文件、全局库和素材逐文件摘要没有预检基线，不称字节未变。现有1656张素材已记录当前摘要。

[当前恢复点](deployment-current-restorepoint.json)明确is_pre_upgrade_backup=false；公开插件/.git、配置/服务JSON及两库在线backup只留服务器私有0700目录，敏感文件0600，SQLite只读事务与integrity_check通过，无源库写入。原本冷安装/回滚路径仅[合成验收](deploy-helper-validation.json)，不冒充生产执行。[最终只读检查](deployment-postflight.json)另记录运行与保留范围。

[宿主合成渲染](deployment-host-render.json)使用实际私有运行代际与Pillow 12.3，FIXTURE十人数据生成三页PNG，尺寸1600×2556/3020/3020，最大473532字节，均通过3200高与2MiB边界。socket禁网，未导入SDK或读取真实配置/数据库，未调用Provider或发送消息，图片字节已丢弃；随后最终只读检查再次通过。

发布与实际目标版本核验完成，原AstrBot路由不改。当前恢复点并非旧版本回滚证明；真实聊天递送、图片压缩、群权限和Cloud审核分别接续，[完成任务](../../tasks/done/2026-10-12-subscription-match-cards-release.md)与[决策](../../notes/implemented/2026-10-12-subscription-match-cards-release.md)说明原因和限度。
