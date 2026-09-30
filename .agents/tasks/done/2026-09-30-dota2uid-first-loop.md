# Dota2UID 首个宿主闭环

Status: done

## 目标
在已核实的 Windows 原生 GsCore 上，让可信平台身份经过 Dota2UID 调用 Core 绑定与查询用例，再由适配器生成消息。

## 非目标
修改 GsCore 框架、复制 Core 业务、真实群发、AI Tool、订阅、图片战报和自动部署。

## 验收
- [x] 实现可安装的发现桥接并在 plugins 路径构造 SV；普通库导入无 HTTP、配置读取和宿主注册。
- [x] 从可信 Event 获取平台/机器人/调用者，配置固定部署隔离；拒绝缺失身份与 @ 代办，不从命令接受写入目标身份。
- [x] 复用 Core SQLite 四维隔离、幂等和显式改绑，不接宿主多 UID Bind，不双写。
- [x] 离线覆盖首次启动/热安装/受控重载/停用、初始化失败门禁、并发初始化、在途取消和关闭等待取消；真实生命周期单列下一项。
- [x] 普通测试禁网、无宿主 SDK/凭据，覆盖输入、身份、错误、消息、安装及资源管理。
- [x] 在运行中的真实宿主核实命令注册、首次热加载、受控重载、卸载清理及恢复后冷启动；用户完成 QQ 单会话帮助/绑定/玩家/战绩实测。
- [x] 消费 STRATZ 主源，附来源/抓取时间，保留下降段位及 None/0/False；失败不换源、不伪装为空。

## 影响模块与决策
[Dota2UID](../../../adapters/Dota2UID/)、[Core](../../../packages/dota2forge-core/)、[宿主基线](../../../docs/subsystems/gscore-host.md)、[组合决策](../../notes/implemented/2026-09-30-dota2uid-composition.md)、[操作步骤](../../../docs/cookbook/dota2uid.md)。

## 验证证据
用户授权实机验证并完成管理员登录；使用正常管理接口，未绕过鉴权。以下时刻均为 2026-09-30 Asia/Shanghai。

2026-09-30，保留开工前修改，读取根/适配器规则及宿主插件开发指南。核对 GsCore 0.11.0 / Python 3.13.2、源码 87c06f11ae10c12b3bb8e76b3c6f420c831282a8。原生 reload 不运行旧 shutdown，uninstall 仅删除目录；采用受控停用流程，不修改宿主核心。
- 统一检查：487 项禁网测试通过；Ruff、mypy（24 源文件）、Core 与 scripts 独立 80% 门槛通过。Dota2UID 80 项测试、独立语句/分支覆盖率 94.88%，默认 pytest 已纳入适配器覆盖率采集。
- 三包构建及独立无索引 wheel 安装导入通过，确认 Dota2UID 命令模块与发现模板在分发包中。
- 已向 D:/bot/gsuid_core/.venv 安装 dota2uid[stratz] 与 Core wheel，放置 plugins/Dota2UID/__init__.py 及本机 data/Dota2UID/config.toml，未改宿主源码。首次 uv 按同版本号复用旧骨架，已改用显式 wheel 路径和 --no-cache 强制安装并验证；smoke_wheels 加入防缓存与新模块/模板断言，需维护者评审。
- 在宿主 Python 3.13.2 中独立执行已安装 Runtime，以合成调用者、临时 SQLite 查询获授权账号，资料显示来源正确、close 后 stopped/client_closed=true；未发送聊天，未记录昵称/账号/原始响应。这是适配器库联调，不是运行中宿主钩子通过。
- 20:08 首次热加载 HTTP 200，状态 ready、client_closed=false，2 个 SV 共 8 个命令；匿名状态请求 401。
- 20:09 停用 HTTP 200，stopped/client_closed=true；随后原生 reload 成功，20:10 恢复 ready，仍为 8 个命令，无重复注册。
- 20:11 再次停用后原生卸载成功，发现目录消失；原进程仍保留 stopped 路由/命令，证实必须重启清理。配置与 SQLite 文件指纹不变。
- 20:12 通过正常管理接口重启（is_send=false），PID 818304 → 817636；20:13 状态路由 404、命令列表为空，卸载清理通过。
- 恢复原发现入口，20:14 再次重启，PID → 725400；20:15 冷启动后 ready、2 个 SV/8 个命令，匿名 GET 状态与 POST 停用均 401。最终配置/SQLite 指纹及入口内容与备份一致，插件保持加载。
- 使用本机临时静态验证页复用已登录 GsHub SDK 调用接口，未保存或输出会话凭据；脱敏事件和截图保留在本机被忽略目录，验证页随后移除。未发外部聊天、提交或推送；宿主源码无保留改动。

## 阻塞与下一步
2026-09-30 用户自行通过 QQ 发送 dota帮助、dota绑定、dota玩家、dota战绩 3，并确认均正常回复。所附截图直接佐证玩家与 3 场战绩回复，包含段位、胜负、K/D/A、GPM/XPM、时间及 STRATZ 来源；帮助/绑定以用户确认为据。截图、昵称、账号 ID 和真实战绩未入库。这是单账号/单会话成功样本，不代表全部平台或异常场景通过。

本任务完成，QQ → NapCat → NoneBot → GsCore → Dota2UID → Core → STRATZ 闭环已验证。运维先 stop 确认关闭再 reload；卸载后重启清理残留。多账号、在线额度耗尽、长期稳定性尚未验证；OpenDota、详情/IMP、缓存、重试与自动回退未实现。
