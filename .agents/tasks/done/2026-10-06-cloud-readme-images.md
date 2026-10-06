# AstrBot Cloud README 图片修复

Status: done

## 目标
修复商店图标、截图与文档链接，同步公开仓库和生成器。

## 非目标
只更新AstrBot文档和宿主版本格式；共享库/运行逻辑不变，旧Release附件保留。

## 验收
- [x] AstrBot分发图片使用HTTPS原图直链，文档链接指向GitHub。
- [x] 图片仍打包，GsCore相对路径不变；检查通过并提交商店更新。

## 影响模块与决策
[生成器](../../../scripts/build_plugin_distributions.py)、[分发契约](../../../docs/subsystems/plugin-distribution.md)。

## 验证证据
Cloud DOM显示logo.png与screenshots/hero-items.png均解析到cloud.astrbot.app/plugin/HBLADEH/，naturalWidth为0。INSTALL.md和LICENSE也解析到该错误基址。修复后两张完整GitHub原图直链均为HTTP 200/image/png；公开a5的七个资产已下载并与候选摘要匹配。

## 阻塞与下一步
0.1.0-alpha.5 已提交Cloud更新，Python适配器为0.1.0a5，共享库a4。[决策](../../notes/implemented/2026-10-06-cloud-readme-version.md)。统一离线检查1537项通过（193.92秒），Ruff/mypy、治理工具96%、Core93%通过；71项分发/安装相关检查通过。Cloud随后退出当前登录态，无法回读该版私有审核状态，因此不宣称已审核通过。生产实例、旧a4资产与查询逻辑未改。
