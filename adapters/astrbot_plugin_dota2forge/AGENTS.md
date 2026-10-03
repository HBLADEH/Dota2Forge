# Dota2Forge / astrbot_plugin_dota2forge

- 只实现宿主命令、配置、身份、权限、消息、调度与清理。
- 命令和 AI Tool 复用 Core 用例及服务端权限校验。
- 不导入 Dota2UID，不复制 Dota 2 API、ID 转换和业务规则。
- 导入不能联网或启动后台任务；卸载需释放会话和定时器。
- 已有无宿主 SDK 的应用组合层与 AstrBot 4.28.2 发现桥接，消费 Core/Renderer；真实平台验收记录于接入任务，不能用离线桩代替。
