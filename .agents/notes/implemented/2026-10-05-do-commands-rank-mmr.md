# do 指令与共享段位 MMR 估算

Category: feature
Related task: [任务](../../tasks/done/2026-10-05-command-mmr-guide-survey.md)
Related code: [共享估算](../../../packages/dota2forge-core/src/dota2forge_core/domain/ranks.py)、[菜单与玩家卡](../../../packages/dota2forge-renderer/src/dota2forge_renderer/engine.py)
Related docs: [估算契约](../../../docs/subsystems/ranks.md)、[双端接入](../../../docs/cookbook/astrbot.md)

## Problem
用户要求现有dotaxxx改doxxx，dota玩家改do查询并展示预估MMR。两个适配器分别注册解析/宿主入口，菜单和订阅提醒也引用命令。现有STRATZ只读steamAccount.seasonRank，PlayerProfile没有精确MMR。仅修改一端或将段位/估算当实测分数会造成入口和语义不一致。

## Decision
所有现有前缀同步改do；玩家主命令为do查询，AstrBot原段位/最近别名变do段位/do最近。旧入口不再注册，不引入do玩家。包括绑定、详情、分页、订阅、状态、停用及文本提示；品牌/包名/内部HTTP路径不改。

Core新增纯函数estimate_rank_mmr与不可变RankMmrEstimate，使用community-medal-v1静态社区阈值。普通段位给包含边界的区间，冠绝只给5620+下界；未知、未定级、不支持编码不估算。共享格式函数供玩家卡和双端文本使用，保留原来源时间并明确估算/非精确/段位滞后。无需新网络请求、Provider字段、数据库迁移或缓存schema。

## Alternatives considered
- 保留旧别名：不采用，用户明确要求替换入口，减少两套菜单/指令维护。
- 每个适配器计算：不采用，业务进入Core，避免双端阈值漂移。
- 给区间中点或单一固定分数：不采用，段位无法证明玩家精确位置，冠绝无可信上界。
- 改取其他来源MMR：不采用，既有来源不提供精确分数，无授权的数据拼接或失败回退不符合来源契约。

## Consequences
旧命令失效；部署须同时更新Core、Renderer、适配器及桥接。玩家卡高度850改960，仍在1600px/2MiB上限内。社区阈值可能随游戏变化，应按契约复核，不能当成官方保证。已有工作区图片/图标/部署改动保留；历史任务和证据中的旧命令不重写。本次未部署/重启宿主或发消息。

## Verification
262项针对性禁网测试及统一入口1254项测试通过；Ruff/mypy、聚合92.79%和scripts/Core独立门槛通过。覆盖估算边界、下降、非法输入、双端文本、图片完整标签/边界及替换后的命令拒绝。四包构建/隔离安装导入成功；43张合成卡及手机预览通过布局验证，传奇/冠绝/菜单人工查看无裁切。玩家卡日志旧高度断言更新为960，边界门槛保留；失败/通过日志见关联任务。宿主部署/真实聊天未验证。
