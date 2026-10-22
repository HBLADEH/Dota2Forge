# 手绘图：补全渲染与消息回路

Status: done

## 目标

按用户反馈收紧画面留白，清楚展示插件取得 Core 业务结果、整理展示数据、调用 Renderer、取得 PNG 后经宿主回复用户的顺序。

## 非目标

不改变业务、架构、接口、部署与真实联调结论；保留上一版图片及其他任务修改。

## 验收

- 保留手绘风格和 GsCore→Dota2UID、AstrBot→AstrBot 插件两种独立接入。
- 插件到 Renderer、PNG 回到插件、宿主发送的责任和先后清楚；无 Core 直接渲染或 Renderer 直接发送。
- 生成 v2 图片、同步文档默认展示、保存提示词与核对证据。
- 复核图片文字与箭头、文档预算及链接；上一轮完整离线检查结果单列，不冒充本轮重跑。

## 影响模块与决策

[架构说明](../../../docs/subsystems/platform-adapters.md)、[原绘图任务](../done/2026-10-17-platform-architecture-map.md)。仅澄清现有流程，无新架构决策。

## 验证证据

核对 Dota2UID Runtime.dispatch 与 AstrApplication._prepare/dispatch：先构造图文回复并渲染，再调用注入的 send；真实业务仍由 Core 用例承担。

已生成[紧凑 v2 手绘图](../../../docs/assets/architecture/dota2forge-handdrawn-v2.png)，同步文档默认图片与业务/展示职责说明；v1 保留。人工核对上下接入路线、业务结果、五步回复链的文字及箭头。提示词与验证范围见[记录](../../artifacts/platform-architecture-20261017/README.md)。本轮复核治理、图源摘要与 diff 空白；业务代码无改动，上一轮完整统一离线检查退出0，本轮未重跑 pytest、未执行宿主/模型/聊天联调。

## 阻塞与下一步

已完成，无阻塞。尚未实现与实机未验证项沿用架构说明及原接入任务，没有扩大功能或验收范围。
