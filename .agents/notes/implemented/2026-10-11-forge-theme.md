# 远古锻炉共享主题与直达帮助

Category: feature
Related task: [主题实施](../../tasks/done/2026-10-11-forge-theme-implementation.md)
Related code: [共享主题](../../../packages/dota2forge-renderer/src/dota2forge_renderer/theme.py)
Related docs: [展示契约](../../../docs/subsystems/renderer.md)

## Problem
用户认可[设计方向](../proposed/2026-10-11-theme-redesign.md)并明确允许实施，要求继续贴合Dota 2游戏美学。旧卡片虽深色但标题／正文层级接近，菜单以命令排列，未配置素材时缺乏主题背景。

## Decision
共享theme模块集中炭黑、暗金属、铜金、余烬红及阵营色；Canvas统一石面标题、方切面板、4px状态边线、命令提示和来源。迁移全部七类Card及宽报告，保留原有业务字段与分页、编码上限、匿名、缺失和文本回退。

默认标题由Pillow本地绘制原创遗迹切面、暗金属和余烬光效，不读取位图／联网；既有显式decor.header仍优先，不更改真实素材配置。生成图只保留为设计参考，不进入wheel。字体继续完整Noto/OFL，不分发本机Georgia。

共享help_text由Dota2UID和AstrApplication同时消费，按目的给命令，保留完整参数／订阅／素材说明及权限边界；无新宿主命令、按钮或平台依赖。IMP、十人数据与正负表现依据不删，近期保留ID／开始／时长／KDA／GPM／XPM；其模型没有装备字段，不为贴样稿而新增请求或编造装备。

## Alternatives considered
复制预览脚本进生产会丢失字段与缺失状态，因此迁移生产组件并保留数据布局。初次把原创PNG随包提供，被现行BundledRuntime位图禁入校验拒绝；改为原创本地绘制，默认安装也有主题，保持校验门槛。既有本地背景允许覆盖。采用本机Georgia不便携，继续使用已授权Noto字体。

## Consequences
公共Card输入及适配器回复接口保持兼容，唯一新增的展示函数检查两端实际消费者。普通菜单1780px；其他卡／报告沿用现行尺寸，最高1800／3200px及2MiB。本文表示源码实施，不表示已发布、已切换宿主或新主题聊天验收完成。

## Verification
统一离线2012项、Ruff／mypy87源码文件通过，覆盖92.49%；五包构建与隔离安装通过，四个实际GsCore运行wheel通过现行校验。22张合成卡通过尺寸及视觉检查；来源／未知／0、长装备名与双端回退回归保留。完整证据见实施任务，未修改policy、工作流、治理门槛或以样图替代实机验收。
