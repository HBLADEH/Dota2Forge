# OpenDota 补充与交叉核验契约

[OpenDotaProvider](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/opendota.py)实现现有玩家、近期和详情端口，[CrossCheckService](../../packages/dota2forge-core/src/dota2forge_core/cross_check.py)显式读取两个来源；默认Bot仍为STRATZ。两个适配器互不依赖，不由平台SDK访问补充API。

## REST与归一化

核对基线为2026-10-02的[公开OpenAPI](https://api.opendota.com/api)31.1.0及[odota/core源码](https://github.com/odota/core/tree/295a76ecdcbe90345fc6373a005280353bac015e)。固定GET /players/{account_id}、/players/{account_id}/matches、/matches/{match_id}；不使用Key、不发解析/刷新作业、不读取环境，客户端由组合入口准备/关闭。

资料核对profile.account_id、保留personaname/rank_tier；profile=null允许已知段位与未知昵称并存，不据fh_unavailable判断整个账号不可查。近期请求limit1–100、significant=0、sort=start_time，显式project基础统计/GPM/XPM列；player_slot0–127为天辉、128–255为夜魇，结合radiant_win算胜负。排序新到旧；重复、过量、错账号和必要ID/开始时间缺失失败。空数组有效，不证明历史无战绩或账号公开。

详情保留开始/时长/胜方、阵营、匿名身份、KDA/GPM/XPM与六装备槽。独立分析端口另保留 `gold_t`、`xp_t` 和 `purchase_log`，语义分别是收集金、经验累计和购买事件；不当作STRATZ净资产或IMP。0/False不当作缺失，匿名账号0/4294967295与null未知账号不携带昵称。players的缺失/null、空数组和不足十人可区分；重复槽位/账号失败。显式null详情为MatchDetailUnavailable/MatchAnalysisUnavailable，原因/隐私未知；错误不降级为空。

MatchDetail新增末尾可选parse_version，保存OpenDota解析格式version，非补丁或STRATZ game_version_id。仅OpenDota正数派生UPSTREAM_PARSED；0/null不证明未解析，仍按已观察字段派生PARTIAL/UNKNOWN并保留原值。has_stats/parsed_at/game_version_id不从version猜测；game_mode使用OPENDOTA_<整数>保留原编号，未知补丁/观测时间为空。Renderer与两个文本消费者分别展示OpenDota version或STRATZ isStats，解析标记不保证详情完整。

## 错误、额度与所有权

HTTP401为AUTHENTICATION、429为RATE_LIMITED；其余非200（含403/404）为UNAVAILABLE，不能从代理状态证明隐私/不存在。非法JSON/类型/模型及200的error对象为INVALID_RESPONSE。不记录响应正文或身份；意外错误/取消继续传播。

同实例串行读取X-Rate-Limit-Remaining-Minute/Day；剩余小于等于0按上游分钟/UTC日窗口和Date限制后续请求，Retry-After保留较长等待。未知429重置停止当前实例发送，由调用方明确重建；不猜等待、不自动重试。timeout有限正数至多60秒，重定向关闭，继承的认证/Cookie/查询默认值移除。实例不关闭注入客户端，无后台轮询、来源缓存或解析任务；跨进程/IP配额需宿主负责。

## 显式核验

CrossCheckService接收两个不同来源的ObservationProvider，提供get_player/get_recent_matches/get_match_detail。SourceObservation分别记录source、SUCCESS/FAILED/SKIPPED_PRIVATE、原归一化值或ProviderFailure的固定code/等待。主源明确PRIVATE时不请求补充源；其他分类错误保留且独立读取第二源，错误来源不匹配视为INVALID_RESPONSE。取消/程序错误终止，不转换成成功。

FieldComparison对None为UNKNOWN；两个已知值相等为AGREE，否则DIFFERENT。玩家比较昵称/段位，近期仅比较共有ID的基本统计，only_primary_ids/only_secondary_ids记录本次列表差异；详情比较开始/时长/胜方。解析版本、源枚举、匿名身份不强行比较。无主源值替换、字段拼接或完整历史推断，抓取时间与来源始终保留。

## 验证范围

普通测试禁网，使用合成HTTP验证既有Core服务、两端文本和真实本地Renderer消费；新来源尚未在线查询或部署到Bot。操作见[SDK步骤](../cookbook/opendota.md)，原因见[决策](../../.agents/notes/implemented/2026-10-02-opendota-cross-check.md)，真实检查见[任务](../../.agents/tasks/done/2026-10-02-opendota-provider.md)。
