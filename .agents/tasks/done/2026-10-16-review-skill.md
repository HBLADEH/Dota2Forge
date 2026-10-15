# 数据驱动的多维复盘 Skill

Status: done

## 目标
参考dota2-newbie-assistant，提供随插件分发的运行时复盘Skill；优先STRATZ，无法完成时显式使用OpenDota；改善多轮建议的依据、覆盖面与可执行性。

## 非目标
不复制自动POST录像解析、不下载录像、不发送真实聊天、不发布AstrBot；不把Skill规则测试当真实模型质量验收。

## 验收
- 阅读并固定参考项目源码版本，保留所需许可证与归属说明。
- STRATZ可用时保持同源证据；回退有明确原因、来源，PRIVATE不绕过，限流/认证/格式错误不隐瞒；不拼接两源数值。
- Skill按问题加载综合/对线经济/出装/团队节奏指南，含数据完整度检查、事实与推断、可执行下一局建议，普通多轮不变。
- 双端消费同一分析指南，GsCore注册原生Skill并验证生命周期；AstrBot不发版。
- 合成离线回归、统一检查、打包隔离消费通过，更新既有授权测试分支。

## 影响模块与决策
Core ReviewService/基础设施/内置资源，GsCore与AstrBot原生桥接，分发构建。Provider策略与公共契约附note，同步文档。

## 验证证据
参考be6cf7f固定版本、MIT归属、Skill前置校验、实际GsCore/Pydantic发现/注册/代际注销与五轮工具链通过；依赖和数据均合成，无真实模型/平台发送。两端中文名称随事实提供。统一检查2150项/590.58秒、覆盖91.11%，scripts/Core/Assets94%/90%/92%，Ruff/mypy103源文件通过。随后仅澄清提示末句的“比赛字段”，105项最终选测和重建/隔离安装通过；6份wheel Skill资源原生解析通过。[证据](../../artifacts/review-skill-20261016/README.md)。

## 阻塞与下一步
源码固定cc591ccfd70b5b389c83fbfd70cf71a5ded85790，双端本地候选分发消费通过；GS提交ab751ab857f4cc5da7610d08425ea10aefbbcf52的25文件/4wheel与生成候选逐字节/摘要一致。主仓与GS原codex/stratz-features均推送并核对远端SHA；没有合并main、创建Release/标签、推送AstrBot分发或修改真实宿主。

候选Dota2UIDa16/Corea9/Renderer8/Assets1，内置Skill1.0.0；更新测试分支并重启后由用户验证模型效果。AstrBot不发布，真实模型分析质量与OpenDota现场兜底仍未在线验证。本轮无真实消息发送。
