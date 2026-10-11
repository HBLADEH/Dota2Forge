# 远古锻炉主题实施

Status: done

## 目标
落实用户已认可的Dota 2美学方向，统一共享Renderer、图片菜单、玩家／近期／出装／状态／详情及完整宽报告，并让双端帮助说明直接易用。

## 非目标
不改变Provider、业务数据、身份／权限、订阅投递和生命周期；不发布或更改真实宿主配置。

## 验收
- 共享颜色／标题／面板／命令组件，默认标题本地绘制原创遗迹／余烬，官方英雄／装备／徽章继续本地ID映射。
- 菜单按用户目的组织；全量现行命令、字段、来源、缺失、解析及IMP边界保留，双端共用帮助文案。
- 普通780px、宽报告1600px及高度／2MiB上限不变；无图／缺失／长内容及双端回退回归通过。
- 使用生产Renderer生成合成样图，390px常规卡与完整报告人工检查；统一离线检查与打包资源验证通过。

## 影响模块与决策
[Renderer](../../../docs/subsystems/renderer.md)、[设计提案](../../artifacts/theme-redesign-v3/README.md)、[实施决策](../../notes/implemented/2026-10-11-forge-theme.md)、两个适配器展示入口。

## 验证证据
用户明确认可方向并允许实施。开工保留上轮预览及两份已有商店任务；未改动真实宿主配置、凭据或聊天数据。Renderer a6、Dota2UID a11、AstrBot a10为本轮源码版本；Core a7／Assets a1不变，锁文件和生成参考已同步。

共享主题／标题／方切面板／命令提示迁移七类Card及完整报告，菜单按目的组织并保留素材、管理和全套订阅命令；双端共用help_text。十人指标、装备、优势曲线、正负IMP依据、来源、0／未知及匿名完整保留。状态换行保留MMR等短拉丁词。

[生产样图脚本](../../artifacts/forge-theme-v3/render_samples.py)生成22张有图／无图合成卡；[检查记录](../../artifacts/forge-theme-v3/qa.json)尺寸、文字边界和重叠通过，最大688,643字节。390px常规卡、未知／状态、完整总览与队页人工检查通过。官方素材样图仅保存在忽略目录。

`uv run --locked python scripts/check_governance.py --all`最终exit0：[完整日志](../../artifacts/forge-theme-v3/offline-complete.log)，2012项禁网测试、无告警；398文件格式／lint、mypy87源码文件通过。聚合覆盖92.49%，scripts／Core／Assets分别94%／93%／92%，三组均超过80%。最终换行专项44项通过；前轮布局与双端专项173项通过。

`uv build --all-packages`五个wheel／sdist构建通过；`scripts/smoke_wheels.py`五包隔离安装／导入通过。四个GsCore实际运行wheel另经现行validate_wheel校验通过，[日志](../../artifacts/forge-theme-v3/runtime-wheels-final.log)。没有放宽位图禁入门槛。

首轮全量7项失败：开发环境旧editable元数据与版本固定断言未同步，原创PNG被运行包契约拒绝；同步锁定开发环境和实际版本断言，改为本地绘制遗迹／余烬后兼容专项通过。保留失败日志，未删除断言或修改治理脚本／policy。一次全量2011项通过后，最后换行修正另作2012项全量复验。归档后的预算／链接／治理复核见[记录](../../artifacts/forge-theme-v3/governance-final.log)，git diff --check通过。

## 阻塞与下一步
源码实施完成，无阻塞。未发布Release、切换真实宿主或发送消息；新主题客户端压缩与聊天阅读、权限和订阅真实递送仍未联调。完整英雄攻略、AI分析等规划能力仍未实现。本地显式decor.header继续优先，已有宿主背景不会因源码修改自动切换。
