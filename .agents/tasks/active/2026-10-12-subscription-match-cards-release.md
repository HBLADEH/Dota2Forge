# 订阅比赛卡发布与部署

Status: active

## 目标
用户在源码与合成预览验收后明确授权“发布部署”。发布UID a14/Astr alpha.12及Renderer a7，更新现行服务器Dota2UID部署，保留配置、绑定、订阅和素材。AstrBot通过GsCore适配器连接，未安装Dota2Forge独立插件，不新增第二业务实例；Windows历史宿主保持停止。

## 非目标
不覆盖旧Release；Core a7/Assets a1复用公开原字节。不改宿主SDK、全局无关依赖、调度归属、路由、订阅授权或数据schema；不创建订阅、人工重试或发送真实聊天。不把Cloud提交写成审核通过。

## 验收
- [ ] 源码PR/CI通过并合并，候选固定已验证源码SHA；2054项离线结果继续有效，分发SDK-free smoke通过。
- [ ] 双端分发main/tag/Release新建，各11附件与仓库/ZIP匿名字节及摘要一致；旧版保留。
- [ ] 现行服务器GsCore预检/备份/停止/安装/启动完成，版本、资源关闭/启动及配置/数据保留证据通过。
- [ ] AstrBot Cloud更新单次提交或明确平台阻塞，记录实时状态；真实图片推送和压缩单独待验。

## 影响模块与决策
[源码卡片任务](../done/2026-10-12-subscription-match-cards.md)、[发行指南](../../../docs/cookbook/plugin-release.md)、[部署](../../../deploy/README.md)、[发布决策](../../notes/implemented/2026-10-12-subscription-match-cards-release.md)。不改policy、工作流或治理脚本。

## 验证证据
源码最终统一离线2054项通过，聚合93.08%，五包构建/隔离导入通过，[证据](../../artifacts/subscription-match-cards-v1/README.md)。当前源码分支与origin/main树一致，既有两个未跟踪历史任务保留，不纳入提交。发行和服务器证据另存最小脱敏状态。

## 阻塞与下一步
核对运行实例，准备固定源码候选，发布后在备份及关闭完成的边界更新现行GsCore。实际平台接受回执与QQ图片可读性需要用户发起订阅验收。
