# 攻略图标、中文天赋与复盘质量约束证据

用户附件只在会话查看，不进入仓库。用户自行测试确认GsCore群聊@多轮与图片可用；代理未发送真实消息，不发布AstrBot。

`probe_constants.py`使用显式uv --env-file .env做公开STRATZ常量只读查询，无比赛/账号。结果[constants.json](constants.json)确认版本190主宰七项天赋中文displayName，ID730内部键special_bonus_attributes且中文为空，故翻译为属性加点，不增加未核实数值。聚合名称版本另行标注，不核实统计周窗口。

同一显式环境以生产StratzHeroes.label_ids只查询公共定义：[implementation-labels.json](implementation-labels.json)确认8/8解析成功，包括属性加点。未查询或保存玩家数据。

[针对性测试](target.log)覆盖独立本场/聚合名称版本、未知名/ID错配/过长/解析失败、保留统计、三个装备图标入口、缺图与超长完整文字回退。

`render_previews.py`绘制6张生产卡片，数据和几何图标均为明确标记的合成演示；公开天赋名称只作展示文本。原始几何素材由脚本生成，未下载官方图。已查看[总览](contact-sheet.png)，三列完整天赋、统计/购买/复盘图标和缺图文字均可读。[尺寸结果](qa.json)最高1780px/289156字节。

提示约束改进不替代真实模型评测；未接入死亡/团战/视野/录像。最终全仓、构建、分支结果见[任务](../../tasks/active/2026-10-15-guide-icons-and-talent-labels.md)。

[统一入口](check-all.log)exit0：2113项禁网测试/486.47秒，聚合覆盖91.04%，scripts/Core/Assets分别94%/90%/92%；Ruff格式/lint、mypy102源文件与治理通过。[五包构建](build-wheels.log)和[隔离安装](smoke-wheels.log)exit0。初始57项选测日志含Pillow弃用警告，测试已改为getcolors，最终统一检查无该警告。
