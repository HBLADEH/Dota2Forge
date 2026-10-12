# 订阅比赛卡发布与部署

Status: done

## 目标
用户在源码与合成预览验收后明确授权“发布部署”。发布UID a14/Astr alpha.12及Renderer a7，更新现行服务器Dota2UID部署，保留配置、绑定、订阅和素材。AstrBot通过GsCore适配器连接，未安装Dota2Forge独立插件，不新增第二业务实例；Windows历史宿主保持停止。

## 非目标
不覆盖旧Release；Core a7/Assets a1复用公开原字节。不改宿主SDK、全局无关依赖、调度归属、路由、订阅授权或数据schema；不创建订阅、人工重试或发送真实聊天。不把Cloud提交写成审核通过。

## 验收
- [x] 源码PR/CI通过并合并，候选固定已验证源码SHA；2054项离线结果继续有效，分发SDK-free smoke通过。
- [x] 双端分发main/tag/Release新建，各11附件与仓库/ZIP匿名字节及摘要一致；旧版保留。
- [x] 现行服务器已达到精确公开a14/Renderer a7，24插件及96运行文件验证通过，ready与订阅job确认，当前私有恢复点完成；发现先前更新/重启后只读验收，未重复执行冷安装。
- [x] AstrBot Cloud更新单次提交并确认Waiting，记录实时状态；真实图片推送和压缩单独待验。

## 影响模块与决策
[源码卡片任务](../done/2026-10-12-subscription-match-cards.md)、[发行指南](../../../docs/cookbook/plugin-release.md)、[部署](../../../deploy/README.md)、[发布决策](../../notes/implemented/2026-10-12-subscription-match-cards-release.md)。不改policy、工作流或治理脚本。

## 验证证据
源码最终统一离线2054项通过，聚合93.08%，五包构建/隔离导入通过，[证据](../../artifacts/subscription-match-cards-v1/README.md)。开工分支与origin/main树一致，既有两个未跟踪历史任务保留，不纳入提交。发行和服务器证据仅存脱敏状态。

2026-10-13源码PR #19合并，固定425fc9f66的四项CI通过；双端候选SDK-free smoke通过，Core/Assets复用原公开字节。UID a14与Astr alpha.12公开，每端11附件、main/tag/ZIP匿名字节一致；旧UID10个/Astr6个tag和Release保留。Cloud alpha.12单次更新提交，02:16复核仍Waiting，alpha.11 Published，详见[本轮证据](../../artifacts/subscription-match-cards-release-v1/README.md)。

部署只读门禁返回previous_plugin_drift，原拒绝结果保留；发现插件已于02:18快进到公开85b878e95，随后客户端关闭/新ready及容器重启，02:18:53订阅job注册。操作者未知，本轮没有stop/apply。独立实际状态核验通过：24插件、96私有运行文件与公开摘要一致；SDK源码/库版本、配置及服务JSON摘要与预检一致；1绑定/1订阅/0事件/0attempts，schema1/3。旧库行、库文件和素材逐文件无升级前基线，不称字节未变。

02:29附近建立明确标为升级后a14当前恢复点，私有0700目录/0600配置与DB文件；SQLite只读事务在线backup、integrity_check通过，无源数据库写入。保留源码.git/配置/服务JSON和两库，未发消息、修改绑定或解除尝试。具体UTC/本地时间及范围见证据，不冒充升级前备份。

实际私有运行代际及Pillow 12.3的禁网合成三页渲染通过，1600宽、最高3020、最大473532字节；未使用SDK、真实配置/库、Provider或消息，PNG字节丢弃。渲染后最终只读运行验收再次通过。

## 阻塞与下一步
发布与服务器目标版本核验完成。Cloud安全检查/上架由平台处理；真实图片订阅、QQ压缩、群权限及段位/日报继续由[Step13](../active/2026-10-02-subscriptions.md)跟踪。Windows宿主不启动，现行AstrBot路由及独立插件状态不改。
