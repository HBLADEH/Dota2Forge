# AstrBot 平台桥接与生命周期

Category: architecture
Related task: [AstrBot 任务](../../tasks/active/2026-10-02-astrbot-platform.md)
Related code: [AstrBot 适配器](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/)
Related docs: [AstrBot 接入步骤](../../../docs/cookbook/astrbot.md)

## Problem

AstrApplication 已能在无宿主 SDK 的环境消费 Core 和 Renderer，但 AstrBot 没有发现入口、配置边界、可信事件身份、图片消息转换或终止清理。现有骨架不能据此宣称普通用户安装即可运行。

## Decision

- 使用 AstrBot v4.28.2 的 `Star.initialize()` / `terminate()` 和命令过滤器；桥接写入main.py、metadata.yaml、_conf_schema.json、requirements.txt，库导入保持SDK-free。requirements让桌面版选择独立data/site-packages，不复制共享库进插件ZIP。
- Runtime 在初始化时读取宿主传入配置，创建专用 SQLite、单个 STRATZ HTTP 客户端和可选 AsyncRenderer；宿主事件的 platform、连接、机器人和用户字段经校验后生成 Core `PlatformIdentity`。@ 他人或无法确认身份时拒绝操作；缺失会话仅拒绝列表选择，仍允许直接查询。
- `dota战绩 第N页` 与 `dota比赛 第N场` 使用每个部署/平台连接/机器人/用户/会话独立的有界进程内列表；完整消息发送成功后才保存，十分钟过期、容量 128，改绑/解绑/停用/重载清除。
- 图片通过 AstrBot `Image.fromBytes()` 加入消息链；Renderer 失败返回同次 Core 数据文本，发送失败不重发。管理员状态/停用由 AstrBot 权限过滤器和事件权限双重确认。
- MenuCard/StatusCard新增可选adapter_label，默认保留Dota2UID，AstrBot显式设置品牌；检查两端已有消费者与Renderer测试。Core现有AccountId/SteamID64输入语义不改变，修正Core文档遗漏的SteamID64转换说明。
- 不在本次接入实现 AI Tool、Scheduler、订阅、OpenDota、来源缓存或自动重试；真实宿主联调单独记录。
- 宿主logger输出state/client_closed，无身份/Token/请求数据。共享库wheel更新需停用后冷启动；单纯桥接重载不能保证刷新外部Python模块，停用页面也不能作为关闭证据。
- 库顶层公开导出改为按需加载。桌面宿主递归展开wheel依赖后，按模块顺序清除/导入；提前导入Application会捕获旧Core/Renderer类，菜单触发类型校验失败。requirements去掉重复Core/Renderer声明，但依赖仍由wheel元数据展开，修复依赖于按需导出。

## Alternatives considered

- 让 AstrBot 直接导入 Dota2UID：违反适配器互不依赖，拒绝。
- 在宿主桥接中复制 STRATZ、SQLite 或图片逻辑：会造成 Core/Renderer 语义漂移，拒绝。
- 直接把 AstrBot SDK 加入普通依赖和测试：会使离线治理依赖宿主环境，选择 wheel 中的桥接模板和无 SDK 库测试。
- 使用宿主持久化保存最近列表：列表是会话交互状态，持久化会扩大隐私范围并跨重载复用，选择进程内有界状态。
- 仅删除requirements中的共享包：宿主会递归展开它们，仍发生类型冲突；改为消除适配器顶层的提前消费，保持Renderer的严格类型校验。

## Consequences

AstrBot 现在具备可安装桥接和离线可验证的首个宿主闭环，wheel 包含宿主模板但运行时依赖仍由 AstrBot 提供。身份隔离依赖宿主提供稳定的平台连接和会话字段；OtherMessage 仍可直接查询但不能保存分页选择。本机生命周期和菜单图片有独立实机证据，不能推断其他平台、查询卡片压缩或多实例路径全部通过。按需公开导出保持原导入接口，但不保证任意外部代码主动导入后手动清除依赖的类型一致性。

## Verification

核对v4.28.2源码；最终40项AstrBot消费者/桥接禁网测试（含独立进程两轮依赖重载）、Ruff/mypy41源文件、834项完整测试、聚合95.85%及独立覆盖率门槛、四包构建与隔离wheel通过。真实安装SDK检查11个命令过滤器、GreedyStr、重复初始化/关闭及依赖优先加载后菜单PNG通过。运行桌面版已发现/配置/冷启动插件，宿主重载后terminate明确stopped/client_closed=True，再启用ready；用户确认菜单、绑定、玩家、20场战绩、第3页和第1场详情正常且图片可读。直接ID和聊天管理员权限未实机验证，[证据](../../artifacts/astrbot-host-v1/README.md)。
