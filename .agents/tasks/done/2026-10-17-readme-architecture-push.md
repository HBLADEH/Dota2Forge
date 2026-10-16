# README 手绘架构图整理与提交

Status: done

## 目标

按用户明确授权，将确认的 v2 手绘架构图直接嵌入 Dota2Forge 主 README，整理配套架构说明、资源和验证记录，提交并推送。

## 非目标

不改业务实现、治理门槛或真实部署；不混入既存两份 GsCore 商店历史任务及其他发行工作。

## 验收

- README 可直接看到 v2 手绘图，并能进入详细架构/交互文档。
- 说明 Core 业务、插件编排、Renderer 绘图和宿主发送顺序；源码与联调边界明确。
- README 中与本轮整理相关的已过时能力/发行提示按真实记录同步。
- 图、相对链接、文档预算、统一离线检查通过；审查明确文件清单后提交、推送并验证远端。

## 影响模块与决策

[README](../../../README.md)、[架构](../../../docs/architecture.md)、[详细图示](../../../docs/subsystems/platform-adapters.md)、[绘图验证](../../artifacts/platform-architecture-20261017/README.md)。仅整理既有架构事实，无新架构决策。

## 验证证据

开工分支 codex/stratz-features / 2866dfa；已保留既有修改。SSH 获取失败后改用既有 gh 登录的命令级 HTTPS 凭据，不改仓库远端或全局配置。

已从 origin/main / fd1ebff 创建 codex/readme-architecture，原分支内容已包含于主分支，只有合并提交差异。gh 只读确认 UID a16 / Astr a14 已公开且非 draft，README 同步链接与能力状态；Cloud 审核结论按发行记录保留。

README 已直接嵌入确认的 v2 原图，并补齐查询返回职责；原 PNG 摘要、1536×1024解码及相对位置核对通过。GitHub Markdown API 正文配本地 PNG 进行版式预览，960×640图示完整可读。审查暂存范围，不含两份既有商店历史任务。

统一离线入口退出0：2150项测试通过，641.22秒；聚合覆盖91.11%，scripts/Core/Assets分别94%/90%/92%，Ruff、mypy与治理门槛通过。完整日志见绘图验证目录。默认shell首次未启动，改用系统PowerShell执行原命令，不改检查入口或门槛。

图文提交 `1560c79529b0e6ad5d347db2db9b5a065b4d8ac7` 已通过原始 HTTPS 地址推送至 origin 的 codex/readme-architecture，未改远端地址或全局配置。GitHub API 确认分支 SHA、README、v2 PNG 与详细文档三个 blob 同本地，见[远端验证](../../artifacts/platform-architecture-20261017/push-verification.json)。已创建[PR #25](https://github.com/HBLADEH/Dota2Forge/pull/25)并附到当前聊天，目标main，未合并。

## 阻塞与下一步

整理、验证、提交与推送完成；PR待维护者评审/合并。现有两份商店历史任务保留未收录。功能和实机验收范围未扩大，录像事件、部署整合仍未实现，AstrBot完整多轮及部分订阅场景仍按原任务验收。
