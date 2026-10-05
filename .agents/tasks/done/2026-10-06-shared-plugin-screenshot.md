# 双端README共用已审查截图

Status: done

## 目标
用户明确要求GsCore也使用此前截图。将已审查的AstrBot主宰出装原图用于GsCore共享Renderer功能展示，同步分发包与本机说明，保留真实截图来源。

## 非目标
不收录旧指令或未脱敏图片，不修改截图内容、不将AstrBot图片当作GsCore聊天验收；不改运行库、配置、连接开关，不发消息或发布远端。保留既有工作区、候选与用户原图。

## 验收
- [x] GsCore README展示此前出装原图并标明AstrBot来源/共享卡片范围。
- [x] 双端分发ZIP携带同字节图片、本地链接及来源/产物摘要；验证完整性与重复生成。
- [x] 本机GsCore说明和图片同步，保留旧说明备份，不重启宿主。
- [x] 同步截图来源/清单及相关说明，统一离线检查通过。

## 影响模块与决策
[GsCore说明](../../../adapters/Dota2UID/README.md)、[发行生成器](../../../scripts/build_plugin_distributions.py)、[截图来源](../../../docs/assets/screenshots/README.md)。[共用决策](../../notes/implemented/2026-10-06-shared-plugin-screenshot.md)按用户授权取代原筛选的GsCore展示隔离，不改变业务验收与隐私边界。

## 验证证据
此前五张原图仍在D:/bot/img，仅无身份信息的780×1530主宰出装完整卡已审查入仓库；其他四图未收录。再次目视确认完整原图，SHA256仍与本机出装.png一致，未修改图片。[证据](../../artifacts/shared-plugin-screenshot-v1/README.md)记录来源、分发和本机同步。

新候选dist/plugin-distributions/0.1.0a2-shared-showcase-v1重复生成一致；GsCore ZIP1915995 bytes、AstrBot ZIP1917604 bytes（与上轮相同）。两端README引用本地screenshots/hero-items.png，ZIP图片字节及全部来源/产物摘要匹配，均低于16MB；旧候选保留。

本机GsCore旧README已备份，新README与图片匹配候选/源图；发现入口、专用配置、两库、全局和权限配置指纹保持，没有重启或修改AstrBot路由。原图390px可读性沿用此前相同字节图片的视觉QA，不宣称宿主内Markdown查看器实测。

统一入口uv run --locked python scripts/check_governance.py --all退出0：271文件格式、Ruff、mypy71文件、1377禁网测试（202.93s）、治理工具96%/Core93%覆盖率通过；现有图片验证扩展为双端，本地引用/原图/ZIP/双摘要和GsCore来源标注均校验，缺图失败/防覆盖仍保留。[日志](../../artifacts/shared-plugin-screenshot-v1/offline-checks.log)。

## 阻塞与下一步
截图共用展示及本机文档同步已完成，没有发布远端、发送聊天或新增GsCore实机验收。其余现行功能图片按[清单](../../../docs/cookbook/plugin-showcase.md)补齐，可注明来源后共用公共卡片；真实聊天/平台边界继续在[宿主任务](../active/2026-10-05-dota-style-host-deployment.md)跟踪。
