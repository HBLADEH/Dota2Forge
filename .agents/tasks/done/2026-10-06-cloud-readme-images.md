# AstrBot Cloud README 图片修复

Status: in_progress

## 目标
修复商店图标、截图与文档链接，同步公开仓库和生成器。

## 非目标
只更新AstrBot文档和宿主版本格式；共享库/运行逻辑不变，旧Release附件保留。

## 验收
- [x] AstrBot分发图片使用HTTPS原图直链，文档链接指向GitHub。
- [ ] 图片仍打包，GsCore相对路径不变；检查通过并回读商店。

## 影响模块与决策
[生成器](../../../scripts/build_plugin_distributions.py)、[分发契约](../../../docs/subsystems/plugin-distribution.md)。

## 验证证据
Cloud DOM显示logo.png与screenshots/hero-items.png均解析到cloud.astrbot.app/plugin/HBLADEH/，naturalWidth为0。INSTALL.md和LICENSE也解析到该错误基址。

## 阻塞与下一步
公开README提交1ae7159已推送，图片直链HTTP200/image/png；生成器与59项相关检查、统一1532项离线测试/Ruff/mypy全部通过，治理工具96%、Core93%。Cloud仍显示旧相对路径；重新解析页面明确要求合法semver，0.1.0a4禁用更新按钮。没有更换仓库、撤销版本或覆盖发行附件。用户已授权继续发布：商店0.1.0-alpha.5/Python适配器0.1.0a5，共享库a4。[决策](../../notes/implemented/2026-10-06-cloud-readme-version.md)。
