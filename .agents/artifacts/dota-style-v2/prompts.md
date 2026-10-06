# 装饰背景提示词

状态：2026-10-05内置image_gen生成并接入完成，未调用API/CLI备用路径。实际工具为image_gen__imagegen，模型未返回，记录model=null；完整实际提示词与[中文v2](header-prompt-v2.txt)逐字符一致。原稿2172×724保存在`output/imagegen/dota-forge-header-v2.png`，仅等比Lanczos缩放为1536×512接入本地decor/header.png。实际时间、尺寸、字节数、SHA256和完整提示词见[生成记录](header-generation-v2.json)；九张卡片与390px验证见[QA](qa-with-ai-v2.json)。

历史失败：用户此前授权API/CLI备用路径并开启CC Switch3.20.4代理；health=healthy，CLI请求gpt-image-2/1536×1024/medium经代理返回HTTP403：Image generation is not enabled for this group，见[失败记录](imagegen-attempt.json)。本轮未重试该路径；内置成功不代表中转权限已经改变。[备用配置步骤](../../../docs/cookbook/imagegen-relay.md)保留。代码绘制的图形不是AI生成素材。

v2明确左侧文字留白及中心裁切构图；只生成一张标题背景，英雄/装备继续使用官方下载素材。提示词优先1536×512，工具实际返回2172×724，同为3:1；原稿独立保留，最终图1536×512由Renderer中心裁切780×174并叠加60%深色遮罩。

以下保留失败请求使用的v1提示词供追溯，后续采用v2：

```text
Use case: stylized-concept
Asset type: background illustration for a Dota2Forge bot card header
Primary request: original dark fantasy game UI art inspired by Dota 2's atmospheric presentation: weathered basalt, aged bronze edges, subtle red embers and muted jade mist.
Scene/backdrop: an ancient stone forge, seen as a quiet material backdrop with shallow carved angular details.
Style/medium: polished painterly game environment art, restrained texture, crisp silhouettes.
Composition/framing: panoramic composition; important details confined to the far right and edges; the central horizontal strip remains dark and uncluttered for UI text. The image will be cropped to 780x174 pixels.
Lighting/mood: low-key cinematic lighting, small warm ember accents, deep readable shadows.
Color palette: charcoal blue-black, weathered bronze, muted Dire red and Radiant jade.
Constraints: no heroes, no creatures, no equipment icons, no rank medals, no Dota logo, no text, no letters, no numbers, no watermark. Do not render a UI screenshot. Background only; all text and data will be added by code.
```
