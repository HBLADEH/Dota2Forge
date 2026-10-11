# Dota2UID 订阅入口修复证据

[任务](../../tasks/active/2026-10-11-subscription-command-prefix.md)、[决策](../../notes/implemented/2026-10-11-subscription-command-prefix.md)。

[隔离脚本](check_matcher.py)读取本机GsCore的Event、Trigger和TriggerIndex源码，仅使用临时模块注册表、合成消息与无行为回调。Bot与SV注册容器为桩，不是完整宿主或聊天联调；没有导入服务器、启动监听、查询Provider、读取配置／凭据或修改宿主源码。外部socket连接、DNS、UDP禁用；asyncio内部loopback提前创建。

2026-10-11用现有CPython3.13.2宿主解释器运行，记录见[路由与源码摘要](matcher-validation.json)。旧注册及倒序注册都先取得短命令并错误切出“玩家”参数；加边界后九种路由通过。三个源码文件摘要前后不变；本机trie实现与历史公开SDK基线有差异，证据只代表实际读取的字节。

普通测试不依赖SDK，模拟trie短前缀优先和block后，执行实际薄／随包桥接、Runtime与订阅控制器。修复前3项失败并复现用户报错，修复后3项通过。[统一禁网检查](offline-check.log)exit0，2013项通过；[五包构建](build.log)与[五包隔离安装／导入](wheel-smoke.log)通过。初次[lint失败](offline-first-lint-failure.log)为脚本循环变量命名，修复后完整门禁通过。Core、Renderer、Assets wheel摘要与已公开a11相同；公开发行证据另记。
