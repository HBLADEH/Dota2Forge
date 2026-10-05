# do 指令、段位 MMR 估算与英雄攻略源调研

Status: done

## 目标
双端现有 dota 前缀改为 do，玩家入口改为 do查询；图片与文本显示明确标注的预估 MMR。调研 do[英雄名或简称]攻略 的稳定来源，先交付方案再决定实现。

## 非目标
不部署/重启宿主、不发聊天消息；不声称取得精确 MMR，不实现未经选择的攻略源。保留工作区已有插图、段位图标及部署修改。

## 验收
- 双端命令解析、发现桥接、菜单、帮助、订阅提示、现行操作文档统一使用 do，旧入口不再注册。
- 段位估算由共享 Core 提供；文本回退与图片含相同预估区间/下界和非精确说明。未知、未定级、非法编码不编造数值。
- 攻略调研记录公开接口/许可/更新/版本/位置/中文别名适配及获取证据、局限和建议。
- 统一离线治理、Ruff、mypy、禁网 pytest 与覆盖率检查通过；合成卡片视觉验证。

## 影响模块与决策
[Core](../../../packages/dota2forge-core/src/dota2forge_core/)、[Renderer](../../../packages/dota2forge-renderer/src/dota2forge_renderer/)、[Dota2UID](../../../adapters/Dota2UID/)、[AstrBot](../../../adapters/astrbot_plugin_dota2forge/)、[开发检查](../../../docs/cookbook/development.md)。[已实现指令/估算决策](../../notes/implemented/2026-10-05-do-commands-rank-mmr.md)与[待选择攻略来源](../../notes/proposed/2026-10-05-hero-guide-source.md)分别记录。

## 验证证据
已阅读根/范围规则、Core/Renderer/双端宿主契约、开发指南及有效 Provider 决策；已检查已有修改。现有 PlayerProfile 只含 rank_tier，STRATZ 查询 seasonRank；未提供精确 MMR。

双端解析/宿主桥接/菜单/帮助/订阅/分页/管理入口同步do，玩家为do查询；原段位/最近别名改do段位/do最近。Core纯函数给社区段位区间/冠绝5620+下界；未知/未定级不估算，图片/文本带相同非精确说明，PlayerProfile/Provider/缓存/SQLite不变。

262项针对性禁网测试通过；统一 `uv run --locked python scripts/check_governance.py --all` 最终1254项禁网测试通过、Ruff格式/lint、mypy63源文件、综合92.79%、scripts97%/Core93%独立门槛通过。`uv build --all-packages`及`uv run --locked python scripts/smoke_wheels.py`四包构建/隔离安装导入通过。43张生产合成卡片及390px预览生成；人工核对传奇/冠绝与菜单，MMR/徽章/来源/免责声明可读且无裁切。失败与修正日志保留于[交付证据](../../artifacts/command-mmr-guide-v1/README.md)。

匿名公开调研：D2PT接口403；Spectral目录/许可/样本200，123份.build、最近2026-08-09、抽样7.41e且非商业许可；OpenDota出装200但不提供完整攻略。STRATZ官网说明有攻略与GraphQL，未用Token验证schema。完整建议见[方案](../../../docs/cookbook/hero-guides.md)。

## 阻塞与下一步
本任务源码/离线验证/攻略源方案完成；未部署、重启宿主或发送聊天消息，新命令/MMR真实聊天未验证。后续升级需同时更新Core、Renderer、对应适配器及发现桥接。攻略尚未实现，建议先显式核验STRATZ两个英雄/位置的schema/版本/样本与限流，再由用户选择完整攻略或缩小为出装参考；另开实施任务。
