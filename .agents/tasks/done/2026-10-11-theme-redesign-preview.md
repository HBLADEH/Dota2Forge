# 全主题与组件重设计预览

Status: done

## 目标
阅读现状契约与有效决策，提出覆盖双端共享图片、文字提示、配置说明与品牌入口的 Dota 2 风格方案，先向用户交付设计想法和样图。

## 非目标
本次不修改生产 Renderer、Provider、宿主配置或发布包；不将样图作为真实战绩、聊天截图或已上线能力。

## 验收
- 明确已实现能力、尚未实现能力和真实聊天待验证范围，以最新契约及代码核实冲突文档。
- 给出主题、颜色、文字层级、布局、组件及简明功能文案；命令保持当前 do 语法。
- 制作菜单、玩家、战绩、出装、宽幅比赛总览/队伍详情及状态组件预览，保留来源、缺失与错误语义。
- 官方英雄/装备/徽章只使用现有本地素材，预览数据清楚标为合成示例；不提交第三方素材预览或真实身份。
- 进行尺寸、文件大小、文字边界和人工视觉检查；运行统一离线检查，列明未实施与未联调事项。

## 影响模块与决策
[Renderer 契约](../../../docs/subsystems/renderer.md)、[设计方向](../../notes/proposed/2026-10-11-theme-redesign.md)、[宽幅报告决策](../../notes/implemented/2026-10-09-match-analysis-report.md)、[官方素材决策](../../notes/implemented/2026-10-04-local-dota-illustrations.md)、[出装说明](../../../docs/cookbook/hero-items.md)。

## 验证证据
开工保留两份用户已有未跟踪商店任务；根、docs、Renderer及notes规则已读取。当前源代码已支持 STRATZ IMP 与1600px宽幅报告，README中部分早期“IMP未实现”表述属于过时信息，方案按最新契约处理。

已完成[全主题方案](../../artifacts/theme-redesign-v3/README.md)、七张独立样稿及三张提案板；原创背景、生成记录及预览脚本保留。780px卡有390px预览，宽报告1600px完整检查；第三方美术图片只留忽略目录，统计为合成示例。[自动检查](../../artifacts/theme-redesign-v3/render-checks.json)全部通过，人工检查菜单／玩家／战绩／出装手机图及状态／完整报告无文字裁切或重叠。

`uv run --locked python scripts/check_governance.py --all`最终exit0：2009项禁网测试，1项pytest-socket告警（测试尝试socket.getaddrinfo，已被禁网机制拦截），Ruff格式/lint通过，mypy86文件通过，聚合覆盖92.49%，scripts/Core/Assets分别94%/93%/93%。[完整日志](../../artifacts/theme-redesign-v3/offline-check.log)。首轮在生成记录落盘前启动，因generation.json链接缺失被治理检查拒绝；补齐记录后重跑通过，没有修改门槛或断言。归档后再次调用check_repository，预算／链接／治理检查通过，git diff --check通过。

## 阻塞与下一步
预览交付完成。用户审阅设计方向后，另建生产实施任务；本轮未修改公共契约、运行插件／宿主配置、发布包或发送聊天。完整攻略／AI等仍未实现；订阅真实投递、报告客户端压缩、各平台权限及新主题实机阅读尚未验证。样稿未覆盖的长字段、完整表现依据及所有管理／订阅状态在实施时必须保留验证。
