# STRATZ英雄观察与宿主原生复盘首版

Category: feature
Related task: [首版实施](../../tasks/done/2026-10-14-stratz-feature-implementation.md)
Related code: [英雄用例](../../../packages/dota2forge-core/src/dota2forge_core/hero_features.py)、[复盘事实](../../../packages/dota2forge-core/src/dota2forge_core/review.py)、[GS原生工具](../../../adapters/Dota2UID/src/Dota2UID/host_ai.py.template)、[Astr入口](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host/main.py.template)
Related docs: [方案](../../../Dota2Forge_STRATZ_FEATURE_PLAN.md)、[分析契约](../../../docs/subsystems/analysis.md)

## Problem
用户授权实施版本强势、丰富攻略和正常多轮AI复盘。[来源证据](../../artifacts/stratz-features-v1/implemented.json)确认按位置/段位的winDay可用，但真实窗口缺日且滞后；攻略周桶的位置标记与请求不一致，guide.matchPlayer为空，技能level为零基技能阶数，不能画成英雄等级。

## Decision
Core新增不可变英雄观察/复盘事实、受限端口及共同参数解析；业务复用共享用例，平台身份与会话留在独立适配器，Renderer只消费本地数据。榜单按当前生效版本与近7/14天完整UTC日交集，累计胜场/场次后以Wilson95%下界排序，最低1000场，全部位置各2或指定位置前10；不计算未知分母的选用率，不补缺日、不平移窗口。

攻略聚合、样例、独立分母分开；不一致位置桶停用并标明scope_mismatch。样例使用guide的临时目标ID重新查询match.players并校验hero/position/account，身份不进入AI序列化或证据文件。嵌套ability解析遭上游拒绝，改用独立constants.ability按本场版本及S_CHINESE查询名称；失败保留源名/ID及label_error。加点按真实事件序号/时间，显示阶数从0起，不推断英雄等级；购买保留赛前负值、组件及重复，终局6+3+中立库存用来源快照。

AI使用宿主原生会话、模型及四个只读工具；Core不保存聊天，无嵌套LLM。首答/追问文字优先；图只按白名单曲线/购买数据生成，工具结果带入同一历史的文字事实。GS用临时资源交给宿主发送工具，Astr发送当前event一次，不接受模型目标用户、URL、路径或SQL。GS每轮hook仅在有效定位与相关追问时提示/保留复盘工具，不改全局persona。宿主AI不可用时提供事实/数据报告；仅绘图不可用时继续文字对话。

GS工具/提示/召回遵守宿主ToolScope.plugin_enabled与blocked_tool_names，visible_when保留persona权限，未授权出站子任务拒绝。Astr仅收紧已经获准工具的Schema，不重新授予被禁用工具。外部工具字段只作数据；本场版本名称未核实不能套用当前攻略。

每端会话定位128条、活动30分钟、绝对2小时，证据10分钟不由读取续期；证据过期仍用定位重新取证，重置/换会话/改绑/解绑/关闭清理。STRATZ所有能力共用一份HTTP与配额状态，不自动重试或切源。有界内存缓存：版本/榜单30分钟、攻略/标签6小时、样例1小时；复盘基础/经济统一5分钟，首版采用更保守短TTL，暂不区分已结束6小时。相同key合并、并发最多16、最后等待者取消即排空，关闭等待清理，无SQL变更。

GS bundled从本generation已校验runtime wheel读取固定AI桥接资源，在业务模块名下注册；关闭注销工具/hook与拥有的原生首轮任务，避免外部缓存helper保留旧Core类型。薄模式仍按已有冷启动升级协议。数据工具不申请录像解析。

## Alternatives considered
逐次要求比赛ID或插件复制聊天历史破坏多轮体验；强制图片报告增加干扰；无来源等级/库存推断会制造事实；静默接受位置异常会误导攻略；第二STRATZ实例会割裂配额状态。

## Consequences
首版只能依据已核实基础统计、经济和购买记录。死亡/团战/插眼事件、命石、任意时刻库存及可验证英雄等级仍未接入，必须区分推测与观察。聚合攻略暂因真实上游位置异常降级，样例可用。未生产发布或发送真实聊天。

## Verification
真实只读实现探针：7.41f、635个位置/英雄日桶、10项榜单；3个实际3号位攻略样例，独立中文技能名成功。凭据由忽略的.env注入，文件只存公开口径、数量/状态，没有账号/比赛ID或原始响应。生产Renderer的6张合成卡片及390px阅读QA通过，最高1780px/约0.19MiB。mypy102源文件通过；五包构建/隔离安装与双端候选离线消费通过。

真实GsCore注册器/Pydantic/hook与AstrBot4.28.2装饰器/ToolSet/ProviderRequest隔离验证通过，五轮取证、补图、重置/关闭使用合成会话；GS禁用persona与子任务出站拒绝通过，没有真实模型/平台消息。完整统一检查结果见[实施任务](../../tasks/done/2026-10-14-stratz-feature-implementation.md)及[证据说明](../../artifacts/stratz-features-v1/README.md)。真实会话验收另列[planned任务](../../tasks/active/2026-10-14-native-review-live-acceptance.md)，不将SDK桩当真实聊天通过。

最终统一入口exit0：2101项禁网测试/758.29s，聚合覆盖91.03%，scripts/Core/Assets分别94%/90%/92%；治理、Ruff、mypy通过。归档后仅复核文档链接/预算/生成漂移，运行源码与打包输入不变。
