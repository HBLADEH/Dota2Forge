# AstrBot Cloud 文档图片与版本格式

Category: bug-fix
Related task: [修复任务](../../tasks/done/2026-10-06-cloud-readme-images.md)
Related code: [分发生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [分发契约](../../../docs/subsystems/plugin-distribution.md)

## Problem
Cloud将README相对图片与文档地址解析到自身域名，导致图标、截图和安装链接失效。仓库推送README后Cloud仍使用已发布文档快照；更新入口要求SemVer，拒绝原Python风格0.1.0a4。

## Decision
AstrBot生成README使用GitHub原图绝对地址，INSTALL/LICENSE用完整仓库地址，ZIP继续包含资源。GsCore保持原相对路径。图片字节不改，第三方权利不变。

用户已授权发布文档修复版。AstrBot adapter升0.1.0a5，宿主metadata/展示版号按SemVer写0.1.0-alpha.5；Python包、release.json、requirements和GitHub运行包tag继续PEP440格式0.1.0a5。生成器明确转换a/b/rc为alpha/beta/rc，未知格式拒绝。Core/Renderer/Dota2UID保持0.1.0a4，运行逻辑不变；旧发行资产/tag不覆盖。

## Alternatives considered
- 仅推送README：已验证Cloud仍显示旧相对地址，无法完成商店修复。
- 删除重建插件或换绑其他仓库：不必要且影响历史，保留原插件ID。
- 所有库升级：此次只改AstrBot文档/宿主元数据，无需发布新的共享库。

## Consequences
商店版本与Python包名格式不同但对应同一adapter版本，清单严格锁定各包。新增更新需要Cloud审核，提交不等于审核通过；其间已发布旧版可能仍显示旧文档。

## Verification
分发/安装器测试检查混合版本和两种版号、HTTPS图片地址与打包资源，统一离线入口及公开资产/商店DOM验收记录在任务中。
