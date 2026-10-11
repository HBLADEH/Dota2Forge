# GsCore 订阅短命令使用匹配边界

Category: bug-fix
Related task: [修复任务](../../tasks/done/2026-10-11-subscription-command-prefix.md)
Related code: [订阅入口定义](../../../adapters/Dota2UID/src/Dota2UID/subscriptions.py)、[薄桥接](../../../adapters/Dota2UID/src/Dota2UID/host_entry.py.template)、[随包业务桥接](../../../adapters/Dota2UID/src/Dota2UID/bundled_business_entry.py.template)
Related docs: [订阅步骤](../../../docs/cookbook/subscriptions.md)

## Problem
有效玩家订阅被报告为参数错误。GsCore command trigger按前缀匹配，`do订阅`与玩家／比赛／列表命令都命中；block使先命中的短命令吞掉后续入口，将“玩家”留在参数中。原桥接测试直接按完整关键字查表，未覆盖原始文本匹配。

## Decision
仅将短命令改为有边界的regex trigger：命令结束或空白后才允许参数。命名捕获完整参数传给原控制器。两种桥接共用定义，长命令保留command trigger；Core、权限、ID验证、订阅存储和推送语义不变。错误类型和多余参数仍由既有控制器拒绝。

## Alternatives considered
长命令先注册：旧线性遍历可能有效，但本机SDK trie固定先收集短前缀，反转顺序仍失败。重新解析被截断参数：会把显式错误语法“do订阅 玩家”默默接受。修改宿主索引：影响全部插件，超出适配器修复范围。

## Consequences
桥接注册从一个短command改为一个regex，管理owner仍持有同一业务SV；薄安装器与随包生成器均更新模板。Dota2UID版本升为a12，其他三个运行组件和AstrBot版本保持。真实宿主安装、聊天和推送仍需另行验收。

## Verification
新增原始文本回归修复前三个入口均复现同一报错，修复后三项通过，覆盖真实控制器和持久化列表、短语法、错误参数及群权限。读取本机Event/Trigger/TriggerIndex源码，在隔离模块注册表中禁网执行，复现原问题及调序无效，九种修复路由通过；[证据](../../artifacts/subscription-command-prefix-v1/README.md)。完整检查与发行结果记入任务。
