# AstrBot README 导航居中

Status: done

## 目标
将用户指定的 AstrBot README 顶部四项导航居中，并保持源码/独立分发/Cloud链接有效。

## 非目标
不改 Dota2UID 排版、截图、业务、版本、配置或发布状态。

## 验收
- 四项导航使用居中的HTML段落及可点击链接。
- 安装链接在公开分发指向INSTALL.md，日志指向目标仓库；主项目文档遵守source_ref。
- 现有导航/摘要/源码引用验证保留；统一离线检查通过。

## 影响模块与决策
[README](../../../adapters/astrbot_plugin_dota2forge/README.md)、[生成器](../../../scripts/build_plugin_distributions.py)、[决策](../../notes/implemented/2026-10-12-readme-navigation-center.md)。保留此前截图和双端说明修改。

## 验证证据
已改HTML导航并同步生成器的href转换，更新现有Markdown导航断言为HTML契约。本地v3候选生成成功，逐项核对安装、日志、主项目和问题反馈目标，source_ref固定SHA也通过；源码与分发均保留居中段落。`uv run --locked python scripts/check_governance.py --all` 退出0，治理、Ruff、mypy及全部离线测试/覆盖率门槛通过。`git diff --check` 通过。未启动真实宿主或进行远端页面验收。

## 阻塞与下一步
已完成并归档；本轮未提交或发布，无新增业务能力及待实现项。
