# AstrBot 4.28.2 首轮接入证据

2026-10-02，本机桌面版 AstrBot 4.28.2 / CPython 3.12.12。源码位于 `D:/AstrBot/backend/app`，运行根为用户 `.astrbot`；插件发现桥接位于 data/plugins/astrbot_plugin_dota2forge，三个本地wheel安装于data/site-packages。宿主原有httpx0.28.1/Pillow12.3.0满足依赖。本文件不包含密码、Token、完整身份或聊天记录。

## 离线与SDK

AstrBot交付基线通过Ruff format/lint、mypy41源文件、834项禁网测试、聚合95.85%、治理工具约97%与Core约99%的独立80%门槛。AstrBot消费者/宿主桩40项；四包构建和无SDK/无索引隔离wheel安装导入通过。发现ZIP重新生成并核对四份资源，本机安装版在该基线逐文件匹配源码。后续OpenDota增量未部署到运行宿主；其新版wheel另在临时目录使用真实SDK验证注册、依赖重载后菜单PNG及重复关闭，不将此当作新宿主消息验收。

[SDK检查脚本](check_sdk.py)在宿主Python中显式运行，使用synthetic-token、临时ASTRBOT_ROOT和独立对象，不启动Bot、不查STRATZ：11个命令过滤器注册；真实GreedyStr保留`01 extra`及空参数；重复initialize/terminate通过且client_closed=true；调用真实依赖优先加载器后菜单PNG生成通过。这是安装SDK验证，不是运行StarManager或真实消息验证。

## 实际宿主

运行StarManager发现Dota2Forge0.1.0a1；初始Token缺失时明确ConfigurationError。随后停用插件，配置本机Token与namespace=astrbot-local/reply_mode=image，更新wheel并冷启动桌面版。普通共享库更新需要冷启动，插件管理器的桥接重载不能保证刷新外部包模块。

冷启动后宿主启用插件并初始化ready；当前桥接重载后再停用、启用，最小状态证据（北京时间）：

| 时间 | 观察 |
| --- | --- |
| 04:57:33 | Runtime ready / image |
| 05:03:30 | 宿主重载新桥接，initialized state=ready |
| 05:04:17 | 宿主terminate requested，terminated state=stopped client_closed=True |
| 05:04:53 | 新实例initialized state=ready，最终已打开 |

停用页面状态不能单独证明资源释放；宿主桥接以AstrBot logger记录初始化/终止结果，字段只包括state/client_closed。终止等待Runtime关闭及Renderer线程，未记录身份或请求数据。此前普通Logger在宿主重载后未提供关闭证据，因此不将那轮停用计为关闭验证。

## 依赖加载修复与真实消息

用户首次发送菜单时宿主报 `TypeError: Unsupported Dota2Forge card input`。桌面版依赖优先加载器会递归展开wheel依赖，再按模块名清除/导入顶层包；适配器原先提前导入Application，持有随后被重载的旧Core/Renderer类。修复为库顶层按需公开导出，保留Renderer严格校验；仅删除重复requirements不能解决递归展开。新增禁网独立进程回归，两轮依赖加载后菜单PNG均通过，真实SDK加载器也通过。

修复wheel安装后宿主再次停用/启用并重载启用中的桥接：05:18:15 terminate明确stopped/client_closed=True，05:18:16新实例initialized state=ready/image。用户随后确认 `/dota菜单` 收到图片，并确认 `/dota绑定`、`/dota玩家`、`/dota战绩 20`、`/dota战绩 第3页`、`/dota比赛 第1场` 均正常展示图片且可读。证据为用户文字反馈，不保存账号、截图或真实聊天。

## 未验证

OneBot单会话主流程和图片已由用户确认；直接ID详情、管理员状态/停用的聊天权限、跨用户/群私聊/多连接隔离及其他平台尚未实机验证。权限和隔离有禁网桩测试，不将其替代真实消息验收。不向未知会话发送验证消息。

后续跟踪[任务](../../tasks/active/2026-10-02-astrbot-platform.md)，操作见[安装步骤](../../../docs/cookbook/astrbot.md)，契约见[宿主](../../../docs/subsystems/astrbot-host.md)。
