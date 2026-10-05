# 中文展示、装备图片与比赛详细统计

Category: feature
Related task: [本轮任务](../../tasks/done/2026-10-06-readable-cards-and-store.md)
Related code: [共享 Renderer](../../../packages/dota2forge-renderer/src/dota2forge_renderer/engine.py)
Related docs: [图片契约](../../../docs/subsystems/renderer.md)

## Problem
出装卡仅文字，比赛详情只展示 KDA/GPM/XPM 与装备 ID。用户要求对应资源图片、更详细数据和合理排版，并要求已有 PR #40 及商店文案使用口语化中文。

## Decision
出装按四阶段各五件装备横排，复用本地受校验的英雄/装备图，名称可两行，保留次数及来源边界。比赛详情按实际阵营每页最多三人，保留全部十人和分页顺序，英雄图、六装备图及名称与统计分区。近期战绩仍每页五场。

MatchParticipant 末尾新增可选 level/last_hits/denies/net_worth/hero_damage/tower_damage/hero_healing，非负整数且禁止 bool，0 与 None 区分；不从其他源补值。STRATZ 查询选取 level/numLastHits/numDenies/networth/heroDamage/towerDamage/heroHealing，类型依据[已有字段核查](../../artifacts/hero-builds-v1/stratz-schema.json)的 MatchPlayerType；OpenDota读取对应 REST 字段。新增字段缺失/null均为未知，非法值失败；既有严格字段规则不变。新增选择未在线联调。

订阅详情 JSON 编解码保存新增字段，读取旧 JSON 时缺失键为 None，不改 SQLite schema。两端图片/文本消费者及存储消费者一起更新；订阅文本报告沿用原摘要，不自动扩展报告或修改 MVP 计算。文本回退保留完整装备名称/ID及新字段；超长数值仍允许 RenderError 后用同次数据回退，绝不隐藏未知 ID。

PR 和商店介绍改为中文，保留首次安装需运行安装器、平台验证范围及预览版状态；生成器同步相同文案。发布的 a3 和真实展示截图不冒充本轮新布局。

## Alternatives considered
- 在五人卡中继续压缩字体：手机阅读密度过高，改成三人分页，代价是完整十人通常发送四张图。
- 绘图时下载素材：破坏离线资源边界，继续使用显式配置的本地素材包；缺图用占位。
- 仅调整布局：无法满足详细数据诉求，因此扩展可选观测字段，同时兼容旧持久化数据。

## Consequences
公共模型保持旧位置参数兼容；STRATZ 选择增加七个标量，仍是原先一次请求，无换源/缓存/重试变更。双端共用数据和绘图，新增资源无需额外下载。治理脚本与门槛未变；生成器文案属于 scripts 变更，保留维护者评审要求。

## Verification
禁网测试覆盖两源新增字段、非法类型/零/未知、旧存储与新存储往返、两端文本、十人四页和正确图片像素。合成全量/缺失/无图样图及手机预览见[本轮证据](../../artifacts/readable-cards-v1/README.md)；统一检查1528测试通过、Ruff/mypy通过，治理工具/Core覆盖96%/93%。未部署生产、发布新包或发送真实聊天。
