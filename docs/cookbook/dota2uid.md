# Dota2UID 本机接入

[适配器](../../adapters/Dota2UID/src/Dota2UID/runtime.py)复用Core用例；普通导入不联网、读配置或注册命令。显式安装器将包内模板写入宿主插件目录。

## 安装与配置
先完成[开发检查](development.md)并uv build --all-packages，在GsCore环境安装同次Core、Renderer和dota2uid[stratz] wheel（允许0.1.0a2预发布）。stratz extra需要HTTPX，Renderer需要Pillow；本阶段不上传包索引。

同版本重建须明确wheel路径并禁用缓存，在workspace运行：

~~~powershell
$gsPython = 'D:/bot/gsuid_core/.venv/Scripts/python.exe'
uv pip install --offline --no-index --no-deps --no-cache --python $gsPython --reinstall dist/dota2uid-0.1.0a2-py3-none-any.whl dist/dota2forge_core-0.1.0a2-py3-none-any.whl dist/dota2forge_renderer-0.1.0a2-py3-none-any.whl
~~~

上例要求HTTPX/Pillow已安装；首次补依赖可能联网。相同版本号不证明内容更新。升级前stop确认关闭并退出宿主，备份配置/两库/入口再安装、冷启动。Pillow DLL须停机更新，见[恢复记录](../../.agents/notes/implemented/2026-10-02-gscore-wheel-recovery.md)。

首次安装桥接：

~~~powershell
uv run --env-file .env --locked python -m Dota2UID.install --host-root D:/bot/gsuid_core --token-from-env
~~~

安装器创建发现桥接和专用配置，不加载/重启宿主、不覆盖已有不同内容；--token-from-env 注入本机凭据，不输出Token。首次Runtime启动也可独占创建空配置：合法但空Token为awaiting_config，填写后停用/重载；非法配置仍failed。已有配置不自动改写，发行候选见[步骤](plugin-release.md)。

配置以 [空模板](../../adapters/Dota2UID/config.example.toml) 为准：namespace 是部署隔离标识，stratz_token 为本机密钥，timeout_seconds 为 0–60 范围内的有限正数。platforms 的键必须对应可信 Event.bot_id；值为 Core 平台标识。默认 onebot/qq→qq、telegram→telegram，其他标识需核实后显式添加。机器人账号使用 Event.bot_self_id，不是 bot_id 或 WS 连接号。

绑定数据在相邻的 bindings.sqlite3，宿主需目录读写权限。不要上传配置、SQLite 或聊天记录。不接 GsCore 多 UID 表或双写；每个部署/平台/机器人/用户仅一个账号。

## 命令
| 命令 | 行为 |
| --- | --- |
| do帮助 | 显示用法 |
| do绑定 ID | 绑定自己；重复相同 ID 幂等，其他账号拒绝覆盖 |
| do改绑 ID | 显式替换自己的绑定 |
| do账号 / do解绑 | 查询是否绑定 / 幂等解绑 |
| do查询 [ID] | 查询玩家及[预估MMR](../subsystems/ranks.md)，不改绑定 |
| do英雄名出装 | [热门出装](hero-items.md)，免绑定 |
| do战绩 [条数] | 查询自己，1–100 默认 10 |
| do战绩 ID 条数 | 查询指定账号，不改绑定 |
| do比赛 比赛ID | 直接按 ID 查历史单局，不要求绑定或出现在近期列表 |
| do比赛 第N场 | 使用当前会话最后有效战绩的绝对序号，1–100 |
| do战绩 第N页 | 读取同次返回结果的第 N 页，不重新查 Provider |
| do停用 | 仅宿主主人权限 0；关闭运行期资源，权限 1 不可执行；WebConsole 管理员使用下文接口 |

ID 接受规范 Dota account ID/SteamID64 数字，不解析 URL/vanity/@他人。绑定不证明账号所有权。未知统计显示未知，0 与负场有效；分段回复保留 STRATZ 来源、抓取时间和历史不完整提示。不会把认证/限流/HTML 拦截或陌生 GraphQL 错误展示成无战绩。

比赛 ID 独立校验为 1–9223372036854775807 的规范十进制，不接受 URL/前导零；第N场是独立序号语法。详情文本按实际阵营分段，保留未知字段、解析标记、版本 ID 和北京时间 UTC+8；匿名/未知账号不展示身份，只有绑定账号确实参赛才标我方。无详情时原因/隐私未知，不宣称不存在或私密。

战绩每页五场，最多先发两页；11–100场可显式取第3–20页。序号用最后完整发送列表，取页不重查Provider；无绑定可用显式账号列表。状态按部署/平台/机器人/调用者/连接和群或私聊隔离，容量128、TTL10分钟，读取不续期；改绑/解绑、连接变化、停用/重载失效。缺失会话及channel/sub_channel拒绝选择；直接ID不依赖列表。用户已确认基础图片、第二页、序号和直接ID详情；10-02停用/重载后复测图片回复正常、文字可读。

`reply_mode`默认image（含旧配置省略），text为纯文本；图片限制/关闭/回退见[Renderer契约](../subsystems/renderer.md)，官方资源见[素材目录配置](illustrations.md)。

## 生命周期

[a7后台配置](gscore-configuration.md)仍须停用后重载。
start_before阻塞初始化，start与首个命令幂等检查就绪，支持热安装。失败锁定failed，修复后显式重载。运行期共用一个HTTP客户端，复用STRATZ/OpenDota Provider；不逐条重建或限流后自动重载。

发现桥接传入 Event.user_type/group_id，使用 Runtime.dispatch 串行查询和发送；完整回复发送成功后才记住列表。失败不重发，不覆盖上一有效列表；有效空结果会替换旧列表。最多接纳16个dispatch；停用取消在途查询/发送并清空选择状态。handle只生成文本，不能确认聊天发送，不创建可选择列表。桥接变更仍须先stop后替换/重载；平台实际递送和部分消息撤回不由返回值保证。

Runtime 日志只记录生命周期、命令名、回复/图片数量、图片尺寸与字节数、渲染回退、发送完成/失败/取消和列表提交；不记录账号、群号、用户号、昵称、消息正文、图片内容或凭据。QQ 窗口不可操作时，用户可按任务逐项执行命令并反馈视觉结果，日志用于核对服务端是否准备/发送完成，不能替代客户端压缩后的可读性确认。

管理员通过宿主头鉴权访问 GET /api/dota2uid/status，返回 state/client_closed。使用 POST /api/dota2uid/stop 停止接收新业务并关闭客户端；响应 stopped 与 client_closed=true 后，才使用宿主 POST /api/plugins/Dota2UID/reload。鉴权由 GsCore require_admin_header 执行，插件没有匿名管理入口。

卸载顺序：先 stop 成功，再用宿主删除发现目录，最后重启清除宿主残余触发器/模块。保留 data/Dota2UID 便于恢复，删除绑定数据另需明确授权。GsCore 0.11.0 此版本的原生 reload 不执行旧 shutdown，原生 uninstall 不清运行态；不能跳过 stop 或宣称直接删除目录能自动释放资源。宿主进程退出会调用同一关闭函数。在途查询取消传播；SQLite 工作线程的写入取消不保证回滚。

## 验证

订阅默认关闭，配置/权限/重试与停用步骤见[指南](subscriptions.md)。
普通测试禁网且不安装宿主 SDK：

~~~sh
uv run --locked pytest tests/dota2uid --cov-reset --cov=Dota2UID --cov-branch --cov-fail-under=80
~~~

测试使用合成宿主桩。09-30热加载、受控重载、卸载/重启及冷启动见[首轮任务](../../.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)。10-02两轮stop/reload后ready/image、配置/绑定库不变，用户确认QQ菜单、账号和详情图片可读，[证据](../../.agents/artifacts/gscore-image-lifecycle-v1/README.md)。仅验证单会话，STRATZ边界见[Provider操作](stratz.md)。

10-05匹配a2运行库与do桥接已部署ready/image，配置/两库/558素材保持；SDK注册与合成卡通过，[证据](../../.agents/artifacts/gscore-current-deployment-v1/README.md)。控制台200、匿名状态401，无客户端连接；联调须选定入口避免两端do重复回复，真实聊天及[截图](plugin-showcase.md)待补。
