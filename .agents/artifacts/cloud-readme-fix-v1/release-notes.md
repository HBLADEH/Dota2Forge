# AstrBot 0.1.0-alpha.5：修复商店图片显示

- README 图标和截图改用完整图片地址，安装说明与许可证链接也改为完整 GitHub 地址。
- 商店版本号改为标准格式 0.1.0-alpha.5，对应 Python 适配器包 0.1.0a5。
- Core、Renderer 继续使用 0.1.0a4，查询和绘图逻辑没有变化。

升级仍需关闭 AstrBot，用宿主的 Python 运行插件中的 install_runtime.py，再重新启动。不要只更新桥接目录而保留旧适配器包。

这是预览版；商店页面需等待本次更新审核。安装与配置见 [INSTALL.md](https://github.com/HBLADEH/astrbot_plugin_dota2forge/blob/main/INSTALL.md)。
