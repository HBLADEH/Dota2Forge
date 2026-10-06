# 双端插件 README 与主宰图标

Status: done

## 目标
阅读现行文档与实现，参考 GenshinUID 的 README 结构，为 GsCore / AstrBot 编写用户说明与待截图清单；参考 NTEUID 图标的呈现方式，生成独立的 Q 版主宰插件图标并纳入本地发行候选。

## 非目标
不发布包、远端仓库或商店，不操作运行宿主，不制造真实聊天截图，不覆盖已有工作区修改；不复制参考插件美术或宣称规划能力已实现。

## 验收
- [x] 两端独立 README 包含图标、安装配置、准确命令、能力边界、功能展示与帮助入口。
- [x] 列明所需截图、命令、平台区别、脱敏要求与建议文件名；未提供图片不引用不存在资源。
- [x] Q 版主宰 PNG 经视觉检查并保存到项目，说明生成方式与最终提示词。
- [x] 发行目录/ZIP 包含说明与对应宿主图标命名，索引草稿使用插件图标；保持可复现与不覆盖语义。
- [x] 统一离线检查通过，记录本地生成结果与未验证项。

## 影响模块与决策
[发行生成器](../../../scripts/build_plugin_distributions.py)、[GsCore 适配器](../../../adapters/Dota2UID/)、[AstrBot 适配器](../../../adapters/astrbot_plugin_dota2forge/)、[发行步骤](../../../docs/cookbook/plugin-release.md)。延续[发行阶段一](../../notes/implemented/2026-10-05-plugin-distribution-stage1.md)。

本轮[说明 / 图标决策](../../notes/implemented/2026-10-05-plugin-readmes-icon.md)、[截图清单](../../../docs/cookbook/plugin-showcase.md)、[图标及完整提示词](../../../docs/assets/branding/README.md)。

## 验证证据
开始前检查 Git 状态，保留既有大量源码、文档、任务和产物修改。已阅读根/双适配器/docs/tests 规则、治理与发行契约及现行命令说明。

统一入口退出0：Ruff格式/lint、mypy71文件、1374项禁网测试通过；总覆盖率93.30%，scripts96% / Core93%独立门槛通过。新产物测试覆盖独立根链接、图标字节、ZIP、指定版本/仓库、摘要与索引；保留原可复现/拒绝覆盖测试。

图标1254×1254 RGBA、1627903 bytes，透明极值0–255、四角全透明；浏览器浅/深底256/128/64px目视检查通过。发行目录为dist/plugin-distributions/0.1.0a2-readmes-icon-v1，GsCore ZIP1622100 bytes / AstrBot ZIP1623752 bytes，全部摘要匹配。详细[证据](../../artifacts/plugin-readmes-icon-v1/README.md)。

## 阻塞与下一步
本轮文档 / 图标目标完成。真实功能截图由用户后续提供，新 do 命令/MMR/出装尚未部署运行宿主，截图须在匹配版本升级后采集。补图时同步发行打包规则；宿主图标加载、当前版本真实聊天、商店安装与公开URL可达未验收。本轮未操作宿主、发送消息或外部发布。
