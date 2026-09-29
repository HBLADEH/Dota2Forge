# M0：Dota2Forge 工程初始化

Status: done

## 目标
统一品牌，建立 monorepo、包骨架、治理规则与真实可执行的离线检查。

## 非目标
Dota 2 业务、数据源请求、宿主命令、图片战报、订阅与部署。

## 验收
- 三个包可构建和独立导入，Core 无宿主 SDK。
- Ruff、mypy、pytest、治理门禁和生成漂移检查通过。
- 治理正反例覆盖超限、非法依赖、缺少 note 与生成漂移。
- CI、文档、许可证与可接续任务齐备，未生效控制如实记录。

## 影响模块与决策
全仓工程底座；[初始决策](../../notes/implemented/2026-09-30-workspace-foundation.md)。

## 验证证据
- 2026-09-30，macOS / Python 3.12.3：`uv sync --locked --all-packages` 与 `uv lock --check` 成功。
- `uv run --locked python scripts/check_governance.py --all` 通过：治理、Ruff 格式/lint、mypy（7 个源文件）、pytest（53 passed）。治理工具覆盖率 97.71%，门槛 80%。
- `uv build --all-packages` 生成三个 wheel 和三个 sdist；wheel 从 sdist 构建。
- `uv run --locked python scripts/smoke_wheels.py` 通过：三个包分别在临时环境使用本地 wheel 安装与隔离导入，无宿主 SDK。
- 反例覆盖非法静态/动态 import、依赖声明、文档预算、断链、缺失 note、生成漂移、未知 policy 字段及版本、缺失/失败命令。
- 临时 Git 仓库测试验证 merge-base、已提交、暂存、未暂存、删除、重命名与未跟踪文件的影响范围。
- 本地 Git 已初始化 main，pre-commit 钩子已安装；M0 初始提交为 `2db972b`。
- 按用户授权创建 MIT 公开仓库 [HBLADEH/Dota2Forge](https://github.com/HBLADEH/Dota2Forge)，推送 main 并设置 origin/main 跟踪；远程初始提交 SHA 与本地一致。
- [首次 GitHub CI](https://github.com/HBLADEH/Dota2Forge/actions/runs/36615343368) 通过 Python 3.12 / 3.13 检查、构建与独立 wheel 安装验证；真实 API、插件安装及生命周期联调未验证。

## 阻塞与下一步
MIT 已获用户选择，公开仓库与在线 CI 已落实；分支保护尚未配置。
用户要求本版本仅整理提交，后续功能暂不开始。[Core 任务](../active/2026-09-30-core-mvp.md) 保持 planned。
