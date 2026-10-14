# STRATZ 新功能规划证据与布局草案

2026-10-14（北京时间）。本目录只服务需求规划，业务和宿主工具均未实现；统计不来自真实玩家。主方案见[功能规划](../../../Dota2Forge_STRATZ_FEATURE_PLAN.md)，取舍见[proposed note](../../notes/proposed/2026-10-14-stratz-feature-scope.md)。

本轮阅读架构/契约、现行远古锻炉theme/Canvas、英雄/分析Provider与双端桥接，以及2026-10-05攻略、2026-10-09分析证据；未读取Token或新增真实API观察。用户指定的STRATZ攻略页标题可读，正文出现客户端错误及Invalid request data，不能确认完整页面字段。官方Meta页面的检索摘要描述多维统计，只作为产品能力线索。

参考项目的README、复盘/证据规则与MIT许可通过公开页面读取；仅借鉴流程，不安装其Skill或执行自动解析脚本。AstrBot官方AI工具文档已读取；本机GsCoreSDK的register.py与手册对照确认common分类、可信上下文和注销候选，未导入运行宿主。源码与手册的特权分类冲突以源码为准；这不是生产SDK/AI调用验收。

布局图使用实际共享Canvas与theme绘制，所有数值/英雄顺序/判断为合成示例，并在每张图醒目标识。没有Valve位图素材，不含账号/昵称/真实聊天或凭据；图仅说明信息层次，不能作为新功能截图。

- [三项布局总览](overview.png)
- [强势榜](hero-meta.png) / [390px预览](hero-meta-phone.png)
- [攻略信息层次](hero-guide.png) / [390px预览](hero-guide-phone.png)：示意一张中的区块，正式摘要按构筑/加点拆两页。
- [复盘摘要](match-review.png) / [390px预览](match-review-phone.png)

复现：`uv run --locked python .agents/artifacts/stratz-feature-plan-v1/render_previews.py`。脚本只绘制固定合成内容，不调用Provider/模型或宿主；使用私有Canvas仅作设计预览，不注册Card。三张原图780×1680、每张小于2MiB，Canvas对文字边界/重叠作严格检查，[QA](qa.json)记录尺寸、字节数与文本数量；另人工查看总览与390px图。规划统一离线检查另记任务，不把合成卡当来源/消息递送证据。

[统一检查](offline-check.log) exit0：2054项禁网测试通过，Ruff/mypy与独立覆盖率门槛通过；[任务归档后治理复核](governance-final.log)也通过，详情见[完成任务](../../tasks/done/2026-10-14-stratz-feature-planning.md)。未验证当前统计覆盖、生产宿主工具/模型或真实聊天；四项实施任务保持planned。
