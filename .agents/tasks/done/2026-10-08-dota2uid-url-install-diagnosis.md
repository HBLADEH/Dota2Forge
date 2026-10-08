# Dota2UID URL 安装后无响应排查

Status: done

## 目标
核对项目文档、公开分发和截图中 URL 安装状态，定位 do帮助 无响应并交付可执行修复步骤。

## 非目标
不改变既有开发中修改，不发布版本、不操作未知远端宿主或发送真实聊天消息。

## 验收
- 核对实际分发入口、依赖与宿主热加载语义。
- 区分截图已证实的事实与待确认的运行状态。
- 提供匹配部署环境的恢复与验证步骤，记录仍需用户确认的信息。

## 影响模块与决策
[公开安装](../../../docs/cookbook/gscore-public-install.md)、[宿主契约](../../../docs/subsystems/gscore-host.md)、[分发契约](../../../docs/subsystems/plugin-distribution.md)。本轮先只读排查，不改架构或公共契约。

## 验证证据
已检查工作区，保留全部已有修改。截图显示 Git remote 查询成功与收到 do帮助，未显示 Dota2UID 导入成功或命令注册。用户确认安装地址为 HBLADEH/Dota2UID，安装后仅热加载，未完整重启。

2026-10-08匿名API/raw核对：公开main清单为三个0.1.0a4运行包，Releases含对应wheel和安装器所需清单；三个项目PyPI JSON均404，gscore-mirror/Dota2UID API亦404。公开入口先执行版本guard，再注册do命令。空Token进入awaiting_config后仍返回配置提示，不应单凭空Token解释完全无回复。

核对本地固定上游87c06f1及当前master 9e4ad01b52b39922f397abbe57b4c52962544b55：reload_plugin未调用flush_pending_installs；镜像管理查不到商店条目时恢复GitHub回退gscore-mirror。结合历史禁网热加载探针，最符合现象的是缺运行依赖导致导入失败；镜像源变化的具体操作及实际失败日志仍未取得。

统一离线命令uv run --offline --locked python scripts/check_governance.py --all退出0：335文件格式、Ruff、mypy82源文件、1608测试通过（261.68秒）；工具/Core/Assets覆盖率96%/93%/92%，总93.03%。这些是当前工作区离线证据，不是用户宿主修复或聊天验收。

恢复步骤：核对并必要时恢复origin至https://github.com/HBLADEH/Dota2UID.git；退出宿主进程，以实际宿主Python运行插件install_runtime.py并指定同一--host-python，确认安装器/pip check通过，再冷启动。首启在data/Dota2UID/config.toml填写本机Token和独立namespace，重新加载后测试do帮助/do菜单。官方Docker Compose的/venv安装可通过stop服务、run --rm --no-deps覆盖entrypoint运行安装器、up -d完成，保持既有挂载卷；bundle配置需使用原-f文件。

## 阻塞与下一步
诊断与恢复方案已交付；尚未收到部署方式、导入错误或安装器输出，无法确认实际包状态。用户宿主安装、冷启动、首次配置与真实聊天仍需执行和验收。本轮只新增此排查记录，未修改业务、分发、宿主或治理代码。
