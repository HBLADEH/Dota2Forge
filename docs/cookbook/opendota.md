# OpenDota SDK独立使用

安装共享Core的HTTP扩展：`pip install "dota2forge-core[opendota]"`。当前包未发布，仓库开发使用`uv sync --locked --all-packages`；外部环境先构建本地wheel，显式安装对应Core wheel与httpx。

显式查询需要调用者提供账号或比赛ID。以下是组合入口示例，函数本身不读取环境/凭据，不自动在Bot运行；替换ID后会执行公开联网GET，普通测试不执行此示例：

```python
import httpx
from dota2forge_core import AccountId, MatchDetailService
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.opendota import OpenDotaProvider


async def inspect_public_account(account_id: int, match_id: int):
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = OpenDotaProvider(client, clock=SystemClock(), timeout_seconds=10)
        player = await provider.get_player(AccountId(account_id))
        recent = await provider.get_recent_matches(AccountId(account_id), 20)
        detail = await MatchDetailService(provider).get_match_detail(match_id)
        return player, recent, detail
```

不记录完整返回对象或身份；调用者按所需字段展示source/fetched_at/缺失状态。空近期与null详情不证明不存在或公开，段位是来源观察。`parse_version`是OpenDota解析格式版本，`game_mode=OPENDOTA_<整数>`是原模式编号；未经对照不能当作STRATZ枚举、游戏补丁或精确MMR。

交叉核验使用`CrossCheckService(primary, secondary)`，例如注入已构造的StratzProvider和独立OpenDotaProvider，再调用`get_player(account_id)`、`get_recent_matches(account_id, 20)`或`get_match_detail(match_id)`。结果有primary/secondary两份SourceObservation和fields：

- SUCCESS保留value及其来源/时间；FAILED保留failure.code/等待，不伪装为空。
- SKIPPED_PRIVATE表示主源明确隐私拒绝，未请求第二源。
- fields.state为AGREE/DIFFERENT/UNKNOWN；一侧None为不可比较。
- only_primary_ids/only_secondary_ids仅为本次近期列表差异，不代表完整历史差异。

主源失败时没有“合并成功”结果；调用方需显示两侧状态。不取最高段位、不跨源填缺失、不自动回退。当前Bot继续使用STRATZ，尚未新增OpenDota或核验聊天命令。

经济与购买事件使用独立的 `MatchAnalysisService(provider).get_match_analysis(match_id)`。OpenDota 的 `gold_t`、`xp_t`、`purchase_log` 与 STRATZ 的 `networthPerMinute`、`itemPurchases` 分别带有来源语义，不能交叉替换；IMP 等专有模型输出没有进入公共契约。

读取限流返回的等待后由调用者决定是否再查询；不自动重试。429未知重置后当前Provider实例停止发送，需明确重建；不用循环重建绕过额度。客户端始终由组合入口关闭。

验证用`uv run --locked python scripts/check_governance.py --all`；详情见[契约](../subsystems/opendota.md)与[任务](../../.agents/tasks/done/2026-10-02-opendota-provider.md)。真实账号/隐私/线上额度、长期运行及Bot新命令未验证。
