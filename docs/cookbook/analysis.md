# 经济与购买数据的独立读取

分析读取使用与基础详情相同的 Provider 客户端，但通过独立端口调用：

```python
from dota2forge_core import MatchAnalysisService

analysis = await MatchAnalysisService(provider).get_match_analysis(match_id)
```

`MatchAnalysis` 的每个 participant 包含 `metrics` 和 `purchases`。先查看 `MetricSeries.semantic` 再解释数值：STRATZ 的 `NETWORTH_LEVEL` 与 OpenDota 的 `COLLECTED_GOLD`、`EXPERIENCE_TOTAL` 不可互换。序列中的 0 是有效数值，`None` 表示来源没有提供该字段；不要将 OpenDota `gold_t` 作为 STRATZ 净资产或 IMP 的替代。

`PurchaseEvent` 的 `time_seconds` 是来源比赛时钟的有符号整数，负数表示赛前购买，不能丢弃或改成零；item ID/key 可能只有一项，不能用名称反查补全。`purchases=()` 是已知空列表，`purchases=None` 是缺失或未请求。

STRATZ IMP原样保存于MatchParticipant，双端 `do比赛` 展示本局最高正分/最低负分及K/D/A、参战率、经济、伤害/治疗依据。IMP无公开模型版本，不换算MMR/胜率/官方MVP；averageImp、award仍未实现。STRATZ比赛优势序列按-60秒首区间及60秒间隔保留有符号值；分析失败仍返回来源错误。

普通验证：

```sh
uv run --locked python scripts/check_governance.py --all
```

2026-10-09 对用户指定比赛的只读诊断确认存在赛前购买时间；单次核查不保证其他比赛的字段覆盖或长期稳定性。解析任务未实现。
