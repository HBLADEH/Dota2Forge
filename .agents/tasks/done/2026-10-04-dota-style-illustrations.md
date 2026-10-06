# Dota2 风格卡片与官方插图

Status: done

## 目标
优化共享图片卡片的 Dota2 风格展示；英雄、装备插图由官方资源下载并按 Core ID 映射。生成装饰背景与真实游戏素材分开记录来源。

## 非目标
不新增业务数据、战绩推断、宿主发布或聊天发送；不把 Valve 美术重新许可为 MIT，不在回复期间联网取图。

## 验收
- [x] 深色/铜金/天辉夜魇主题应用于五类卡片，保留 780px、1600px、2MiB 与五行分页约束。
- [x] 官方下载工具生成本地版本化英雄/装备素材包，保留 ID、名称、来源、时刻、摘要及缺失状态。
- [x] Renderer 只读本地文件，双端组合入口显式配置目录；未知英雄/装备、None 与 0 保持区别。
- [x] 同次数据文本回退、关闭/取消和懒加载契约保持通过。
- [x] 合成卡片与 390px 预览验证；统一离线检查、构建和 wheel 验证。
- [x] 装饰背景生成：10-05内置image_gen按中文v2成功生成，原稿保留，1536×512接入decor/header.png；来源/实际方式/模型未知/提示词/时间/摘要完整记录。
- [x] 本轮统一离线检查复跑并归档任务。

## 影响模块与决策
[Renderer](../../../packages/dota2forge-renderer/)、两个适配器与[素材决策](../../notes/implemented/2026-10-04-local-dota-illustrations.md)。

## 验证证据
已读根/Renderer/适配器/测试/文档规则、现有 Renderer 契约与共享绘制决策。工作区已有未跟踪插件商店评估 note/task，保留。
只读请求确认 Valve 英雄横幅 256×144 与装备列表/图标 CDN 可用；下载和普通测试分别处理。

`uv run --locked python scripts/download_dota_assets.py --output .dota2forge-assets`：127张英雄图、415张装备图、129条404；542张PNG逐一验证SHA256与尺寸，见[摘要](../../artifacts/dota-style-v2/download-verification.json)。素材和含官方图的预览均被忽略，不进wheel。
10-04实际共享包生成9张合成卡片与390px预览；最大1594px/284854 bytes，边界/重叠检查及人工QA通过，见[QA](../../artifacts/dota-style-v2/README.md)。未知ID/None/0与长装备ID回退均验证。
`uv run --locked python scripts/check_governance.py --all`通过：Ruff格式/lint、mypy62源文件、1144项禁网测试；聚合覆盖率92.72%，scripts独立97%、Core独立92%，均过80%门槛。`uv build --all-packages`及`uv run --locked python scripts/smoke_wheels.py`四包构建/独立无索引安装导入通过。未改policy/治理脚本/门槛，原有修改保留。

10-05接入背景后复跑统一入口通过：1144项禁网测试、Ruff格式/lint、mypy62源文件；聚合92.72%、scripts97%、Core92%。第一次因三处原稿链接超出测试隔离副本范围导致5项治理测试失败，修正文档引用后全绿；[失败日志](../../artifacts/dota-style-v2/offline-checks-v2.log)、[通过日志](../../artifacts/dota-style-v2/offline-checks-v2-retry.log)与[检查摘要](../../artifacts/dota-style-v2/checks-with-ai-v2.json)保留。测试/治理规则未改；本轮无包代码变化，未重复构建。

## 阻塞与下一步
10-05用户已认可卡片和官方图，并授权图像生成及API/CLI备用路径。新对话内置image_gen按[中文v2](../../artifacts/dota-style-v2/header-prompt-v2.txt)成功生成2172×724原稿，等比缩放接入；模型未返回，清单如实记录未知，完整证据见[生成记录](../../artifacts/dota-style-v2/header-generation-v2.json)。新Renderer实例生成九张卡片与390px预览；543张可用素材逐一验证PNG/摘要，最大1594px/420756 bytes。人工QA通过；除标题绘制区外像素与已认可预览完全相同，见[接入QA](../../artifacts/dota-style-v2/qa-with-ai-v2.json)。本轮未改包代码、配置、uv.lock或凭据。

此前CLI经CC Switch3.20.4（health=healthy）请求gpt-image-2遇HTTP403：Image generation is not enabled for this group，见[失败证据](../../artifacts/dota-style-v2/imagegen-attempt.json)和[备用配置](../../../docs/cookbook/imagegen-relay.md)。本轮未重试，内置成功不代表中转权限已变。背景已完成，新主题尚未部署或聊天实测；宿主发布、聊天发送与客户端压缩验证另行处理，不属于本任务。
资源定时校验更新为后续方向，尚未创建自动化或运行期Scheduler；可先周期校验manifest摘要与Valve列表，再显式更新，避免把网络检查放入Renderer。
[接续说明](../../artifacts/dota-style-v2/continue.md)已补录完成状态，保留历史授权、提示词和403证据。
