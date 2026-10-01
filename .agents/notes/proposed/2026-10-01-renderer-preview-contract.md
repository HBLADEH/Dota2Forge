# 基础图片展示契约草案与样图

> 实施状态：核心边界已由 [共享 Renderer 决策](../implemented/2026-10-01-shared-image-renderer.md) 取代；本文件保留样图参数和替代方案记录。

Category: architecture
Related task: [图片交互](../../tasks/active/2026-10-01-image-interaction.md)
Related code: [离线样图原型](../../artifacts/image-interaction-v1/preview.py)
Related docs: [当前架构](../../../docs/architecture.md)

## Problem
原决策要求样图先确认，但尚无可审阅版式。近期查询允许 100 条；每页 5 条若立即全部发送会产生 20 张图片。新增共享包也超出现有治理配置仅有 Core/两个适配器的包角色，不能把 Renderer 伪装成适配器以通过门禁。

## Decision
本文件记录已采用的原创浅色主题、北京时间、5 场/页的 [合成样图](../../artifacts/image-interaction-v1/README.md)，菜单只列当前功能；生产实现边界已按下列约束接入，细节以 implemented 决策为准：

- 独立 dota2forge-renderer 包依赖 Core 的不可变结果；Core 不反向依赖 Renderer、Pillow 或宿主。Renderer 只接收结构化成功数据、本地字体/资源和展示参数，输出 PNG ImageArtifact（bytes、mime、宽高），不拥有 HTTP/Provider。
- Adapter 提供 TextReply / ImageReply 两种回复。先查询一次并准备文本，再尝试工作线程出图；只捕获绘制/编码边界的已知 RenderError，回退同次文本。取消、Provider 分类错误与程序错误按现有边界处理；bot.send 失败传播，不自动重发。
- 图片计划宽 780、高最多 1600 px、单文件最多 2 MiB；每宿主最多一项绘制任务，排队与资源关闭有界。完整中文字体保留 OFL，未知/不支持字符有显式降级，不用预览子集支撑任意昵称。
- 默认 10 场最多发两页。查询 11–100 条也最多先发两张，并保留已取得结果供显式页码取图；不重新查询。具体翻页命令拟 `dota战绩 第N页`，只在功能启用后进入菜单。
- 图片分页与后续“第N场”选择共用有界宿主结果状态：部署/平台/机器人/会话/调用者隔离；账号与绑定记录核对，拟容量 128、TTL 10 分钟。改绑/解绑/停用/重载失效，只保存最后一次有效查询，不持久化。容量、有效期与命令仍待实施验证；这是交互状态，不是 Provider 数据缓存。
- 单局详情、STRATZ schema 核对与十人/两队详情卡已在后续任务接入；基础图片只显示已支持入口。
- 新包已扩展治理 Schema/policy 的共享包角色、单向依赖检查、构建/wheel 导入和资源断言；保留全部现有门槛，改动需维护者评审。

## Alternatives considered
- 100 场一次发 20 张：虽有固定页长仍会刷屏，采用有界发送和用户取后续页。
- 降低查询上限为 10：会破坏现有 1–100 契约，不选。
- 每次翻页重取 recent：可能导致序号漂移和额外额度消耗，不选。
- 字体依赖本机微软雅黑：不可保证跨宿主可用或再分发许可，选择 OFL 中文字体。

## Consequences
需要新增临时宿主状态并明确会话映射、失效/并发和最终取页规则；这些规则尚未实现。样图只确认排版，字体子集只覆盖样图；英雄/装备美术授权、QQ 压缩和真实发送仍需独立验证。启用新包前，治理扩展必须可审阅并保持失败门禁。

## Verification
已生成基础菜单/玩家/战绩两页/状态、未知玩家与空列表七张原型卡片及390px预览；生产包另生成九张卡片，文字边界/相互重叠、字体字符覆盖和100条布局检查通过。统一离线检查792项通过。真实QQ压缩/发送/重载尚未验证；核心Renderer契约已在implemented决策记录，本文保持proposed仅作样图历史。

后续已独立实现文本列表选择/取页，真实边界见 [已发送列表决策](../implemented/2026-10-01-delivered-list-selection.md)；图片Renderer/消息类型已在实现决策中记录，宿主实机联调仍待完成。
