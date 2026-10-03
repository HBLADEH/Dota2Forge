# OpenDota 独立观察与显式交叉核验

Category: data
Related task: [OpenDota任务](../../tasks/done/2026-10-02-opendota-provider.md)
Related code: [Provider](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/opendota.py)
Related docs: [来源契约](../../../docs/subsystems/opendota.md)

## Problem
STRATZ主源与双端接入已有实机证据，规划Step10要求独立补充和交叉核验。OpenDota的significant默认筛选、解析version及字段缺失与STRATZ不同；把另一来源结果自动拼接或当作失败回退会隐藏段位滞后、历史范围和隐私差异。

## Decision
- 新增OpenDotaProvider，复用已有PlayerProvider/MatchProvider/MatchDetailProvider，客户端/时钟显式注入并由调用方关闭。Core基础安装无HTTP依赖，新增opendota extra；不更改运行Bot的STRATZ配置或来源。
- 查询固定公开HTTPS的GET端点；近期最多100场，显式significant=0、sort=start_time和统计列project，一次请求后按时间/ID排序，不补齐未知历史。null、空、缺失、非法响应分别处理；匿名哨兵/未知账号不携带昵称。
- OpenDota version保存为MatchDetail末尾可选parse_version，旧构造不变；正数是上游解析格式证据，0/null不证明未解析，按已观察字段保留部分/未知状态。公开schema只定义内部解析版本，源码的完整性判断还需多个字段，不能把version缺口等同isStats=False。has_stats仍为STRATZ的isStats，version不是game_version_id或游戏补丁；模式暂保留OPENDOTA_<整数>，不猜测跨源枚举。Renderer及两个文本消费者展示各来源的真实标记。
- 分钟/日剩余额度读取真实响应头，按已核对上游窗口与Date计算等待，不硬编码免费配额。429未知重置时当前实例停止发送，需调用方重建；有限超时、取消传播、不自动重试。移除注入客户端继承的认证、Cookie与查询默认值，避免主源凭据被带往公开补充源。
- CrossCheckService只依赖新增组合Protocol，不改变旧端口/服务构造。顺序请求两份来源，各自保留成功、固定错误或因主源明确PRIVATE而未请求；取消/程序错误传播。None不可比较，两份0/False仍可相等；仅对共有比赛ID比较可归一化字段，来源独有ID不表示另一来源历史中不存在。无胜者、无字段拼接、无降级为成功。

## Alternatives considered
- 自动换源或取最高段位：会把滞后值和口径差异隐藏，拒绝。
- 将OpenDota version映射为STRATZ isStats或game_version_id：指标意义不同，保留独立解析证据。
- 给所有消费者改造必选构造参数：保持旧端口，新增独立核验服务并回归双端/Renderer。
- 依据403/404或空近期猜测PRIVATE/NOT_FOUND：代理响应和上游隐藏历史不可区分，分别保留UNAVAILABLE或有效空结果，不推断原因。

## Consequences
SDK可显式使用补充来源及比较结果，运行Bot继续使用STRATZ；尚未注册补充源/核验命令。比较只描述两次观察，不证明当前段位、字段完整或全历史一致；观测时间/补丁无法核实时为空。新增可选解析版本与来源标记，旧STRATZ数据语义保持。

## Verification
核对2026-10-02公开OpenAPI31.1.0及odota/core commit295a76ecdcbe90345fc6373a005280353bac015e的API、spec、playerFields、web/time限流与utility完整性判断。最终80项新增禁网合成测试、914项完整测试（95.97%）及Core/治理独立门槛通过；Ruff/mypy45源文件、四包build/smoke及git diff --check通过。两端/Renderer保留STRATZ提示并显示OpenDota版本，未删旧断言；新wheel临时目录真实SDK依赖加载与关闭通过。未查询真实账号、未安装到运行宿主、无在线Provider或新Bot命令验收。
