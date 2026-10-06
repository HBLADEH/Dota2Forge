# AstrBot 兼容声明下界

Category: feature
Related task: [版本下界任务](../../tasks/active/2026-10-06-astrbot-version-floor.md)
Related code: [宿主元数据](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host/metadata.yaml)
Related docs: [宿主契约](../../../docs/subsystems/astrbot-host.md)

## Problem
元数据使用`>=4.28.2,<4.29`，把一次本机验收版本误写成市场兼容范围，远高于常见AstrBot插件下界，也无必要上限。

## Decision
声明调整为`>=4.5.0`，移除上限。上游v4.5.0标签（07ba9c772c3518838921a01dd09290215833a80e）只读核对了本插件使用的公开API路径：astrbot.api、event、message_components、star以及filter command；这些文件均存在且HTTP 200。真实宿主/OneBot生命周期证据仍仅为v4.28.2，文档明确区分，不以静态路径检查代替聊天验收。

适配器升Python包0.1.0a6，Cloud显示标准SemVer 0.1.0-alpha.6，Core/Renderer继续0.1.0a4。这样Cloud能够接收元数据更新，不将无运行逻辑变更包装成共享库更新。

## Alternatives considered
- 继续限制到4.28.2：阻止兼容的正常市场安装，且不代表实际API需求。
- 声明无下界：无法表达API基线。
- 宣称所有未来版本均验收：没有证据，保留无上限声明但不扩大实机验证。

## Consequences
4.5.0至4.28.1用户可安装，但真实平台边界仍待社区或后续验收。上游破坏性变更可能需要修复；普通导入/消费者测试不能保证每个宿主发行版。市场元数据更新需要独立审核。

## Verification
标签/API路径核对、元数据/README/安装文档/分发测试、离线检查、独立安装与公开资产验证由关联任务记录。
