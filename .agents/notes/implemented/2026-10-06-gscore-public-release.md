# GsCore 公开发行与冷启动安装路径

Category: operations
Related task: [公开发行执行](../../tasks/done/2026-10-06-gscore-store-release.md)
Related code: [候选生成器](../../../scripts/build_plugin_distributions.py)、[版本guard](../../../scripts/plugin_bootstrap.py)
Related docs: [执行记录](../../../docs/cookbook/gscore-store-publish.md)

## Problem
用户已授权执行公开分发、安装验收与商店PR。候选本地通过，但三个项目包未公开，当前GsCore87c06f1商店热路径只收集依赖而不执行安装。预装wheel的生产成功不能证明普通用户新装成功。

首次公开a2安装暴露实际宿主冲突：fastembed0.7.4在Python3.13要求Pillow<12，Renderer要求>=12.3；pip返回0但记录冲突。因此不能以安装退出码单独宣称成功。

## Decision
已将原样审查的九文件候选公开至HBLADEH/Dota2UID的main，保持业务共享包、平台边界和guard，不向主仓提交其他既有工作。缺PyPI发布认证时，先用现有GitHub登录提供公开Releases wheel；未读取/输出其他凭据，PyPI仍待认证补充。

新增标准库运行包CLI，由同次三个wheel生成固定版本/SHA256清单。显式指定宿主Python，先检查版本并准备pip，以三个带hash的直接引用共同解析依赖。先退出宿主、运行CLI再冷启动；原生pyproject保留三个版本约束，不以URL空specifier替代版本比较，不在import中触发安装。根分发附本地INSTALL.md，避免用户操作依赖未同步主仓链接。

修正采用新版本0.1.0a3，保持已公开a2资产与tag不变。共享Renderer与AstrBot清单支持Pillow>=11.3,<13；两个消费者检查兼容下界。CLI读取目标pip的包元数据，保留其他宿主包对Pillow的当前有效版本约束，排除正在替换的三个项目包；无法安全解析则失败。安装后执行pip check，任何冲突均不报告成功。旧a2安装可通过匹配a3清单修复，不移除或升级宿主fastembed。

优先验证明确停机/冷启动的安装与升级流程。冷启动源码在导入前执行依赖队列，可避免热路径遗漏；使用独立、无生产配置数据的实际SDK环境，从公开源取得依赖后逐项验证。该路径已在固定Windows/GsCore0.11.0/Python3.13.2隔离SDK验证，不扩大其他宿主/平台范围，未修改GsCore上游。

用户已选择先隔离宿主，QQ命令后续自行测试，不改现有聊天路由。索引PR在其余前置条件完成后提交，并明确QQ新功能尚待用户验收；不会用合成SDK/WS或共享截图替代真实平台递送。

## Alternatives considered
- 修复并提交GsCore上游热依赖执行：可以恢复直接热安装，但上游接受时间不受本项目控制，共享库升级仍需要停机；可后续单独推进。
- 在插件import中自行联网pip安装：会绕过宿主依赖开关和生命周期，不采用。
- 直接把宿主pyproject依赖换成GitHub URL：specifier为空时已有旧包被视为满足，采用显式公共安装器与原版本约束，更新后仍冷启动。

## Consequences
公开入口是有限M0候选；自动安装、聊天递送和索引收录保持分列。公开安装与固定SDK组件生命周期已验证，决策转implemented；不会声称已上架、直接热安装成功或QQ递送通过。

## Verification
公开a3仓库12文件、Releases七资产均匿名下载匹配摘要。四包构建、双端无SDK隔离安装、Pillow11.3下双端消费者424测试、统一门禁1398测试/Ruff/mypy/两覆盖率门槛通过。实际SDK发现/冷加载/hook/重载、首次配置恢复、PNG编码、权限/失败、调度及关闭通过；公开a2→a3修复、冷加载绑定恢复、原生卸载及新进程不再发现通过，配置/两库摘要不变。SDK源码/函数未改，合成HTTP与出站采集，无监听服务或真实QQ。索引PR #40已提交并附加，待审核；[完整记录](../../../docs/cookbook/gscore-store-publish.md)。
