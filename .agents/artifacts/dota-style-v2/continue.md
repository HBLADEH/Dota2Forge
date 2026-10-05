# Dota2Forge 标题背景接续与完成记录

## 2026-10-05接续完成

内置image_gen已按header-prompt-v2.txt成功生成并接入标题背景，无需继续尝试生成。原稿保存在`output/imagegen/dota-forge-header-v2.png`，本地素材为.dota2forge-assets/decor/header.png（1536×512）；模型未返回，未推断。完整提示词、生成方式、北京时间、尺寸和摘要见[生成记录](header-generation-v2.json)。九张实际卡片及390px预览在.dota2forge-assets/previews-with-ai-v2，见[QA](qa-with-ai-v2.json)及[说明](README.md)。官方素材/清单与既有布局保留。旧CLI的403未重试；内置成功不能证明中转权限已变。未创建调度。

统一离线检查1144项禁网测试、Ruff/mypy与覆盖率门槛全部通过，见[检查摘要](checks-with-ai-v2.json)；[任务已归档](../../tasks/done/2026-10-04-dota-style-illustrations.md)。以下保留执行前的接续说明，含当时状态与授权；“当前/待生成/本轮不请求”等措辞仅描述此前那一轮，旧请求中active任务路径已移入done。

## 2026-10-05部署与聊天反馈

用户另行授权后已部署GsCore/AstrBot，各自备份并配置独立素材目录，明确wheel安装/逐文件核对与冷启动ready通过。用户在手机/QQ发送命令，确认AstrBot /dota菜单及所测其他指令图片/图标正常；OneBot已连接，新增日志未见插件渲染/配置错误。本轮统一1144项禁网检查通过。GsCore桥接维持原有关闭状态，聊天未验收；分页、五人详情和手机文字可读性未获本轮逐项反馈。后续从[部署任务](../../tasks/active/2026-10-05-dota-style-host-deployment.md)和[部署证据](../dota-style-host-v2/README.md)接续，不重复生成背景。

## 执行前说明

2026-10-05用户要求整理提示词后在新对话继续；本轮不再请求生成API，不创建新对话。工作目录为D:/workstation/Dota2Forge。

## 可复制到新对话的请求

```text
继续 D:\workstation\Dota2Forge 的 UI 装饰背景任务。
先阅读 AGENTS.md、.agents/tasks/active/2026-10-04-dota-style-illustrations.md，以及 .agents/artifacts/dota-style-v2/continue.md。
我已认可当前卡片样式、官方英雄和装备图，也已授权图像生成，包括 API/CLI 备用路径。使用 .agents/artifacts/dota-style-v2/header-prompt-v2.txt 生成原创 Dota2 风格标题背景；优先使用当前对话的内置图像生成工具。若只能用已授权 CLI，遵循 imagegen 技能；现有中转分组曾返回403，不要在权限未变时反复请求。
生成后保留原稿，接入本地素材包 decor/header.png，记录来源/实际生成方式/模型/完整提示词/时间/SHA256，生成九张合成卡片和390px预览并完成视觉及离线检查。
保持我已认可的版式和官方英雄/装备资源。当前修改均未提交，请保留已有修改；本轮只完成背景生成、接入和验证，宿主部署、外部发布与聊天发送另行处理。
```

## 当前已完成

- 共享Renderer的深色主题、铜金分隔、天辉/夜魇配色已实现，两个适配器共用，用户已认可。
- 本地.dota2forge-assets含127张官方英雄横幅、415张装备图；129个装备条目404已记录。未知ID/None/0不推断，普通渲染不联网。
- 现有780px卡片、1600px/2MiB上限、五场/五名分页及同次成功数据文本回退已验证；最新统一检查1144项禁网测试通过，四包构建/wheel验证此前通过。
- 标题装饰加载接口已实现，无需重做主题或官方图下载。当前没有成功生成的AI背景。

## 生成目标与输入

只生成一张标题背景，提示词以[中文v2](header-prompt-v2.txt)为本轮事实源。它明确左侧文字留白、中心裁切带和手机可读性；[旧v1](header-prompt.txt)保留用于失败请求追溯，不覆盖。
参考现有本地预览：.dota2forge-assets/previews/overview.png、menu-mobile.png、detail-radiant-mobile.png。预览含官方图，仍保留在被忽略目录。背景不包含英雄/装备/徽章/文字；真实英雄和装备仅使用已有官方ID素材。
优先1536×512，最终中心裁切为780×174；模型仅支持标准横图时使用1536×1024。生成原稿建议output/imagegen/dota-forge-header-v2.png，保留非破坏性版本；不要用HTML/SVG或代码纹理冒充AI生成位图。

## 接入与验证

PillowRenderer(illustration_path=Path(...))读取本地manifest.json version=1，decor.header只接受文件decor/header.png。必需字段：name_loc、source字符串、status=available、file、sha256；同时记录生成方式、模型（工具未返回时如实记录未知）、prompt、fetched_at、width/height及原稿摘要。保留heroes/items/catalogs等既有清单内容。
原稿及最终图用Pillow确认PNG、尺寸和摘要；标题图不超过单图8MiB/2048²像素，生成更大原稿时先等比缩放。Renderer会中心裁切并叠加60%深色遮罩，字体与品牌由代码绘制；清单更新后用新Renderer实例复核，避免已有缓存。

```sh
uv run --locked python .agents/artifacts/dota-style-v2/render_samples.py --illustration-path .dota2forge-assets --output .dota2forge-assets/previews-with-ai-v2
uv run --locked python scripts/check_governance.py --all
```

人工检查原稿、标题裁切与390px预览：无生成文字/Logo/人物，纹理不干扰标题，五人详情/空列表/未知ID均可读，文字无重叠或裁切。同步真实QA摘要及受影响文档；有代码/包变化时重建并验证wheel。下载素材和含官方图的预览不进入MIT wheel；生成图来源单独记录。

## 已知阻塞与边界

CC Switch3.20.4代理health=healthy，实际CLI请求gpt-image-2被弘连Codex上游分组以403拒绝：Image generation is not enabled for this group，见[请求记录](imagegen-attempt.json)。这是已观测的供应商权限错误，未证明是应用版本限制。
被忽略的.env.imagegen已配置本地127.0.0.1:15721/v1与PROXY_MANAGED占位Key；真实Key由CC Switch注入，勿读取/输出凭据。CLI配置见[指南](../../../docs/cookbook/imagegen-relay.md)。新对话内置工具是否可用需实际发现；换对话不保证上游权限会变化。CLI失败时不要静默降级图像模型。
新主题未部署或聊天实测；资源定时校验更新为后续方向，未创建调度。工作区另有插件商店评估note/task，属于既有修改，应保留。
