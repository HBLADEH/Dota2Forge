# 订阅比赛卡双端发行与现行服务器部署

Category: operations
Related task: [发布部署](../../tasks/active/2026-10-12-subscription-match-cards-release.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)、[双端适配器](../../../adapters/)
Related docs: [发行指南](../../../docs/cookbook/plugin-release.md)、[部署说明](../../../deploy/README.md)

## Problem
订阅比赛卡源码和2054项禁网验证已完成，但运行实例仍使用文字通知。用户明确授权发布并部署，新增共享展示API需要匹配Renderer与适配器，不能仅替换桥接或复用旧版本号。

## Decision
通过源码PR/CI固定SHA生成新UID a14 bundled与Astr alpha.12候选，使用Renderer a7。Core a7/Assets a1版本不变，复用既有公开wheel/sdist原字节；新建预发行及标签，不覆盖旧产物。上传draft全部附件并校验后公开，匿名核对仓库/ZIP/附件。Astr Cloud单次提交更新，审核由平台处理。

部署范围沿用经历史目标摘要与实时预检确认的服务器GsCore/Dota2UID。现行AstrBot只有GsCore适配器，未安装Dota2Forge独立插件；Windows宿主已停止。保留该路由，不新增独立实例。先备份匹配插件与必要数据、排空并停止GsCore，再安装精确已发布组件，启动后验证版本、清单、订阅调度、资源和HTTP状态。保留原配置、绑定、订阅和素材，不改SDK、全局无关包或平台目标。

## Alternatives considered
仅推分发main不能锁定安装摘要和Cloud版本；覆盖旧Release会破坏已安装版本的固定摘要。只更新入口会导致旧Renderer缺少新API。启动Windows旧实例可能形成重复调度，故以已在运行的服务器实例为部署对象。

## Consequences
维护窗口内对应Bot服务短暂中断，必须保留回滚所需旧组件及数据备份。成功启动不等于真实聊天视觉送达；不发测试消息、不解除旧outbox占用、不重建检查点。跨端仍无跨库去重，原调度归属不改变。

## Verification
源码离线及合成验证见前任务。发行固定SHA、公开附件、源码CI、服务器备份/版本/启动及Cloud状态实际证据在关联任务持续记录，未完成不写为已通过。
