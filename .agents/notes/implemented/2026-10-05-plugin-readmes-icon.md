# 双端说明与共用主宰图标

Category: feature
Related task: [说明与图标任务](../../tasks/done/2026-10-05-plugin-readmes-icon.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)、[双端产物检查](../../../tests/test_plugin_distributions.py)
Related docs: [截图清单](../../../docs/cookbook/plugin-showcase.md)、[图标来源](../../../docs/assets/branding/README.md)、[发行步骤](../../../docs/cookbook/plugin-release.md)

## Problem

用户要求阅读项目文档后参考 GenshinUID 编写双端插件说明，先列截图需求，并参考 NTEUID 生成 Q 版主宰图标。现有生成器内联 README 过短，两适配器缺独立用户说明；索引头像使用作者头像，发行产物未提供插件图标。现行 do / MMR / 出装源码与历史宿主证据必须区分，不能制作虚构成功截图。

## Decision

两个适配器各维护 README，参考中心图标、安装提醒、快捷导航、命令与功能展示结构，按平台保留唤醒前缀、配置位置、管理员入口与生命周期差异。现有命令以源码注册为准：GsCore 不宣传 AstrBot 专用 do段位 别名。截图清单写明必需 / 可选画面、文件名、版本、脱敏和手机可读性；未提供图片用文字展示位，避免不存在链接。

内置 image_gen 独立生成主宰同人 PNG；仅观察 NTEUID 图标构图，不将参考文件作为编辑输入或发行素材。单一源文件位于 docs/assets/branding，保留原始透明通道和完整最终提示词。两份 README 引用同一源文件；发行候选分别使用 ICON.png / logo.png，索引草稿 avatar / cover 指向目标 GsCore 仓库 main 的 ICON.png。远端未同步，URL 可达性仍待验证。

生成器读取适配器说明，替换唯一发行标记为包版本和目标仓库，转换主仓相对文档链接，根 LICENSE 与图标使用本地链接。说明 / 图标 / 生成器源码进入来源摘要，README 与图标进入产物摘要及确定性 ZIP；继续保留已有目录完全一致才可重复生成、否则拒绝覆盖的规则。不操作宿主、不改手动安装器或版本依赖、不发布远端。

## Alternatives considered

- 只改生成器中的长字符串：用户无法直接在适配器目录阅读，维护成本高；选择可独立阅读的 README 源。
- 两端分别生成图案：容易破坏统一品牌且无当前需求；共用原始图标，只适配文件名。
- 复制 NTEUID 美术或合成聊天成功截图：不符合独立图案与真实验收要求；只参考呈现方式并留待用户采集真实图片。

## Consequences

桥接 ZIP 增加约 1.6MB 图标，仍须检查 16MB 上限。README 导向主仓文档，公开可达依赖源码同步；图标 UI 加载与商店安装尚需实机验收。未来补入功能截图需同步生成规则与摘要，不能仅改源 README 留下发行缺图。本轮不改治理脚本、policy 或工作流。

## Verification

图标1254×1254 RGBA，四角全透明；浅/深底256/128/64px浏览器目视检查通过。统一入口退出0，Ruff/mypy71文件与1374项禁网测试通过，总覆盖率93.30%，scripts96% / Core93%门槛通过。产物测试验证双端本地链接、ZIP / 根图标字节、指定版本/仓库与来源摘要、索引图标URL；既有可复现与拒绝覆盖测试保持通过。两端ZIP均约1.62MB，全部摘要匹配，[证据](../../artifacts/plugin-readmes-icon-v1/README.md)。真实功能截图、运行宿主更新、商店图标加载与公开发布未执行。
