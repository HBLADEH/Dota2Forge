# AstrBot 接入步骤

现行入口为do，玩家为do查询 [ID]并显示[预估MMR](../subsystems/ranks.md)。2026-10-05本机已同时更新Core、Renderer、适配器及发现桥接至0.1.0a2，启用后ready/image，OneBot已连接。用户已提供完整出装卡；新菜单/MMR等及出装命令输入待补图，[范围](../assets/screenshots/README.md)。旧dota入口不再注册；[英雄攻略仍为调研](hero-guides.md)。

Step13玩家/指定比赛订阅、日报、主动推送和受控timer已接入；配置、权限、失败人工重试和共享wheel停机升级见[订阅接入](subscriptions.md)。主动推送目前只支持OneBot v11反向WebSocket，不宣称全平台可用。

AstrBot 适配器是 `astrbot-plugin-dota2forge`，宿主桥接只负责事件、身份、权限、消息和生命周期；账号、Provider、SQLite 绑定和图片 Renderer 仍由 Dota2Forge 共享组件提供。声明支持 AstrBot `>=4.5.0`；4.5.0 公开 API 已核对，真实宿主测试目前在4.28.2完成。

## 安装

1. 先构建 wheel 并导出发现桥接；本阶段这些包尚未发布，不能只用包名从索引安装：

   ```sh
   uv build --all-packages
   uv run --locked python -m astrbot_plugin_dota2forge.install --output dist/astrbot_plugin_dota2forge.zip
   ```

2. 在 **AstrBot实际Python** 环境中安装 Core、Renderer、Assets、AstrBot四个wheel。联网安装本地 AstrBot wheel 的 `stratz` extra 会解析同目录依赖；示例将python替换为宿主解释器：

   ```sh
   python -m pip install --find-links /path/to/Dota2Forge/dist "/path/to/Dota2Forge/dist/astrbot_plugin_dota2forge-0.1.0a2-py3-none-any.whl[stratz]"
   ```

   桌面版以 `--target <运行根>/data/site-packages` 安装；不要覆盖内置Python的宿主依赖。若httpx/Pillow已满足，可先用 `--no-index --no-deps --target ...` 显式安装四个wheel，再核对两个依赖版本。缺依赖时先准备wheel，不将离线安装失败当作通过。

3. 将压缩包通过 AstrBot 插件管理器安装，或执行桥接安装：

   ```sh
   uv run --locked python -m astrbot_plugin_dota2forge.install --host-root /path/to/AstrBot
   ```

   `--host-root` 只写入 `data/plugins/astrbot_plugin_dota2forge`，已有内容不一致会停止并保留原文件。桌面版源码目录和运行目录分离时，另传 `--data-root <运行根目录>`。安装脚本不导入 AstrBot、不重启宿主。ZIP 只包含发现桥接；必须先在宿主环境安装四个共享/适配器 wheel、Pillow 与 httpx，不能只上传 ZIP 期待自动取得尚未发布的包。

4. 在 AstrBot 插件配置中填写 `stratz_token`，为每个部署设置唯一 `namespace`，选择 `image` 或 `text` 回复模式，并重新加载插件。Token 仅进入宿主配置和专用 HTTP 客户端，不进入日志或消息。

0.1.0a2候选将其他字段合法的空Token显示为awaiting_config，给出本机配置提示；未创建客户端/数据库/订阅任务。保存配置后重载的新实例恢复就绪，非法配置仍failed。商店专用根入口、锁定依赖和隔离安装步骤见[发行候选](plugin-release.md)；公开包和商店验收尚未完成。

更新共享库wheel时先停用插件、确认关闭，再替换wheel并冷启动AstrBot。仅更新桥接可用插件重载；处于停用状态时宿主可能复用旧模块，不能把页面成功提示等同新代码生效。若旧版菜单报 `Unsupported Dota2Forge card input`，安装包含顶层按需导出修复的新wheel后冷启动；修改requirements不能单独修复依赖递归重载造成的类型冲突。当前本机已完成发现、配置加载、冷启动、重载与关闭/恢复ready验证，用户确认OneBot单会话菜单/绑定/玩家/战绩分页/序号详情图片正常且可读，[证据](../../.agents/artifacts/astrbot-host-v1/README.md)。

## 命令

```text
do帮助 / do菜单
do绑定 <ID> / do改绑 <ID>
do账号 / do解绑
do查询 [ID]
do战绩 [条数] / do战绩 <ID> <条数>
do战绩 第N页
do比赛 <ID> / do比赛 第N场
do斧王出装 / doAM出装 / do出装 Shadow Fiend
```

do段位是do查询别名，do最近是do战绩别名；常规命令遵循AstrBot唤醒前缀（默认如 `/do菜单`）。`ID`接受规范Dota账号ID或public individual SteamID64，拒绝URL/vanity/前导零。[英雄出装](hero-items.md)已实现：动态do…出装接受裸命令和斜线，不需绑定；攻略尚未实现。

平台事件中的发送者、机器人、平台连接和会话字段组成隔离边界；命令参数不能指定绑定目标身份。群聊和私聊的最近列表在完整发送后保存十分钟，最多 128 个会话；改绑、解绑、停用和重新加载会清除列表。直接比赛 ID 查询不要求已有绑定。

管理员可使用 `do状态` 查看状态，使用 `do停用` 关闭客户端、Renderer 和在途操作；再次加载会创建新的 Runtime。渲染失败只回退同次查询的文本，发送失败不会重试或提交新列表。

## 验证边界

普通测试禁网且不安装 AstrBot SDK，验证宿主桩可调用的生命周期、配置、身份、图片发送和失败边界。wheel smoke 只证明包可安装和资源存在，不证明 AstrBot 真实事件、平台图片上传、压缩、权限或宿主热重载；这些需在获得授权的 AstrBot 实例中按相同命令逐项确认并记录到任务证据。

深色卡片的英雄/装备插图支持 illustration_path 配置；显式下载与路径基准见[本地插图指南](illustrations.md)。新源码候选留空按 auto/manual/off 使用托管素材，首次完成前占位，普通回复不下载资源。2026-10-05本机已更新三个wheel和发现资源，配置独立素材目录并冷启动ready，安装包已确认加载新背景。用户确认本轮/do菜单及所测其他指令图片/图标正常，OneBot已连接；分页/五人详情/手机可读性未获本轮逐项反馈，详见[部署/聊天证据](../../.agents/artifacts/dota-style-host-v2/README.md)。

截图前升级另见[证据](../../.agents/artifacts/astrbot-screenshot-update-v1/README.md)：保留配置、绑定、订阅与558张素材，停用确认客户端关闭后停机安装；18个静态命令及动态出装捕获通过宿主SDK检查，菜单/玩家MMR/出装合成PNG可解码。桌面插件页已显示新主宰图标与0.1.0a2；按[清单](plugin-showcase.md)采集真实聊天图片，不以合成图替代。
