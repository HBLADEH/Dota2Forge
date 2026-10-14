# STRATZ 强势榜、攻略与宿主多轮复盘首版实施

Status: done

## 目标
按用户2026-10-14明确实施授权完成[已确认方案](../../../Dota2Forge_STRATZ_FEATURE_PLAN.md)的P0和P1：共享数据/业务、当前主题卡片、双端指令和宿主原生多轮复盘按需补图。

## 非目标
不自动申请录像解析、不伪造任意时刻库存，不把尚未核实事件/命石写成支持；不生产部署、发布或发送真实消息。

## 验收
- 完成STRATZ最小只读schema/口径核查，合法本机Token由uv注入，证据不含凭据/真实身份/原始比赛响应。
- Core新增受限端口、不可变结果和可追溯事实；领域/用例不依赖SDK/HTTP/SQL/环境。
- 双端使用同一业务和Renderer，来源/窗口/位置/样本/缺失及失败保留；保持旧查询/订阅兼容。
- 复盘复用宿主会话及可信调用者，定位/证据分开、有界与重置清理，正常追问按需取证和补图，报告可选。
- meaningful禁网测试、统一治理/格式/lint/mypy/覆盖率、五包构建与隔离wheel/双端分发验证通过；卡片视觉QA与SDK证据分别记录。

## 影响模块与决策
[Core](../../../docs/subsystems/core.md)、[Renderer](../../../docs/subsystems/renderer.md)、[现有分析](../../../docs/subsystems/analysis.md)、两适配器及发行消费链。P0/P1进度分别记录于[数据](2026-10-14-stratz-data-readiness.md)、[榜单](2026-10-14-hero-meta.md)、[攻略](2026-10-14-stratz-hero-guides.md)、[复盘](2026-10-14-ai-match-review.md)；公共契约/Provider/缓存/权限与生命周期附实施note。

## 验证证据
开工HEAD=f5e26c9，从原分支创建codex/stratz-features，保留全部上轮规划和两份已有GsCore商店历史任务；未附独立工作区。共享Core/Renderer、两个实际适配器/发现桥接/发行链已实现候选；Core/Renderer a8、Dota2UID a15、AstrBot a13。真实来源探针确认7.41f/635桶/10项与3个位置校验样例，聚合位置异常显式停用。[证据说明](../../artifacts/stratz-features-v1/README.md)，原截图、凭据与真实玩家响应未入库。

真实GsCore工具注册/Pydantic/hook与AstrBot4.28.2装饰器/ToolSet/ProviderRequest接口验证通过，使用合成会话验证五轮、按需图、权限与重置/关闭，不当作真实模型/平台联调。生产Renderer合成卡片及390px人工QA通过；五包构建、五份隔离安装及双端候选离线消费exit0。mypy102源码文件、Ruff格式/lint已通过，完整统一检查最终日志为[check-all-final.log](../../artifacts/stratz-features-v1/check-all-final.log)。

最终统一入口exit0：Python3.12.9，2101项禁网测试通过/758.29s，聚合语句与分支覆盖91.03%；scripts/Core/Assets独立94%/90%/92%，门槛80%未改。治理、489文件格式/lint、mypy102源文件全部通过。早期失败与修正分别保留，未删除断言或自动接受快照；发行源哈希仍核验原字节，产物规范LF另作严格校验。

## 阻塞与下一步
首版候选代码、本地产物和统一验证已完成。未发布、部署或发送真实消息。上游聚合位置/窗口异常、英雄等级/中立获得/库存回放、死亡/视野/团战事件仍未支持；[真实会话接续](../active/2026-10-14-native-review-live-acceptance.md)须后续授权，当前不自动执行。
