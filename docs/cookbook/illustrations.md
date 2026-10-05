# Dota2 本地插图

共享 Renderer 使用深色主题；英雄横幅和六槽装备图按 Core hero_id/item_ids 映射。未知英雄保留 ID，装备 0 是空槽、None 是未知，官方缺图使用问号。长昵称省略；超过槽位宽度的装备 ID 触发同次数据文本回退，避免省略原 ID。

## 下载

在仓库根目录显式执行联网工具，无需玩家凭据：

```sh
uv run --locked python scripts/download_dota_assets.py --output .dota2forge-assets
```

工具读取 Valve 的 herolist/itemlist 与官方 Steam CDN；六个下载线程、20秒请求超时、4MiB响应限制。使用临时目录完成全部请求后再更新目标文件及 manifest，网络失败保留原素材；更新目录时应暂停渲染，文件与 manifest 替换不是目录级原子操作。无自动重试；只有 HTTP 404 记录 missing，其他 HTTP/网络/格式错误失败。每次命令重建当前表快照，不保证涵盖所有历史 ID。

段位/星级和金币为Valve游戏美术，实际下载自[OpenDota素材镜像](https://github.com/odota/web/tree/master/public/assets/images/dota2/rank_icons)，非Valve托管URL；清单额外记录source_kind=valve_game_art_mirror及mirror=OpenDota。默认完整下载包括这些图标。仅更新15张界面图、保留现有英雄/装备/catalogs/背景与其他字段：

```sh
uv run --locked python scripts/download_dota_assets.py --output .dota2forge-assets --only-ui
```

可选ranks键0–8对应未定级/八档徽章，rank_stars键1–5对应透明星级，ui目前只允许gold；本地文件分别为ranks/N.png、rank_stars/N.png、ui/gold.png。旧version=1清单不含新节仍有效。玩家rank_tier 11–75且星数1–5时叠加徽章/星级，0未定级、80冠绝一世，None或其他编码不猜图；段位文字与原始编码保留。缺徽章不单画星级，缺星级仍保留文字；不推断排行榜名次。近期与详情的GPM使用金币图，缺图保持文字。损坏图仍为RenderError；图像来源和版权不随MIT wheel重新许可。

manifest.json version=1；heroes/items 以规范十进制 ID 为键，保存内部名、中文名、available/missing、官方 source、fetched_at、file、sha256、尺寸与版权。catalogs 保存列表来源及原响应摘要。图像原字节保留，不生成替代英雄或装备。

下载包被 Git 忽略且不进入 wheel；Valve 美术权利归 Valve，仓库 MIT 不重新许可它，也不主张 CDN 可下载即获得再分发许可。发布独立素材包需另核许可。

## 配置

Dota2UID 的 config.toml 增加：

```toml
illustration_path = "D:/workstation/Dota2Forge/.dota2forge-assets"
```

相对路径以 config.toml 所在目录为准。AstrBot 的插件配置提供同名字符串字段，相对路径以插件数据目录为准。留空仅使用随包字体/名称及占位；不隐式扫描其他路径，不自动下载。升级共享 wheel 与配置后遵循各宿主的[受控停用/重载](dota2uid.md)或[AstrBot生命周期](astrbot.md)。

直接消费 API：

```python
from pathlib import Path
from dota2forge_renderer import AsyncRenderer, PillowRenderer

renderer = AsyncRenderer(PillowRenderer(illustration_path=Path("/local/dota-art")))
# 在宿主关闭阶段 await renderer.close()
```

第一次 render 才读取清单；缺文件/缺条目占位，非法版本/路径/摘要或损坏图片返回 RenderError；适配器沿用同次成功数据的文本回退。缓存最多48张，单图8MiB/2048²像素，关闭释放图片。默认回复仍限780px/1600px/2MiB。

## 装饰与预览

可选 decor.header 使用 decor/header.png，记录 name_loc、source、fetched_at、status=available、sha256、尺寸、生成方式、模型与完整提示词及原稿摘要。图片仅作标题区装饰，经中心裁切为780×174和60%深色遮罩；字体与数据由 Renderer 绘制，禁止生成英雄/装备参数。2026-10-05已用内置image_gen生成v2原稿2172×724，保留在output/imagegen/dota-forge-header-v2.png；等比缩放1536×512接入本地素材包。工具未返回模型名，清单model=null并说明原因。提示词、来源和摘要见[素材说明](../../.agents/artifacts/dota-style-v2/prompts.md)与[生成记录](../../.agents/artifacts/dota-style-v2/header-generation-v2.json)。

官方图下载后离线复现九类合成样图：

```sh
uv run --locked python .agents/artifacts/dota-style-v2/render_samples.py --illustration-path .dota2forge-assets --output .dota2forge-assets/previews-with-ai-v2
```

数据 source=fixture，PNG及390px预览留在被忽略目录；[QA记录](../../.agents/artifacts/dota-style-v2/README.md)不保存真实玩家数据。清单更新后使用新Renderer实例，避免复用旧清单缓存。重下载工具保留decor条目；原稿及装饰来源独立于Valve素材，不进入MIT wheel。普通 pytest 禁网，下载工具不参与网络测试。

2026-10-05已部署到本机两端：GsCore data/Dota2UID/illustrations-v2与AstrBot data/plugin_data/astrbot_plugin_dota2forge/illustrations-v2，各自显式配置并冷启动ready/image。用户确认AstrBot菜单及所测其他指令图片/图标正常；GsCore桥接仍关闭，聊天未验收。本机敏感备份留在各自数据目录；[部署证据](../../.agents/artifacts/dota-style-host-v2/README.md)区分安装PNG、日志和客户端反馈。

随后新增15张段位/星级/金币PNG，两端受控停机后更新Renderer与本地素材、冷启动ready。41种合成段位与九类卡片手机QA、1195项统一禁网检查和四包构建/wheel检查通过；新图聊天反馈单独记录于[段位验收](../../.agents/artifacts/rank-icons-v1/README.md)。
