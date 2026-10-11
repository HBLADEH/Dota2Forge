# 远古锻炉主题源码验收

本轮落实用户认可方向，使用实际共享PillowRenderer，非上轮独立设计脚本。菜单、玩家／未知、近期／空、状态、旧详情、热门出装及完整报告共11类，各渲染有图／无图版本；合成fixture来自tests/renderer，不读取真实账号／配置／聊天。含Valve素材的图只留忽略目录`.dota2forge-assets/forge-theme-v3/`，不随MIT包提交。

[复现脚本](render_samples.py)运行`uv run --locked python .agents/artifacts/forge-theme-v3/render_samples.py`，记录[尺寸／重叠检查](qa.json)。原始PNG不改字；qa及phone前缀加外部合成标识，不作为消息递送证据。overview.png为四张生产常规卡的可读总览。

源码版本Renderer a6、Dota2UID a11、AstrBot a10，Core a7／Assets a1不变。默认标题本地绘制遗迹切面／余烬光效，不随包提供位图；现有显式decor.header仍优先，已配置旧背景的宿主不会被源码修改自动替换。[资源说明](../../../packages/dota2forge-renderer/src/dota2forge_renderer/assets/v1/README.md)与[实施决策](../../notes/implemented/2026-10-11-forge-theme.md)。

最终[统一离线检查](offline-complete.log)exit0：2012项禁网测试、Ruff／mypy87源码文件通过，覆盖92.49%；五包[构建](build-final.log)与[隔离安装／导入](wheel-smoke-final.log)通过，四个实际GsCore运行wheel通过[现行校验](runtime-wheels-final.log)。22张样图最大688,643字节，尺寸／文字检查和人工阅读通过。原创PNG曾被位图禁入校验拒绝，已改为本地绘制，没有改门槛；失败及复验日志保留。

完整验证与未联调项见[实施任务](../../tasks/done/2026-10-11-forge-theme-implementation.md)。没有发布Release、修改真实宿主配置或发送消息；官方素材／配置／权限边界沿用现行契约。
