# 订阅比赛卡双端发行与现行服务器部署

Category: operations
Related task: [发布部署](../../tasks/done/2026-10-12-subscription-match-cards-release.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)、[双端适配器](../../../adapters/)
Related docs: [发行指南](../../../docs/cookbook/plugin-release.md)、[部署说明](../../../deploy/README.md)

## Problem
订阅比赛卡源码和2054项禁网验证已完成，但运行实例仍使用文字通知。用户明确授权发布并部署，新增共享展示API需要匹配Renderer与适配器，不能仅替换桥接或复用旧版本号。

## Decision
通过源码PR/CI固定SHA生成新UID a14 bundled与Astr alpha.12候选，使用Renderer a7。Core a7/Assets a1版本不变，复用既有公开wheel/sdist原字节；新建预发行及标签，不覆盖旧产物。上传draft全部附件并校验后公开，匿名核对仓库/ZIP/附件。Astr Cloud单次提交更新，审核由平台处理。

部署范围沿用经历史目标摘要与实时预检确认的服务器GsCore/Dota2UID。现行AstrBot只有GsCore适配器，未安装Dota2Forge独立插件；Windows宿主已停止。保留该路由，不新增独立实例。先备份匹配插件与必要数据、排空并停止GsCore，再安装精确已发布组件，启动后验证版本、清单、订阅调度、资源和HTTP状态。保留原配置、绑定、订阅和素材，不改SDK、全局无关包或平台目标。

实际部署门禁发现源版本已由其他执行者更新为目标a14，拒绝原a13冷安装分支，未放宽门禁。保留失败证据，改为独立核验实际公开文件、运行代际、配置及ready/job；日志确认快进、关闭、新ready和容器重启，操作者未识别。本轮未重复stop/apply；创建升级后的当前私有恢复点，两库以只读事务在线backup，不写源库。

## Alternatives considered
仅推分发main不能锁定安装摘要和Cloud版本；覆盖旧Release会破坏已安装版本的固定摘要。只更新入口会导致旧Renderer缺少新API。启动Windows旧实例可能形成重复调度，故以已在运行的服务器实例为部署对象。

## Consequences
计划冷安装需要短暂维护窗口和旧组件备份，本轮没有执行；当前恢复点不冒充升级前状态。成功启动不等于真实聊天视觉送达；不发测试消息、不解除旧outbox占用、不重建检查点。跨端仍无跨库去重，原调度归属不改变。

## Verification
源码四项CI、双端SDK-free smoke及每端11附件匿名核验通过；旧tag/Release保留。服务器24插件/96运行文件精确匹配、配置摘要及SDK源码/库版本一致，数据库schema/计数保留；旧行/库文件/素材摘要无基线，不作逐字节不变承诺。当前SQLite恢复点及完整性验证通过，实际运行代际的禁网合成三页PNG渲染通过。Cloud alpha.12仅单次提交并显示Waiting，真实图片推送待验。范围和证据详见关联任务。
