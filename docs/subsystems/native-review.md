# 原生多轮比赛复盘

开发候选已实现SDK外业务与两端原生入口。用户自测截图确认GsCore群聊@后连续追问和图片可用；代理未发送真实消息，AstrBot及完整生命周期验收仍未验证。宿主负责模型、预算、对话历史和发送权限；插件不新增模型配置，不保存聊天，不用每轮临时LLM冒称多轮。

## 事实与用例
`ReviewService`通过详情/分析端口取A/B层观察，`ReviewEvidence`保留同比赛同来源的详情、经济、购买、目标slot和分析错误。英雄需本场唯一匹配；未指定英雄时可用可信调用者绑定偏好，无匹配则双方概览，不猜参赛身份。分析关联校验slot和公开账号一致；错误不混接，基础事实仍保留。序列带单位、语义和真实时轴，STRATZ净资产不是OpenDota累计金币；天辉优势有符号且起点-60秒。终局补刀不可解释成对线期补刀。

`evidence_data`删除账号/昵称/聊天身份，只含英雄、slot、位置、来源、时间、计量事实和局限，附内容摘要evidence_id。工具不执行外部文本指令，不把旧AI判断或攻略样例当新事实。未接入死亡/团战/插眼、轨迹或录像操作事件，无法判定操作因果。Core不调用LLM。

## 四个只读工具
`get_dota2_meta`接受受限位置、段位、7/14日、可靠度/胜率；`get_dota2_hero_guide`接受英雄、位置、可选比赛ID；`get_dota2_review_context`接受可选比赛ID/英雄与overview/economy/items/laning/team主题；`render_dota2_review_data`只接受economy/team_advantage/items和有界比赛秒数。所有工具拒绝额外字段及模型身份、URL、SQL、路径。画图区间不得超过本局时长，开始可最低-600秒，结束0在宿主桥接表示实际时长。仅查询/渲染，不申请解析、不嵌套LLM。

攻略工具各统计桶最多64/32/16项、样例购买最多128条，携带总数与选择说明，独立分母不合成为整套胜率。原生工具返回JSON事实，图片对应文字事实随同一次工具结果进入宿主历史，不再手工复制一次历史或要求OCR。图片不是AI生成的想象图，只画已取证事实；没有序列/购买时显示缺失。图失败可继续文字；发送失败不盲目重试。

## 适配器会话
会话键由可信调用者、机器人/连接、群/私聊和宿主原生conversation/session构成；模型不能构造它。定位128份，活动30分钟/绝对2小时，证据10分钟不读取续期；有效定位在11分钟可重新取得来源，不要求重新输入ID。基础/经济来源缓存均5分钟，相同请求有界合并。每次工具重新校验绑定，改绑/解绑立即清理；会话换ID、同ID宿主代际变化或历史重置清理，关闭排空拥有的任务、缓存和Renderer。

GsCore注册common工具，使用可信ToolContext、主对话原生session对象；每轮AFTER_CONTEXT提示和ASSEMBLE_TOOLS召回只作用于有效定位/相关追问，不写全局persona，不强灌天气等无关问句。图片由宿主临时RM资源交给发送工具；未授权出站的子任务不可调用复盘上下文。工具/hook注销及原生首轮任务清理纳入bundled代际协议。

AstrBot使用原生conversation_manager和event.request_llm(conversation=...)；后续走正常聊天管线。工具由官方Args文档注册，on_llm_request用共享显式JSONSchema限定已获准工具，保持persona禁用策略；图只发送当前可信event一次。当前4.28.2接口已核对；缺少会话/模型能力时返回事实或可选数据报告，绘图缺失不降级整段多轮聊天。真实宿主连续性/模型兼容仍需部署后验收。

原因见[决策](../../.agents/notes/implemented/2026-10-14-stratz-hero-and-native-review.md)，操作见[复盘指南](../cookbook/native-review.md)。

GsCore H14不填query，桥接以同一可信event.raw_text补齐，相关追问钉数据工具并提示先取本主题事实。@/主动回复策略仍由宿主控制。首答至少一项字段依据和建议，实际模型遵守情况待自测。[反馈修正](../../.agents/notes/implemented/2026-10-15-stratz-followup-and-card-fixes.md)。

共享提示要求补图后仍回答实际问题，出装调整给条件建议；优势曲线不能证明团战从未获胜/个人责任，净资产斜率不等于GPM，引用数值需核对本轮字段与采样时间。工具limitations同步净资产/因果边界。提示不等于输出正确性保证：用户截图仍出现数字前后不一致和过度归因，模型质量需人工评估，见[本轮决策](../../.agents/notes/implemented/2026-10-15-guide-icons-and-talent-labels.md)。
