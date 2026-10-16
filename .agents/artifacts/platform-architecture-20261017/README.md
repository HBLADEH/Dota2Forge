# 双宿主架构图验证

2026-10-17：[文档](../../../docs/subsystems/platform-adapters.md)先以手绘简图解释接入方式，再保留三份 Mermaid 结构/时序源码及代码索引。

## 手绘图

使用内置 image_gen 生成并编辑，没有使用 CLI。[初版](../../../docs/assets/architecture/dota2forge-handdrawn-v1.png)及其[提示词](imagegen-prompts.txt)保留。用户指出留白过多、渲染发送顺序不够直观后，生成[当前 v2](../../../docs/assets/architecture/dota2forge-handdrawn-v2.png)，1536×1024；[v2 编辑提示词](imagegen-flow-v2-prompt.txt)记录完整构图约束。

人工核对标题、两个宿主与插件、各自身份/权限/消息、Core 业务范围、来源名称、Renderer 两端共用和 AI 宿主归属。共享 Core 表示复用代码，各端独立运行；简图省略 Assets、SQLite 和调度细节，完整说明在同一文档。

v2 用两条紧凑接入路线及底部五步回复链明确顺序：插件整理 Core 业务结果 → Renderer 渲染 → PNG 返回同一插件并组装消息 → 对应宿主发送 → 用户收图。重复“对应插件”表示同一插件的处理阶段，无额外模块；没有 Core 直接渲染或 Renderer 直接发送。核对 Dota2UID Runtime.dispatch 和 AstrApplication._prepare/dispatch 与该顺序一致。

## 结构与时序

Mermaid 11.12.0 成功解析、渲染三份源码，无 error-icon。图源摘要见[验证记录](diagram-validation.json)，人工检查[总览](overview-final.png)、[查询时序](query-sequence.png)与[复盘时序](review-sequence.png)，修正了初稿分组标题遮挡及易混淆连线。

## 离线检查

`uv run --locked python scripts/check_governance.py --all` 退出 0：治理、Ruff 格式/lint、mypy（103 个源文件）、pytest（收集 2150 项）及 scripts/Core/Assets 三个独立 80% 门槛通过。最终文档调整后另调用原检查器的 `check_repository(ROOT)` 复核预算、链接、依赖边界、note 与生成参考；没有修改或跳过原统一入口的任何门禁。

本轮未改业务实现、未部署宿主、未读取凭据或发送聊天，不以图示生成/离线测试替代 AstrBot 多轮、订阅真实递送等实机验收。工作区其他发行任务的并发产物保留。

v2 仅调整 PNG、说明及任务记录，复核图片、文档治理、图源摘要与 diff 空白；完整统一离线入口沿用上轮退出0的结果，本次未重跑 pytest 或宿主联调。

## README 收录

用户随后授权将确认的 v2 图插入主 README 并提交推送。README 在项目介绍后、模块表前直接嵌图，补全 Core→插件→Renderer→插件→宿主→用户顺序，并链接详细时序；主仓发行提示同步为经 GitHub API 核实的 UID a16／Astr alpha.14。

[图像及位置核对](readme-validation.json)确认引用一次、使用已确认 PNG 的原始摘要、放置于模块表之前。GitHub Markdown API 解析通过；其返回正文配本地原 PNG 作[版式预览](readme-preview.png)，图像以960×640完整显示，人工核对无覆盖或裁切。预览不代替已发布页面或宿主联调。

本次重新执行统一离线入口退出0，完整输出见[README 检查日志](readme-check-all.log)：2150项禁网测试通过（641.22秒），聚合覆盖91.11%，scripts/Core/Assets分别94%/90%/92%，Ruff与mypy通过。提交与远端结果记录在对应接续任务。

图文提交1560c79529b0e6ad5d347db2db9b5a065b4d8ac7已推送至codex/readme-architecture，[远端核对](push-verification.json)验证分支及README、v2图片、详细文档blob一致。[PR #25](https://github.com/HBLADEH/Dota2Forge/pull/25)已创建但未合并，交付接续见[完成任务](../../tasks/done/2026-10-17-readme-architecture-push.md)。
