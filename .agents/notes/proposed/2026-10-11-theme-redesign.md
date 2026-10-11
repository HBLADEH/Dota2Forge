# 全主题与简明功能说明

Category: feature
Related task: [设计预览](../../tasks/done/2026-10-11-theme-redesign-preview.md)
Related code: [共享Renderer](../../../packages/dota2forge-renderer/src/dota2forge_renderer/)
Related docs: [主题预览说明](../../../docs/cookbook/theme-preview.md)

## Problem
现有图片已具备深色、铜金和本地官方素材，但菜单以命令列表组织，查询结果、统计和来源的视觉层级接近。用户要求重新设计全部主题与组件，并先查看想法和样图。

## Decision
提出“远古锻炉”方向：原创石材／暗金属标题、平静实色正文、克制铜金与余烬红，天辉／夜魇按真实语义着色。功能文案按目的→命令→简短说明组织，查询卡按结果→数据→下一步→来源排列。

本次只有[设计提案及离线预览](../../artifacts/theme-redesign-v3/README.md)，不修改生产Card、公共接口、Provider、权限、宿主配置或发行包。官方英雄／装备／徽章使用现有ID映射素材；统计均为合成并标识。预览不作为实机截图。宽幅报告保留现有全量要求，样稿省略项须在实施时恢复。

建议下一切片先在共享Renderer提取主题与组件，然后迁移常规卡、完整报告和双端文字；具体接口及消费者验证留在实施任务，不以本note宣称已经实现。完整攻略／AI等规划能力不进入已实现菜单。

## Alternatives considered
保留命令密集列表，变更较小但仍不利于快速找功能。全局天辉青绿偏轻，弱化锻造品牌；全局夜魇红黑更强，但长期统计阅读容易混同告警。独立网页后台超出当前Bot界面范围，不作为此次实现前提。

## Consequences
标题装饰不铺进正文；未知、0、空、错误、匿名、来源与时间不能因简化文案而消失。样稿字标使用本机Georgia且未分发字体，生产字体选型待落实。官方美术预览留在忽略目录；用户认可后仍需双端离线回归、报告长字段与真实客户端验证。

## Verification
[预览自动检查](../../artifacts/theme-redesign-v3/render-checks.json)记录尺寸、2MiB、文字边界和文字重叠；人工检查390px常规卡及完整报告。统一离线验证及未联调边界由交付任务记录。仅表示方案可审阅，不表示主题已实施。
