# 本地开发与离线验证

要求 Python 3.12+、uv 和 Git。先在仓库根目录安装锁定依赖：

```sh
uv sync --locked --all-packages
uv run --locked python scripts/check_governance.py --all
```

统一入口验证治理规则，然后依次执行 Ruff 格式、Ruff lint、mypy、pytest，以及治理工具、Core 和 Assets 各自的覆盖率报告。任一命令缺失或失败均返回非零；三组语句与分支综合覆盖率须分别至少 80%，无覆盖数据同样失败。测试使用 pytest-socket 禁网；Core 流程与异步循环测试说明见 [离线闭环](core-offline.md)。

已有提交时可以根据目标分支计算变更范围：

```sh
uv run --locked python scripts/check_governance.py --base main
```

该模式读取 merge-base 到当前工作区的完整差异，包含暂存、未暂存、删除和未跟踪文件；重命名作为删除与新增处理。仍执行完整检查，不缩减测试。无有效 Git 基线时明确失败，初始化使用 `--all`。

更新包配置后重建参考资料与锁文件，再验证：

```sh
uv lock
uv run --locked python scripts/generate_reference.py
uv run --locked python scripts/check_governance.py --all
```

构建五个包并检查 wheel 在独立环境中的安装和导入：

```sh
uv build --all-packages
uv run --locked python scripts/smoke_wheels.py
```

安装本地提交钩子（需已初始化 Git）：

```sh
uv run --locked pre-commit install
```

`.env.example` 是本机联调配置模板；复制为被忽略的 .env 后，仅由显式 [STRATZ 联调命令](stratz.md) 经 uv 注入环境。普通检查和 Core 导入不读取它；不要填入密钥后提交模板。
CI 配置见 [workflow](../../.github/workflows/ci.yml)，托管保护配置见 [治理契约](../subsystems/governance.md)。
