# Dota2Forge / astrbot_plugin_dota2forge

- 只实现宿主命令、配置、身份、权限、消息、调度与清理。
- 命令和 AI Tool 复用 Core 用例及服务端权限校验。
- 不导入 Dota2UID，不复制 Dota 2 API、ID 转换和业务规则。
- 导入不能联网或启动后台任务；卸载需释放会话和定时器。
- 当前仅包骨架，平台安装与生命周期尚未验证。
