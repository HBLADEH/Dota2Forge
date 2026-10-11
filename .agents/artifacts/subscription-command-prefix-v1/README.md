# Dota2UID 订阅入口修复证据

[任务](../../tasks/done/2026-10-11-subscription-command-prefix.md)、[决策](../../notes/implemented/2026-10-11-subscription-command-prefix.md)。

[隔离脚本](check_matcher.py)读取本机GsCore的Event、Trigger和TriggerIndex源码，仅使用临时模块注册表、合成消息与无行为回调。Bot与SV注册容器为桩，不是完整宿主或聊天联调；没有导入服务器、启动监听、查询Provider、读取配置／凭据或修改宿主源码。外部socket连接、DNS、UDP禁用；asyncio内部loopback提前创建。

2026-10-11用现有CPython3.13.2宿主解释器运行，记录见[路由与源码摘要](matcher-validation.json)。旧注册及倒序注册都先取得短命令并错误切出“玩家”参数；加边界后九种路由通过。三个源码文件摘要前后不变；本机trie实现与历史公开SDK基线有差异，证据只代表实际读取的字节。

普通测试不依赖SDK，模拟trie短前缀优先和block后，执行实际薄／随包桥接、Runtime与订阅控制器。修复前3项失败并复现用户报错，修复后3项通过。[统一禁网检查](offline-check.log)exit0，2013项通过；[五包构建](build.log)与[五包隔离安装／导入](wheel-smoke.log)通过。初次[lint失败](offline-first-lint-failure.log)为脚本循环变量命名，修复后完整门禁通过。Core、Renderer、Assets wheel摘要与已公开a11相同；公开发行证据另记。

源码[PR #15](https://github.com/HBLADEH/Dota2Forge/pull/15)已合并，固定head `2e4e56a4b2e8242938474f65d3084f7ba201c736`生成候选；[四项CI](source-ci.json)全通过。[分发生成](distribution-build.log)与[SDK-free分发smoke](distribution-smoke.log)通过，综合覆盖率92.51%，scripts／Core／Assets分别94／93／92%。

[v0.1.0a12 Release](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a12)已公开，分发main／tag均为`d66c12e80cedc7d3e9f131ce77f61866c2bd24f1`。[公开验证](Dota2UID-public-validation.json)确认18个根文件与候选相同、ZIP与仓库相同、11个附件完整匿名下载与SHA256通过。未覆盖旧附件，AstrBot仍为a10。

匿名Release API首轮返回403限流；改用gh读取同一个公开API，[元数据](release-api.json)不含凭据。验证器增加仅切换元数据读取来源的参数，版本、预发行标记、附件集合／大小／摘要断言保持；记录明确assets_anonymous=true，整轮anonymous=false，避免将带登录态的元数据读取算成匿名验证。codeload及全部附件下载均匿名。

生产宿主、凭据／配置／数据库均未改动，真实QQ命令和订阅推送未复测。
