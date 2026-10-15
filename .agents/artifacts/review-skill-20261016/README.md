# 复盘Skill实施证据

参考项目固定为be6cf7f038c0f548a535d50b723181c0b806a01e（只读clone位于被忽略dist/reference）；阅读SKILL、match-review、fundamentals-operations及MIT。共享资源保留归属/许可证，未复制解析POST脚本或固定版本攻略。

[Skill验证](skill-validation.log)通过。[初步选测](target.log)102项禁网通过，覆盖来源选择、错误边界、同源语义、精确采样/缺失、两端原生会话、Skill代际注销和组件最低版本。[初始失败](target-initial.log)是新增合成fixture用了None而非契约规定MatchAnalysisUnavailable；修正fixture后保留同一缺失场景及断言。

`check_gscore_native.py`读取实际GsCore注册器/hook/Skill库，以合成配置和内存会话/RM/HTTP执行：原生dota2-review注册与Pydantic元数据解析、五轮同会话取数/按需补图、人格禁用、可信身份、重置/注销关闭。[结果](gscore-native.json)、[日志](gscore-sdk.log)。真实模型和平台发送均为false。[初始探针](gscore-sdk-initial.log)误读SDK metadata嵌套层级，修正断言为实际metadata.metadata.version后通过；没有删断言或改SDK。

新指南按overview/economy/items/team选择，使用真实数据字段而不冒充事件已接入；模型输出质量尚未实测。完整统一检查与打包结果按最终任务记录，不将初步选测当作全仓通过。

[统一入口](check-all.log)exit0：2150项禁网测试/590.58秒，覆盖91.11%，scripts/Core/Assets分别94%/90%/92%，Ruff/mypy103源文件通过。名称标签加入前[前轮统一检查](check-before-labels.log)2149项/91.10%通过；[最初格式检查](check-format-initial.log)发现两处未格式化，在最终检查前已修正。

统一检查之后仅澄清提示末句“工具字段”为“比赛字段”，区分来源数据与插件指南；逻辑/结构未再变更，[最终选测](target-final.log)105项通过。最终源码[五包构建](build-wheels.log)/[离线隔离安装](smoke-wheels.log)exit0，[wheel原生解析](wheel-skill.log)确认6份Skill文件、版本1.0.0及0个执行脚本。[SDK日志](gscore-sdk.log)另确认中文标签与当前专题指南进入实际工具结果，仍无真实模型和发送。

源码固定cc591ccfd70b5b389c83fbfd70cf71a5ded85790，[分发生成](build-distributions.log)与[双端本地消费](smoke-distributions.log)exit0；GS ab751ab857f4cc5da7610d08425ea10aefbbcf52的[提交字节核对](committed-bytes.log)25文件/4wheel一致。更新GS候选为a16/Corea9，删除的仅是隔离干净分发clone中被新版本替代的两个已跟踪wheel；没有操作真实宿主。

主仓与GS原codex/stratz-features已推送，远端SHA核实；未合并main、创建标签/Release或推送AstrBot分发。SSH22当时不可用，临时使用443及已有github.com信任键完成验证，不改全局SSH或Git配置。初始失败日志仅去除行尾空白用于git diff --check，失败内容和断言保留。[完成任务](../../tasks/done/2026-10-16-review-skill.md)。
