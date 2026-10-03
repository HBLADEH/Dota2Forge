# Step13 接线、安装与冷启动证据

2026-10-03（北京时间），用户授权宿主关闭后更新并重启。开始及安装前进程/监听检查均未发现GsCore或AstrBot运行；NapCat保持不动。未查询真实账号或发起真实消息。

## 离线与构建

统一入口1123项禁网测试通过，聚合覆盖92.68%、Core独立92%、治理工具97%；Ruff格式/lint、mypy60源文件、治理预算/链接通过。四包构建、无索引/无SDK的四份独立wheel安装导入与git diff --check通过。新增玩家/指定比赛MatchReport、详情分析快照和schema v3回归。日志仅为合成测试输出：[统一检查](offline-check.log)。

普通/管理员菜单分别780×1450/1580、168152/173348字节，390px视觉检查无裁切、命令和权限提示可读：[普通](menu-390.png)、[管理员](menu-admin-390.png)。不是聊天客户端压缩后的视觉验收。

## 实际SDK

[AstrBot检查](check_astr_sdk.py)使用宿主CPython3.12.12、SDK4.28.2、临时ASTRBOT_ROOT与合成Token，真实依赖优先加载器后17个CommandFilter注册（含别名为19个命令名），GreedyStr完整参数、菜单PNG、重复initialize/terminate通过；唯一订阅timer创建后被取消/等待，client_closed=true。

[GsCore检查](check_gscore_sdk.py)使用宿主CPython3.13.2，gsuid_core.__version__报告0.10.7；不覆盖历史文档版本口径。真实gsuid_core.aps/安装版APScheduler注册/移除、max_instances=1/coalesce、两轮独立Runtime启停及client_closed=true通过。该脚本只替换SDK配置/日志依赖为桩，避免读取真实配置；未启动第二个宿主或发送消息。实际target_send参数从本机SDK源码核对。

## 停机安装与重启

21:49:51在两端专用数据目录backups/step13-match-reports-20261003-214951备份各自发现桥接、配置和绑定库。备份包含本机敏感配置，不在仓库保存。使用明确wheel、no-index/no-deps/no-cache安装各自三个包；未升级Pillow12.3.0、HTTPX0.28.1或其他依赖。

发现桥接/配置schema更新。GsCore模板原有混合CRLF/LF已统一后重建和安装；没有通过放宽匹配门槛掩盖差异。[逐文件核对](verify_install.py)确认六份安装包内容及双端桥接均与构建/源码完全一致。启动前原配置和绑定库字节指纹均不变，Token未读取到输出。

随后隐藏启动同一GsCore模块入口与AstrBot桌面入口。GsCore记录state=ready/subscriptions_enabled=True/job_registered=True，监听8765；AstrBot记录state=ready，后端监听6185。两端订阅库已从schema2迁移到schema3，订阅/outbox/attempt均0。当前开关由用户指定两端分别使用。没有向未知会话发消息。

## 未验收

两端已启用且分别使用，各自不跨库去重。真实群权限、玩家/指定比赛完成报告、段位/日报推送、失败人工重试及客户端可读性仍需用户发起测试。SDK/离线桩不能代替真实消息。GsCore通用gs_subscribe管理页未接入，兼容原因见[决策](../../notes/implemented/2026-10-02-subscription-delivery.md)。进度见[任务](../../tasks/active/2026-10-02-subscriptions.md)。
