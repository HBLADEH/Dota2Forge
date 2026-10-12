# 订阅比赛详情卡

Status: done

## 目标
用户已确认订阅能够触发，要求将比赛文字提醒改为比赛详情卡。复用现有比赛报告，双端图片模式发送订阅总览与分队详情，保留事件、来源、未知字段及有限观察边界。

## 非目标
不改Provider、检查点、数据库、评分或订阅授权；不保存用户提供的账号/比赛/事件样本。不发布或替换正在运行的宿主，不发送真实聊天。

## 验收
- [x] 完整比赛订阅复用总览与分队详情，明确订阅玩家、事件ID、非官方表现与来源时间。
- [x] 双端图片模式使用现有Renderer生命周期；整组渲染后单次宿主调用，仅RenderError回退同一快照的完整分段文本。
- [x] 文字模式及段位/日报/缺详情事件正常；取消、程序错误、未知回执不盲发或确认。
- [x] 统一离线检查和合成卡片视觉验收通过；记录尚未验证的真实宿主与聊天。

## 影响模块与决策
[Renderer](../../../packages/dota2forge-renderer/)、[Dota2UID](../../../adapters/Dota2UID/)、[AstrBot](../../../adapters/astrbot_plugin_dota2forge/)、[订阅契约](../../../docs/subsystems/subscriptions.md)、[Renderer契约](../../../docs/subsystems/renderer.md)。沿用[订阅投递](../../notes/implemented/2026-10-02-subscription-delivery.md)和[完整报告](../../notes/implemented/2026-10-09-match-analysis-report.md)，新增[展示与依赖决策](../../notes/implemented/2026-10-12-subscription-match-cards.md)。

## 验证证据
最终`uv run --locked python scripts/check_governance.py --all`通过：2054项禁网测试，聚合93.08%、治理工具94%、Core93%、Assets92%，Ruff及mypy87源文件通过。[日志](../../artifacts/subscription-match-cards-v1/offline-check.log)。`uv build --all-packages`及`uv run --locked python scripts/smoke_wheels.py`五包构建/隔离导入通过，日志见[证据目录](../../artifacts/subscription-match-cards-v1/README.md)。

27项Renderer/报告专项、双端23项投递专项、Astr完整66项及包/分发75项检查通过。合成总览1600×2556、队页1600×3020，最大470742字节，文字边框/重叠及人工目视无裁切；文本各段≤1400。缺曲线压缩、分析null/空/部分缺失区别保留。来源时间不同不合并，匿名无身份。

开发版本Renderer a7、UID a14、Astr a12，双方Renderer下限a7；Astr直装静态模板同步当前组件。旧公开产物未覆盖。修改文本/产物扫描未发现用户提供的主账号、比赛或事件样本；git diff --check通过。原有两个未跟踪任务文件保留，不改policy、工作流或治理脚本。

## 阻塞与下一步
源码与合成验收完成。生产安装、真实聊天压缩及发送回执本轮未验证，继续由[Step13](../active/2026-10-02-subscriptions.md)跟踪。发布/部署另行授权，不替用户发送真实聊天。
