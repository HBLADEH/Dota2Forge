# 宽幅比赛报告与来源 IMP

Category: feature
Related task: [详情改进](../../tasks/active/2026-10-09-match-analysis-report.md)
Related code: [报告值](../../../packages/dota2forge-core/src/dota2forge_core/domain/match_reports.py)、[布局](../../../packages/dota2forge-renderer/src/dota2forge_renderer/match_report_layout.py)
Related docs: [分析](../../../docs/subsystems/analysis.md)、[Renderer](../../../docs/subsystems/renderer.md)

## Problem
用户真机查询后指出空装备槽不应有文字，详情因手机比例拆成多页且缺少综合比较和表现评分。用户提供STRATZ截图作参考，并明确选择STRATZ IMP，而非自定义评分。[旧研究](2026-10-02-analysis-enrichment.md)未开放IMP，因为没有版本化定义；本次仅展示本局原始来源分数，不宣称自有公式或跨局尺度。

## Decision
MatchParticipant追加可缺省IMP、位置/分路、三背包槽和中立装备；STRATZ imp严格为有符号Short，MatchDetail仅允许STRATZ承载，OpenDota不补值。STRATZ新字段由2026-10-09内省核对。实际样本许多空槽为null，按用户要求装备0/None均视觉置空，模型不混同，页脚说明可能是空或未提供；正物品缺图仍保留名称/ID及问号。

MatchAnalysis追加两条独立团队优势序列。STRATZ明确首样本为-60～0秒，按-60起点、60间隔存储有符号净资产/经验优势。不能把团队差值混入个人净资产或OpenDota金钱序列。订阅JSON追加字段，旧缺键按未知/空新增集合读取，无SQL迁移。

MatchReport派生五人完整阵营的合计及参战率，并按本局可用IMP列最高正分/最低负分各至多三人，0/缺失不进入突出或偏弱列表；并列KDA/经济/伤害/治疗，不声称这些就是模型公式。匿名仍只展示英雄及统计。原KDA候选公共属性兼容保留。

新增MatchReportCard为1600px宽、最高3200px、最大2MiB的总览和五人分队详情。双端do比赛消费同一报告，总览显示十人对比/优势曲线/表现列表，队页显示所有已实现指标与十个装备槽。旧780px卡兼容；仅报告放宽尺寸，线程/并发/编码边界不变。文本分段限制1400字符，回退不重查Provider；成功图片不重复发送回退文本。

发行准备升级Core a6/Renderer a5、Dota2UID a9及两个适配器的依赖下限。AstrBot仅源码准备a9，本次发布Dota2UID，延续用户此前直接推送合并及真机更新授权。Assets a1保留原公开字节，不覆盖旧Release。

## Alternatives considered
坚持手机比例会继续删信息或拆碎队伍，故以宽报告为主。自造综合分会与用户选择及截图尺度不同；只按KDA判断会忽略来源模型、经济和辅助贡献。删除空槽改变装备位置，所以保留空框。吞分析失败会把错误冒充数据，维持原失败分类。

## Consequences
新公共字段检查Core、双端、Renderer及订阅JSON消费者。图可放大查看，真实聊天压缩和递送需用户复测；旧运行库对新字段不会展示，不宣称新报告已上线。地图、对线结论、视野/堆野、回放与官方MVP仍未实现，不从截图编造。

## Verification
新增合成字段、评分正负/零/缺失/并列、序列符号/时间、存储兼容、十人内容/空槽/缺图/宽图和双端消费回归。真实只读与完整离线证据见任务；未保存用户参考截图或原始身份。
