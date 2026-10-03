# Step13 订阅系统

Status: active

## 目标
交付Core新比赛/段位变化/北京时间每日有限观察、双端命令/权限/受控调度及持久化投递尝试。用户授权继续，并要求Bot关闭后修改安装重启；保留既有工作区，无提交或新分支。

## 非目标
不做AI、跨源回退、精确MMR、完整历史或exactly-once。不猜真实投递对象或代发聊天消息；推送需用户主动订阅/授权。两端独立库不跨平台去重，配置默认关闭。

## 验收
- [x] 订阅快照、身份/路由/来源隔离、检查点CAS与同事务outbox；首次非空比赛/已知段位静默基线。
- [x] schema v3发送前原子claim，不确定/失败/取消跨重启保留，人工retry；v1/v2严格校验后事务迁移，损坏回滚。
- [x] 北京时间半开日期、最多100场、胜负未知和窗口不足可区分；无历史批量补发，报告日期去重。
- [x] 双端六个订阅入口、当前Bot管理员群权限、可信路由复核；改绑/解绑先撤销全部旧订阅再写绑定。
- [x] 玩家recent完成对局转MatchReport；指定比赛完成游标、详情/分析快照、非官方表现候选和schema v3迁移。
- [x] 宿主显式唯一timer/job，有限分页/公平投递、配额暂停；先取消等待再关客户端/Renderer。禁网桩验证重复启停。
- [x] 最终统一禁网检查、四包构建/隔离wheel导入及菜单视觉QA。
- [x] 关闭宿主后备份/安装/重启，真实SDK注册与宿主ready证据。
- [ ] 用户确认菜单/命令与真实比赛、段位、日报推送、群权限及stop/reload；非OneBot的AstrBot主动推送未实现。

## 影响模块与决策
[Core](../../../packages/dota2forge-core/)、[Dota2UID](../../../adapters/Dota2UID/)、[AstrBot](../../../adapters/astrbot_plugin_dota2forge/)、[Renderer](../../../packages/dota2forge-renderer/)、[契约](../../../docs/subsystems/subscriptions.md)、[首轮决策](../../notes/implemented/2026-10-02-subscription-outbox.md)、[投递决策](../../notes/implemented/2026-10-02-subscription-delivery.md)。两端消费者均检查，不改policy、工作流或治理脚本。

## 验证证据
首轮1057项禁网测试通过。接续最终统一检查1123项通过，聚合92.68%、Core92%、治理工具97%；Ruff/mypy60文件、治理预算/链接、四包构建和四份隔离wheel导入通过。本轮新增MatchReport、指定比赛游标、详情/分析持久化和双端命令回归；最终治理检查已再次通过。

2026-10-03安装前宿主已退出；NapCat不动。21:49:51在两端本机数据目录备份桥接/配置/绑定。六份安装包与两端桥接逐文件匹配构建/源码；原配置和绑定启动前指纹不变，未升级无关依赖。冷启动后两端ready，监听8765/6185；两端订阅库schema3且为空。配置按用户要求两端分别启用，GsCore记录job_registered=true。实际SDK检查：GsCore报告0.10.7/APScheduler注册移除，AstrBot4.28.2真实加载器17个CommandFilter与唯一timer取消；均client_closed=true、无真实消息。详见[脱敏证据](../../artifacts/subscriptions-host-v1/README.md)。

## 阻塞与下一步
两端已按用户要求分别启用。剩余：真实群权限、玩家/指定比赛完成报告、段位/日报与人工重试、客户端可读性，需要用户发起订阅并反馈。任务保持active，不代发到猜测会话。非OneBot的AstrBot主动推送未实现。
