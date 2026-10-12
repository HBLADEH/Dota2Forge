# 订阅复用完整比赛报告卡

Category: feature
Related task: [订阅比赛详情卡](../../tasks/done/2026-10-12-subscription-match-cards.md)
Related code: [共享展示](../../../packages/dota2forge-renderer/src/dota2forge_renderer/subscriptions.py)、[UID Runtime](../../../adapters/Dota2UID/src/Dota2UID/runtime.py)、[Astr应用](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/application.py)
Related docs: [Renderer](../../../docs/subsystems/renderer.md)、[订阅](../../../docs/subsystems/subscriptions.md)

## Problem
用户确认订阅已触发，但比赛推送仍固定为简要文字，未消费已有总览与分队详情卡，且相同来源和抓取时间重复显示。订阅数据已经保存在不可变MatchReport中，无需重新查Provider。

## Decision
MatchReportCard追加可选subscription_event展示上下文，旧查询构造兼容。共享subscription_event_cards生成总览与所有实际分队页；subscription_event_text_pages生成完整报告的1400字符分段文本。订阅标识、订阅玩家、事件ID、来源时间、有限观察提示保留；IMP缺失保留已有KDA表现候选，不称官方MVP。相同来源时间只列一次；不同观察不合并。

缺优势曲线时订阅总览压缩空图表区域，保留明确未提供说明。分析参赛者null不显示为零，购买事件null注明未提供；显式空tuple保留零条，数量仅统计来源实际返回的观察。

双端订阅Controller仍负责claim/ack/retry，Runtime将内部文字回调转换为宿主无关的一组图片或文字回复。图片模式先完成全部渲染；仅RenderError回退同一快照的完整文本，无额外Provider请求。段位、日报、旧MatchSummary及无详情报告继续文本。渲染和整组发送持有既有消息锁，与素材替换、关闭协调，取消和程序错误传播。

GsCore薄桥接与bundled业务桥接同时消费新回复组，转为普通Message列表并调用一次target_send(wait_recall=True)；避免node/markdown引入额外分帧。AstrBot OneBot显式self_id的一次call_action包含所有文本或base64图片段。发送前检查连接、目标和当前Bot管理员；发送失败不补发文本，未知或异常回执不ack，保留既有人工重试边界。

现行Renderer a6、UID a13、Astr a11已有公开产物，新增必需接口不能继续允许安装旧Renderer。开发版本升级Renderer a7、UID a14及Astr a12；双端依赖下限为Renderer a7。Astr直装消费者直接复制host模板，同步其metadata/requirements；发行生成器仍动态读取包元数据。Core/Assets不升级，不发布或覆盖原产物。

## Alternatives considered
独立画简化订阅卡会遗漏已有详情并产生两套布局，选择复用比赛报告。逐页渲染发送会使后页渲染失败产生部分图片与文本混发，因此先准备整组。宿主逐页调用无法用一个回执确认事件完整提交，选择单次消息调用；调用返回不等于客户端视觉送达。

## Consequences
完整十人报告通常三张1600px宽卡，流量高于原文本；平台压缩和消息大小仍需真实聊天验证。文字模式比原摘要详细。Core模型、Provider、数据库schema、授权、检查点和发送占用语义不变；公开发布及生产部署另需任务授权。本轮仅使用合成数据，不保留用户账号/比赛/事件原文。

## Verification
专项覆盖双端整组准备、后页渲染失败、文本完整性、缺详情/段位/日报、取消和程序错误、素材替换/关闭等待；相同宿主sender契约覆盖UID两种桥接及AstrBot单调用/回执。统一检查与合成视觉结果记录于关联任务；真实SDK发送和聊天压缩未验证。
