# 双端共用已审查出装截图

2026-10-06用户明确要求GsCore使用此前截图。本轮让两端README共用已审查的AstrBot主宰出装原图，源文件及数据未改写；其他旧指令/含身份图片仍留本机。

- [来源与范围](../../../docs/assets/screenshots/README.md)：原PNG780×1530、302705 bytes，SHA256 11f5062ebae74f34db21a3ce59614cede05f54e3e51d0c6fef5219078cdefdde；再次目视确认四阶段、来源、时间和脚注完整。相同原图的780/390px视觉检查沿用[此前QA](../plugin-screenshots-v1/visual-qa.png)。
- [核对摘要](review-summary.json)：源图与D:/bot/img/出装.png字节一致；两端分发README均使用本地screenshots/hero-items.png，ZIP内图片一致，全部输入/输出摘要匹配，重复生成一致。
- 新候选dist/plugin-distributions/0.1.0a2-shared-showcase-v1：GsCore ZIP1915995 bytes，AstrBot ZIP1917604 bytes，均低于16,000,000；AstrBot ZIP与上轮相同，旧候选保留。
- 本机GsCore旧README备份后同步新README及screenshots/hero-items.png，两者与候选/原图一致。发现入口、专用配置、两库、全局及插件权限配置指纹保持；没有重启运行库或改动AstrBot路由。

GsCore README明确标注“来自AstrBot”及共享Renderer展示范围。此复用不新增GsCore客户端连接、指令捕获、权限或聊天递送证明；真实验收继续单独跟踪。未发送聊天或发布远端。

现有分发截图验证扩展为双端，核对本地引用、ZIP原图字节、双摘要及GsCore来源文字；缺图失败和候选防覆盖验证保留。[统一离线检查](offline-checks.log)退出0：271文件格式、Ruff、mypy71文件、1377禁网测试（202.93s）、治理工具96%/Core93%覆盖率。[任务](../../tasks/done/2026-10-06-shared-plugin-screenshot.md)已完成。
