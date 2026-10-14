# 2026-10-15自测反馈修复证据

用户提供的六张图只在会话中查看，未复制到仓库。当前修复仍是codex/stratz-features测试候选，AstrBot不发版，不修改真实宿主配置或发送QQ群消息。

## 来源与复盘事实

`probe_guide_shapes.py`经显式`uv run --env-file .env`做主宰1号位小范围只读诊断。修复前220技能桶中14个ID0触发Invalid ability ID，3个单场候选均invalid_response；图片中的物品桶本身可用。修复后[guide-shapes.json](guide-shapes.json)确认764物品桶/220技能桶/8天赋桶、3个实际1号位样例，升级18/23/24、购买20/23/24，模块错误为空。周索引仍未映射日期，0仍为未标识技能，不猜属性点。

`probe_review_shape.py <比赛ID> <英雄>`核对用户指定比赛，参数只在内存/显式命令中使用，不保存到脚本或结果。[review-shape.json](review-shape.json)确认目标唯一匹配、1条个人经济序列/38条购买/2条团队序列，analysis_error为空、序列化无身份。说明来源确有详细数据，不能只凭旧短回复分析。两份JSON仅保留公开形状、数量/布尔，无账号、昵称、比赛ID、凭据或玩家响应。

## 追问边界

真实SDK的`agent_run/tools.py:_fire_tool_hooks`构造H14上下文时不填query。旧隔离探针手工填了问句，漏掉现场差异；新桥接读取同一可信event.raw_text，且识别“这把有什么问题”。[SDK结果](gscore-native.json)、[日志](gscore-sdk-final.log)在真实GsCore注册器/Pydantic/hook类上验证空query回退、工具召回、persona禁用、子任务出站拒绝、重置与关闭；会话与资源仍为合成替身，没有模型或平台发送。

用户设置“仅@才回复”保持不变；群聊先do复盘定位，再每次@机器人追问。工具取本主题详细事实并沿用英雄/比赛，提示不只读旧短摘要，实际模型表现仍需用户自测。

## 卡片与离线验证

`render_previews.py`用生产Renderer和明确标记的合成数据生成8张780px卡片及[QA](qa.json)，最高1780px、最大189881字节。已人工查看[390px总览](contact-sheet.png)：ID0占位、物品去重、说明换行、缺模块不发送空白页、页数正确。无原图或真实玩家数据。

针对性禁网回归52项通过：[target-final.log](target-final.log)，涵盖ID0/模块独立失败、缺页抑制、H14空问句、同会话主题工具；Ruff/mypy通过。五包构建与隔离安装exit0：[build-wheels.log](build-wheels.log)、[smoke-wheels.log](smoke-wheels.log)。完整统一检查仍以最终日志/任务实际结果为准，不将选测结果代替全仓门槛。

统一入口exit0：[check-all.log](check-all.log)，2106项禁网测试/401.26秒，聚合覆盖91.01%，scripts/Core/Assets各94%/90%/92%，80%门槛未改；治理、Ruff格式/lint、mypy102源文件通过。选测与SDK证据是补充，不代表真实模型或QQ群消息验收。

原因见[实施note](../../notes/implemented/2026-10-15-stratz-followup-and-card-fixes.md)，最终检查/分发/推送见[任务](../../tasks/done/2026-10-15-stratz-followup-and-card-fixes.md)。

固定源码SHA `3a38f64e019b00c090ae6f838fa324430bb7288e` 的候选位于 `dist/plugin-distributions/stratz-feedback-20261015/`；[生成](build-distributions.log)、[双端隔离消费](smoke-distributions.log)exit0，[提交字节检查](committed-bytes.log)25文件/4wheel全部匹配。GS测试分支提交`110cd6f8688d08c95201101885079833fd054e2d`，主仓/GS均推送codex/stratz-features，未推送Astr分发或创建Release/标签。

用户已将旧GS候选合并至main(a263b16)。新修复仍在测试分支，安装者需fetch并切到codex/stratz-features更新后重启；未发布候选a15版本号沿用，以新manifest/运行指针摘要辨别。主仓固定源码与GS修复都可按提交SHA核实，真实模型/群聊图片仍需用户自测。
