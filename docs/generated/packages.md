# Dota2Forge 包参考

由 `scripts/generate_reference.py` 从 workspace 与各包 pyproject.toml 生成。

| 分发包 | 版本 | 导入包 | 运行依赖 |
| --- | --- | --- | --- |
| dota2uid | 0.1.0a4 | Dota2UID | dota2forge-core>=0.1.0a4,<0.2, dota2forge-renderer>=0.1.0a4,<0.2 |
| astrbot-plugin-dota2forge | 0.1.0a6 | astrbot_plugin_dota2forge | dota2forge-core>=0.1.0a4,<0.2, dota2forge-renderer>=0.1.0a4,<0.2 |
| dota2forge-core | 0.1.0a4 | dota2forge_core | 无 |
| dota2forge-renderer | 0.1.0a4 | dota2forge_renderer | dota2forge-core>=0.1.0a4,<0.2, pillow>=11.3,<13 |

本表仅描述包元数据；实现边界见 [当前架构](../architecture.md)。命令与资源契约以适配器/Renderer文档为准，AI Tool 注册表尚未实现。
