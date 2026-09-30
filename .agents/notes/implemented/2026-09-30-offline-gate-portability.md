# Windows 离线检查与独立 Core 覆盖率

Category: bug-fix
Related task: [Core 最小业务闭环](../../tasks/done/2026-09-30-core-mvp.md)
Related code: [检查器](../../../scripts/check_governance.py)
Related docs: [开发指南](../../../docs/cookbook/development.md)

## Problem
在 Windows 首次运行统一检查，workspace Path 被转为反斜杠字符串，无法匹配 policy 的正斜杠路径；53 个原测试中 30 个因此失败。wheel smoke 写死 bin/python，Path 排序在双平台的大小写规则不同；子进程裸 python 还可能解析到虚拟环境外。加入业务后，单一聚合覆盖率可能用治理工具的高覆盖率掩盖 Core 缺口。

## Decision
仓库路径比较与包排序使用 as_posix()，保留原路径覆盖及禁止依赖检查；wheel 按 sys.platform 选择 Scripts/python.exe 或 bin/python。检查命令中的 python 解析为当前 sys.executable。包参考生成器只陈述包元数据并链接架构，避免把已加入业务的 Core 写成骨架。

pytest 同时测量 scripts 和 dota2forge_core，并保留原聚合 80% 门槛。在 policy 的命令尾部增加两组 coverage report，各自以 80% 失败退出；无数据也失败，不删减原门禁。该 policy/治理脚本变更仍需维护者评审，本地通过不代表托管审批已生效。

## Alternatives considered
- 仅依赖 Linux CI：无法让当前 Windows 工作区按文档验证，修正路径语义而不跳过检查。
- 只增加 Core 到聚合覆盖率：不能保证两部分分别达到目标，增加独立门槛。
- 用手动覆盖率命令作为门禁：容易漏执行，放入统一检查入口读取的 policy。

## Consequences
检查顺序在 pytest 后追加两个只读报告，缺依赖、无数据和不足门槛均继续按非零失败。policy schema、预算、网络禁用与宿主依赖禁令均未放宽；不修改 CI 工作流。

## Verification
既有治理正反例在 Windows 重新运行；增加双平台解释器路径测试与高/低/无数据覆盖率反例。最终结果见关联任务。
