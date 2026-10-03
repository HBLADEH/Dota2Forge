# 经济与购买数据的独立读取

分析读取使用与基础详情相同的 Provider 客户端，但通过独立端口调用：

```python
from dota2forge_core import MatchAnalysisService

analysis = await MatchAnalysisService(provider).get_match_analysis(match_id)
```

`MatchAnalysis` 的每个 participant 包含 `metrics` 和 `purchases`。先查看 `MetricSeries.semantic` 再解释数值：STRATZ 的 `NETWORTH_LEVEL` 与 OpenDota 的 `COLLECTED_GOLD`、`EXPERIENCE_TOTAL` 不可互换。序列中的 0 是有效数值，`None` 表示来源没有提供该字段；不要将 OpenDota `gold_t` 作为 STRATZ 净资产或 IMP 的替代。

`PurchaseEvent` 的 `time_seconds` 是来源比赛时间；item ID/key 可能只有一项，不能用名称反查补全。`purchases=()` 是已知空列表，`purchases=None` 是缺失或未请求。

IMP、averageImp、award 等专有模型输出没有进入公共契约。分析结果不会自动生成“评分”、MMR、胜率或建议，也不会阻塞基础详情查询。当前没有 AstrBot/GsCore 命令展示这些字段。

普通验证：

```sh
uv run --locked python scripts/check_governance.py --all
```

真实账号、在线字段覆盖、解析任务和长期稳定性未验证。
