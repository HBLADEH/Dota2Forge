# AstrBot 无宿主 SDK 共享消费者

Category: architecture
Related task: [图片交互](../../tasks/active/2026-10-01-image-interaction.md)
Related code: [AstrApplication](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/application.py)
Related docs: [当前架构](../../../docs/architecture.md)

## Problem
Renderer 和详情能力已接入 Dota2UID，但 AstrBot 包仍是空骨架。规划要求两个适配器消费相同 Core/Renderer，同时禁止相互依赖；真实 AstrBot SDK 尚未作为离线测试前提，不能把宿主生命周期写进共享核心或声称平台安装已通过。

## Decision
- 在 AstrBot 包内增加 AstrApplication、独立命令解析和 Text/Image reply 值，导入不读取环境、不联网、不导入 AstrBot 或 Dota2UID。宿主未来只负责可信 PlatformIdentity、配置、权限、消息转换和生命周期。
- AstrApplication 注入 Dota2Service、MatchDetailService 和 AsyncRenderer；玩家、近期、详情和菜单先取得同次 Core 结果，再创建卡片。Renderer 失败返回同次文本，不重复 Provider 请求；文本模式可显式关闭 Renderer。
- AstrApplication 不复制 Dota API、身份转换、SQLite 或 GsCore 状态选择；绑定/详情端口与 Dota2UID 共用 Core，Renderer 仅依赖 Core。AstrBot 的群/私聊临时列表和平台发送确认仍属于宿主接入增量，不在本层伪造。
- Wheel smoke 在无 AstrBot/gsuid_core 的隔离环境导入 AstrApplication；离线测试使用合成 Provider、SQLite 和本地 Renderer 资源。平台插件注册、生命周期、配置 UI、真实图片消息和调度不在本次宣称完成范围。

## Alternatives considered
- AstrApplication 依赖 Dota2UID：会违反两个适配器互不依赖，拒绝。
- 为 AstrBot 复制 Provider/Renderer：会产生数据和缺失语义漂移，拒绝。
- 直接安装 AstrBot SDK 运行普通测试：会引入平台环境和网络前提，选择无 SDK 的组合层测试。
- 把群聊/权限映射放入 Core：Core 会依赖平台身份语义，保留在宿主适配器。

## Consequences
AstrBot 现在有可复用、可离线验证的应用组合层，但仍不是可加载的 AstrBot 插件；需后续核对 AstrBot 事件身份、权限、图片消息 API、卸载清理和真实宿主配置。消息发送失败、平台压缩和跨会话状态不能由本层测试证明。共享依赖使 AstrBot wheel包含Renderer/Pillow，四包构建与隔离安装需继续维护。

## Verification
19 项 AstrApplication/命令合成测试通过：菜单/玩家/近期图片消费、文本模式、RenderError 行为和严格参数；最终统一门禁 811 项通过，Ruff/mypy/覆盖率门槛通过。wheel smoke 验证 astrbot_plugin_dota2forge 在无 AstrBot/gsuid_core 环境中导入并导出 AstrApplication；没有声称 AstrBot 平台生命周期或真实消息通过。
