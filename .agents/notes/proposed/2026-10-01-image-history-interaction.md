# 图片交互与历史单局详情的后续顺序

Category: architecture
Related task: [图片交互](../../tasks/active/2026-10-01-image-interaction.md)、[历史详情](../../tasks/active/2026-10-01-historical-match-detail.md)
Related code: [现有展示层](../../../adapters/Dota2UID/src/Dota2UID/presentation.py)、[现有端口](../../../packages/dota2forge-core/src/dota2forge_core/ports.py)
Related docs: [项目规划](../../../Dota2Forge_PROJECT_PLAN.md)

## Problem
首个 QQ 文本查询闭环已通过。用户希望菜单和查询以图片回复，参考 StarRailUID，并增加历史对局中某一局的详细信息。旧顺序把 Renderer 放在 AstrBot、OpenDota 和重试之后，会使已可用数据的图片交互等待无关扩展；也未明确历史单局的选择方式。

## Decision
用户已要求记录这些功能；以下为实施顺序与边界记录。共享Renderer和基础详情代码已按已实施决策落地，未完成项仍由active任务跟踪。
- 优先让现有 Dota2UID 消费共享图片 Renderer：菜单/帮助、玩家卡、近期战绩卡，然后账号状态卡；保留纯文本提示与可配置文本模式。普通图片菜单展示命令，不当作已支持可点击按钮。
- Core 负责业务数据和规则，计划独立 dota2forge-renderer 包负责可复用排版与编码。绘图库/字体/图片资源不进入 Core 领域和用例，宿主事件/消息只在适配器；包结构、依赖和治理路径在实施时更新。
- 首轮采用 Pillow，参考 StarRailUID 的分类帮助与命令调用绘图/发送方式；资源和主题采用 Dota2Forge 自有设计，记录字体、英雄/装备图标来源和授权。静态英雄中文名与缺图占位先准备，复杂图表必要时再评估 HTML，不以完整浏览器运行时阻塞首版。
- 图片保留 None/0/False、来源、抓取时间与未知观测时间；默认北京时间、时长分钟/秒、英雄中文名。近期列表维持默认 10、1–100，出图有界分页，不以长图/无限图片轰炸会话；具体每页数量经样图确认。
- 最小历史详情紧随基础图片交互：新增独立详情端口/模型和严格 ID 用例，由 STRATZ 固定查询获取。保留原玩家/近期端口兼容，新增契约必须检查已实现 Dota2UID 和合成消费者。
- dota比赛 <比赛ID> 查询指定历史比赛，独立于当前 recent 的 100 场/10 页边界；上游无收录或未解析仍可能缺失，不宣称历史全覆盖。账号确实在该场参赛才显示我方视角。
- 战绩卡显示比赛 ID 与查询方式；后续 dota比赛 第N场 只能解析调用者最后一次有效结果。临时列表与机器人/会话/绑定账号关联，规定容量/有效期和改绑/重载失效；不重新取列表猜测序号，不把此临时选择状态冒充数据源缓存。
- MatchDetailCard 在详情 Provider 通过验证后接入；IMP、经济/购买序列另外增量验证，不阻塞基础十人/两队详情。之后 AstrBot 复用图片和详情能力，OpenDota、缓存/重试、订阅/AI 按原边界分别验收。
- 正常数据已取得而渲染失败，回退同次数据的文本，禁止补发 Provider 请求。数据源错误保持分类；图片发送失败不自动重发导致重复消息。

## Alternatives considered
- 先 AstrBot/OpenDota，再 Renderer：可走原顺序，但让当前 QQ 用户等待已有数据就能提供的图片体验。
- 两个适配器各复制绘图：主题、资源和缺失语义会漂移，选择共享包。
- 为每次详情查询全量抓历史：耗费限额且无法证明完整，选择比赛 ID 直接查；列表序号只是便捷入口。
- 一次实现详情/IMP/全经济曲线：字段可用性不同，先最小详情，逐项核对再扩展。
- 全部回复立即图片化或依赖按钮：失败时提示不可读/平台支持未验证，保留文本补充，按钮后续独立评估。

## Consequences
需要维护独立 Renderer、资源版本/授权、回复类型和详情模型；这些首轮边界已实现，列表选择为有界宿主状态。图标/装备资源授权、QQ压缩/发送/重载、IMP/经济和AstrBot消费仍需增量验收；没有自动重试、解析作业或跨源回退的授权扩展。

样图技术基线已采用（浅色主题、完整OFL字体、780px、5场/页）；实现细节见 [Renderer决策](../implemented/2026-10-01-shared-image-renderer.md)，样图历史见 [展示契约草案](2026-10-01-renderer-preview-contract.md)。真实平台验收不由本记录宣称通过。

## Verification
参考仓库 [StarRailUID](https://github.com/baiqwerdvd/StarRailUID/tree/739a80a26b7a137b6b7b7d45435c769822de06d0) 的帮助注册与Pillow调用方式已静态核查；其GPL-3.0-or-later元数据不作为复制代码/资产到本MIT项目。共享Renderer/详情契约/Provider与文本ID/序号/取页已独立实现，见三个implemented决策。原方案仍未完整实施：GsCore/QQ新图片功能与AstrBot消费未验证；普通测试继续禁网。
