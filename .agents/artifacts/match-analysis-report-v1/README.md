# 宽幅比赛报告验收

用户截图仅作展示参考，未存入仓库；新代码位于独立工作区 codex/match-analysis-report。普通测试只用合成响应，新真实观察不作为fixture。

2026-10-09 STRATZ内省核对IMP为有符号Short，位置/分路为枚举，三背包/中立为可缺省物品ID；比赛优势序列首项文档为-60～0秒。[schema](schema.json)仅含类型资料，无凭据或玩家身份。

本机系统DNS将api.stratz.com解析至103.73.220.188，直连发生证书信任失败。显式只读诊断通过Google公共DoH核对104.26.8.64，并以原域名Host/SNI及完整TLS证书校验连接，基础/分析均HTTP200。诊断选项只存在[手工预览脚本](preview.py)，未改系统DNS、宿主配置或生产Provider，也未禁用TLS。

指定比赛9035146588的十个IMP为[-7,-47,-23,-19,9,23,30,66,59,48]，与用户STRATZ参考值一致；净资产/经验优势各41项，保留-60秒起点。客户端关闭。保存前移除所有参赛者账号/昵称，生成[脱敏观察](sanitized-observation.json)和[摘要](live-preview.json)；它们不是完整原始响应或真实聊天记录。

[总览](report-1.png)、[天辉详情](report-2.png)、[夜魇详情](report-3.png)均1600px宽，2990/2870/2870px高，最大约1.3MiB。已视觉检查图标/文字/图表无重叠、内容非空；空白槽可来自0或null，模型保留差别，页脚说明。正物品ID缺图仍保留ID/名称。真实昵称在实际用户回复中保留，验收样图使用匿名标签。

版本为Core a6、Renderer a5、Dota2UID a9（AstrBot源码a9但未发行）。[统一离线检查](offline-check.log)1985通过、92.61%；scripts/Core/Assets均过80%，Ruff/mypy通过。双端候选和五wheel隔离安装日志：[distribution smoke](final-distribution-smoke.log)、[wheel smoke](wheel-smoke.log)；五包构建见[build](build.log)。

离线结果、尚未发布与真机边界见[任务](../../tasks/active/2026-10-09-match-analysis-report.md)。旧780px卡保持兼容，新增宽图不预先宣称QQ压缩/递送效果。
