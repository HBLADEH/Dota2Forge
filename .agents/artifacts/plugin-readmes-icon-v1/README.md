# 双端 README 与主宰图标交付证据

日期：2026-10-05。关联[任务](../../tasks/done/2026-10-05-plugin-readmes-icon.md)、[决策](../../notes/implemented/2026-10-05-plugin-readmes-icon.md)。

## 交付

- [GsCore README](../../../adapters/Dota2UID/README.md)、[AstrBot README](../../../adapters/astrbot_plugin_dota2forge/README.md)：中心图标、安装提醒、配置 / 快速开始、命令、功能展示、数据边界、FAQ、致谢与许可。
- [截图清单](../../../docs/cookbook/plugin-showcase.md)：双端各采菜单、绑定 / 账号、玩家、近期两页、显式取页、两阵营详情、出装与配置；包含可选图、文件名、升级前提、脱敏与手机可读性。
- [生成 PNG](../../../docs/assets/branding/juggernaut-icon-v1.png)和[最终提示词](../../../docs/assets/branding/juggernaut-icon-v1.prompt.txt)：内置 image_gen，未使用回退CLI或传入参考图作编辑输入；工具未返回模型名。

参考来源：[GenshinUID README](https://github.com/KimigaiiWuyi/GenshinUID/blob/v4/README.md)、[NTEUID](https://github.com/tyql688/NTEUID)及其ICON.png。NTEUID原图只下载至被忽略的.tmp用于观察，未进入项目美术/发行产物。AstrBot根logo.png命名依据[官方指南](https://docs.astrbot.app/dev/star/plugin-new.html)。

## 检查

`uv run --locked python scripts/check_governance.py --all` 退出0，[完整日志](check-governance.log)。Ruff格式/lint、mypy71文件通过，1374项禁网测试通过，总覆盖率93.30%；scripts96% / Core93%独立门槛通过。新增两项产物测试，验证独立根链接、原样图标与ZIP内容、版本/仓库注入、唯一发行标记、来源摘要和索引URL；现有可复现/拒绝覆盖/大小门槛测试继续通过。

初次格式检查指出新增测试断言需要格式化，随后仅格式化该测试文件，再运行完整统一检查。初次图标元数据探针使用假定尺寸导致越界，改为读取实际尺寸；没有修改图像。浏览器file协议不可用，改用仅开放预览HTML/图标的临时127.0.0.1服务，60秒自动关闭；服务已结束。

图标1254×1254 RGBA、1627903 bytes，alpha极值0–255，四角全透明。原始生成图和[浅/深底256/128/64px预览](icon-preview.png)已目视检查：面具、红纹与圆边清晰，文字 / 水印缺省；64px下剑与面具轮廓可辨，细节自然缩小。预览为图标QA，不作为真实插件聊天图。详见[元数据](icon-metadata.json)及[浏览器预览页](icon-preview.html)。

## 本地发行候选

目标目录：dist/plugin-distributions/0.1.0a2-readmes-icon-v1。实际生成退出0，全部manifest产物摘要核对通过。包含同一图标字节的GsCore根ICON.png与AstrBot根logo.png，以及各自README。说明链接指向主仓文档；根许可/图标可在独立ZIP内解析。索引仅是草稿，avatar/cover指向目标仓库main/ICON.png。

| ZIP | 字节数 | SHA256 |
| --- | --- | --- |
| Dota2UID.zip | 1622100 | eba4600e30b245145e61a93fd6dd21b4dac9c51bb8335778f2f0bd0c83a0673e |
| astrbot_plugin_dota2forge.zip | 1623752 | 0a28f050c418ca7ef3b15775feb649060a652d943f870031c33d6cd4f2253190 |

[摘要核对结果](distribution-summary.json)留存。保留既有0.1.0a2候选，未覆盖它；本轮只改文档/图标及发行生成规则，没有运行宿主或修改手动桥接安装器/运行库版本。

## 未验证

真实功能截图、宿主图标加载、当前do/MMR/出装聊天、订阅真实投递、多平台与当前版本商店安装均未验证。英雄攻略 / AI Tool / IMP / Deploy仍未实现。没有外部发布、商店提交、消息发送或凭据操作；远端图标/新增文档URL在源码同步前不可作为已可达链接。
