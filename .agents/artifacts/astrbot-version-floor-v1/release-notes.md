# AstrBot 0.1.0-alpha.6：兼容范围调整

AstrBot 商店要求调整为 **>=4.5.0**，移除了不必要的 `<4.29` 上限。

上游 AstrBot 4.5.0 的公开 API 已核对；实际 AstrBot/OneBot 宿主测试仍在 4.28.2 完成。因此 4.5.0 是可安装的 API 基线，不代表所有版本和平台都已实机验收。

Python 适配器包为 `0.1.0a6`，共享 Core/Renderer 继续使用 `0.1.0a4`。升级请关闭宿主，用它的 Python 运行 `install_runtime.py`，再重新启动。
