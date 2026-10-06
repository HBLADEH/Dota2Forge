# 本地官方插图与共享深色主题

Category: data
Related task: [插图任务](../../tasks/done/2026-10-04-dota-style-illustrations.md)
Related code: [Renderer](../../../packages/dota2forge-renderer/src/dota2forge_renderer/)
Related docs: [Renderer 契约](../../../docs/subsystems/renderer.md)

## Problem
现有共享卡片为浅色文字布局，已知英雄也仅有问号。用户要求 Dota2 风格生成装饰与下载的游戏英雄等素材。旧决策未打包未经许可的 Valve 美术；运行期 Renderer 又禁止 HTTP/环境读取。

## Decision
共享卡片使用深色石材、铜金分隔及天辉/夜魇色。英雄/装备来自 Valve datafeed ID/内部名和官方 CDN，由独立显式下载工具生成本地素材包。下载文件被 Git 忽略，不进入 MIT wheel；来源/抓取时间/SHA256/版权原样记录，不主张获得再分发许可。
PillowRenderer 增加可选 illustration_path；两个已实现适配器从显式配置注入，不读取环境、不隐式查找路径或联网。未配置/未知 ID/已记录缺图采用占位；损坏摘要/非法路径/未知素材版本作为 RenderError。同次成功数据的文本回退不新增 Provider 请求。缓存有界，关闭释放解码图片。
生成背景属于装饰，单独记录模型/提示词/摘要，可替换局部 header；不生成英雄、装备、段位或数据。内置 imagegen 不可用时遵守技能的明确 CLI/API 授权要求，先保留提示词和未完成状态。

## Alternatives considered
随 wheel 打包全部 Valve 美术：没有已核实的再分发许可，因此只提供独立本地下载路径。
回复时拉图/把 URL 传给 Renderer：破坏离线和线程边界；采用预下载与只读注入。
两端独立主题或生成英雄：易产生视觉/ID 漂移，保留共享绘制与真实 ID 素材。

## Consequences
部署需额外下载并配置素材目录，未配置仍可生成有明确占位的卡片。官方当前表不保证覆盖历史游戏 ID，历史缺项不推断；装饰生成与宿主实测单独验收。本地下载不等于开放许可或已完成发布。

## Verification
2026-10-05接入后统一入口1144项禁网测试、Ruff/mypy/独立覆盖率通过，见[检查摘要](../../artifacts/dota-style-v2/checks-with-ai-v2.json)；四包构建与wheel独立安装/导入此前通过。内置image_gen按中文v2提示词生成2172×724原稿，保留后等比缩放1536×512接入decor/header.png；未返回模型名，清单如实记录未知。542张官方图与1张背景逐一验证摘要/PNG；九张卡片及390px人工QA通过，标题绘制区之外像素与已认可预览完全相同，见[生成记录](../../artifacts/dota-style-v2/header-generation-v2.json)和[QA](../../artifacts/dota-style-v2/qa-with-ai-v2.json)。本轮没有改动包代码或配置，未部署新UI或宿主实测。
