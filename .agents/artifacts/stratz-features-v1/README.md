# STRATZ 首版实施与验证证据

2026-10-14 开发候选，未发布、部署或发送真实平台消息。Core/Renderer a8、Dota2UID a15、AstrBot a13、Assets a1；来源分支为 `codex/stratz-features`，起点 f5e26c9。原截图与真实玩家原始响应未复制到仓库。

## 来源核查

`probe_*.py` 是显式只读诊断，只有 `uv run --env-file .env python <脚本>` 才注入本机凭据；普通检查不读取 .env。这些脚本不保存 Token、账号/昵称、真实比赛 ID 或原始玩家响应。schema 字段名、公开英雄统计和技能名称不是玩家身份。

- [schema.json](schema.json)、[readiness.json](readiness.json)、[followup.json](followup.json)、[scope.json](scope.json)、[labels.json](labels.json) 保留字段形状、公开口径与数量/状态。`winDay.take` 为日数；当前版本 7.41f，7 日窗口实际仅返回 5 日且滞后，不补零、不移动窗口。
- [sample-shape.json](sample-shape.json) 是修复前的失败诊断：嵌套 ability 查询被拒绝。脚本引用当前查询，重新执行可能与这份历史结果不同。
- [implemented.json](implemented.json) 是修复后的真实实现探针：635 个日桶、10 项榜单、3 个实际 3 号位样例，独立中文技能名成功。攻略聚合位置标记不一致，保留 `scope_mismatch`，不据此推荐；技能 level 是零基技能阶数，不能作为英雄等级。

真实核查仅覆盖所记录的小查询，不能证明全英雄、长期可用性或事件完整性。

## 卡片 QA

`uv run --locked python .agents/artifacts/stratz-features-v1/render_previews.py` 使用生产 Renderer 和合成 fixture，输出六张卡片、同源文字与 [qa.json](qa.json)。全部标注合成；780 px、最高 1780 px、最大约 0.19 MiB。已人工查看 [390 px 总览](contact-sheet.png)：文字可读、无溢出，概览随内容缩短，四列加点按真实记录序号，图片不模拟可操作库存滑块。

## SDK 隔离验证

- GsCore：`D:/bot/gsuid_core/.venv/Scripts/python.exe .agents/artifacts/stratz-features-v1/check_gscore_native.py`，[结果](gscore-native.json)、[日志](gscore-native.log)。真实工具注册/Pydantic Schema/hook registry；会话、资源与有副作用依赖为合成替身。验证五轮取证、泛化追问召回、persona 禁用、子任务出站拒绝、同 ID 代际重置与注销排空。
- AstrBot：`D:/AstrBot/backend/python/python.exe .agents/artifacts/stratz-features-v1/check_astr_native.py`，[结果](astr-native.json)、[日志](astr-native.log)。SDK 4.28.2 的真实装饰器、ToolSet、ProviderRequest、event.request_llm；conversation manager 为合成替身。验证显式 Schema、同会话五轮、一次补图与文字事实、同 ID 历史重置与关闭。

这两项证明 SDK 接口接入，不是实际模型的工具召回、自然语言质量或消息递送验收。真实联调见 [接续任务](../../tasks/active/2026-10-14-native-review-live-acceptance.md)。

## 离线与打包

统一入口 `uv run --locked python scripts/check_governance.py --all` exit 0：2101 项禁网测试通过/758.29 秒，聚合覆盖 91.03%，scripts/Core/Assets 分别 94%/90%/92%，80% 门槛未改；治理、Ruff 格式/lint、mypy 102 源文件通过。结果记录在 [实施任务](../../tasks/done/2026-10-14-stratz-feature-implementation.md)，[最终日志](check-all-final.log)。归档后文档/链接/生成漂移复核另见 `governance-final.log`。

保留早期失败记录，不覆盖成通过：`check-all.log` 包含未同步候选元数据、缺少 fixture AI 资源和英雄歧义回归；`check-all-v2.log` 剩旧版本断言及源文件 CRLF/产物 LF 的比较问题。现分别验证源文件原字节校验和与打包后规范字节，未改变生成器的校验契约。`distribution-corrections.log` 的 3 个断言通过，但单独选测仍触发全仓覆盖率不足，因此不将其 exit 1 宣称统一验证成功。

推送归档时仅清除两份早期失败日志的行尾空格以通过diff空白检查，未删除失败段落、修改结果或重新接受快照。

`build-wheels-final.log`、`smoke-wheels-final.log`、`build-distributions.log`、`smoke-distributions.log` 分别记录最终五包构建、五个隔离安装、双端候选生成和离线隔离消费。产物位于忽略的 `dist/plugin-distributions/stratz-features-20261014-v1/`，依赖在 `dist/release-assets/stratz-features-20261014-v1/`；manifest 标记 local_candidate。链接与 GitHub 下载地址仅为未发布候选元数据，不能当作已发布可下载版本。

原因见 [实施 note](../../notes/implemented/2026-10-14-stratz-hero-and-native-review.md)，用法见 [榜单/攻略](../../../docs/cookbook/hero-meta.md) 与 [正常对话复盘](../../../docs/cookbook/native-review.md)。
