# 双端 README 截图整合

Status: done

## 目标
整合用户提供的七张截图，更新双端 README 展示区、来源记录与发行白名单，保留前轮说明更新及其他已有修改。

## 非目标
不改业务、宿主或真实配置，不伪造/重绘统计，不提交未脱敏原图；不提交、推送或公开发布。

## 验收
- 审查菜单、玩家、近期战绩、比赛三页与主宰出装；隐藏昵称、账号/比赛ID及可回溯来源URL中的ID，其他内容原样。
- 双端共享同一套审查图片，README 清晰呈现主要卡片，长图可展开，注明真实来源和已知版本边界。
- 旧历史原图保留，新增图片可溯源，白名单/ZIP/两份摘要与Cloud图片链接完整。
- 统一离线检查和双端本地分发检查通过，配置图/真实订阅验收仍分列待补。

## 影响模块与决策
[AstrBot README](../../../adapters/astrbot_plugin_dota2forge/README.md)、[Dota2UID README](../../../adapters/Dota2UID/README.md)、[截图来源](../../../docs/assets/screenshots/README.md)、[发行生成器](../../../scripts/build_plugin_distributions.py)。接续[前轮任务](../done/2026-10-12-plugin-readme-refresh.md)；共享展示遵守来源记录。

## 验证证据
已逐张观察七图，用户确认全部来自 GsCore，授权双端复用，并明确选择本地图像工具精确遮挡。菜单/出装按原字节收录，另五图遮挡昵称、账号/比赛ID及URL中的比赛ID，共40个区域。逐像素核对确认遮挡外像素完全一致，尺寸/比例不变，原件未修改；已逐张目视检查，未把未脱敏原件或身份值写入仓库。

七图存于 GsCore 日期目录，双端使用同一文件；玩家/战绩并排，其余五图分别展开并附原图链接。已同步来源/处理摘要、采集指南、主README与发行说明。版本未提供，来源记录明确未知；不把共享展示作为 AstrBot 实机验收。[决策](../../notes/implemented/2026-10-12-plugin-showcase-integration.md)记录图片与分发边界。

两图阶段候选v1生成、双端 SDK-free 离线安装和统一2013项测试均通过。用户确认后补齐七图并加强白名单/ZIP/源图/目标摘要与Cloud HTML引用验证。最终v2候选生成与双端离线安装通过；七图各自的源图/产物SHA256和ZIP字节、GsCore本地引用、Cloud完整图片URL逐一核对通过。AstrBot ZIP为5,116,430 bytes，低于16,000,000上限；UID随包ZIP为18,912,258 bytes。

最终 `uv run --locked python scripts/check_governance.py --all` 退出0：2013项禁网测试通过，Ruff格式/lint、mypy87文件和治理链接检查通过，聚合覆盖率92.52%，scripts/Core/Assets独立覆盖率门槛均通过。`uv run --locked python scripts/smoke_plugin_distributions.py --candidate dist/plugin-distributions/showcase-20261012-v2 --wheels dist` 双端退出0；使用既有匹配wheel，不依赖真实宿主。`git diff --check` 通过。先前预算检查拒绝过长的发行说明，精简正文后恢复通过，未放宽门槛。

## 阻塞与下一步
七图与双端README整合及最终分发验证已完成。两端配置图和真实订阅推送仍待补，英雄攻略/AI Tool尚未实现；本轮未提交、推送、公开发布或运行真实宿主。
