# GsCore 上架前置条件复核

核查日期：2026-10-06。结论：Dota2UID 已具备本地发行候选，尚不具备可供普通用户直接从商店安装的全部条件。公开分发仓库、三个运行包取得和宿主热安装依赖执行仍有阻塞；README、图标及现有共享截图已准备好。

后续执行已公开a3分发/运行包并通过隔离SDK安装、升级与卸载，提交索引PR #40，待审核；最新状态见[执行记录](gscore-store-publish.md)。直接热安装限制和QQ未验收边界仍保留。下文为执行前核查时的历史证据。

## 已满足与阻塞

本次对象为 dist/plugin-distributions/0.1.0a2-shared-showcase-v1，GsCore ZIP 为1,915,995 bytes。输入/输出摘要匹配当前源码；四包离线重建与现有wheel摘要一致。证据见[核查记录](../../.agents/artifacts/gscore-store-readiness-v1/README.md)。

| 项目 | 结果与范围 |
| --- | --- |
| 根发现入口及清单 | 已有__init__.py、pyproject.toml、release.json和导入前版本检查；Python>=3.12，三个项目库锁定0.1.0a2 |
| 展示与配置 | README、MIT许可、主宰ICON、空配置示例和已审查出装截图齐全；无真实配置或数据库，GsCore说明标明截图来自AstrBot |
| 本地干净安装 | 两端独立Python3.12.9环境从本地wheel安装通过；无SDK、无网络，验证空Token待配置、配置后ready及绑定重启保留 |
| 公开仓库 | 目标HBLADEH/Dota2UID及main根入口/清单/ICON匿名访问均404，无法据此公开克隆或显示商店图标 |
| 项目运行包 | dota2forge-core、dota2forge-renderer、dota2uid的PyPI接口均404；目前清单锁定的0.1.0a2无法按该公开渠道取得 |
| 第三方依赖 | HTTPX0.28.1和Pillow12.3.0有符合清单约束的公开版本；不替代目标平台wheel安装验证 |
| 宿主热安装 | 固定GsCore提交87c06f1中，reload_plugin收集依赖后直接导入，未先执行安装队列；隔离复现被缺包guard拦住 |
| 实机部署 | 本机Windows/Python3.13.2已手动预装wheel并从0.1.0a1升级至0.1.0a2、冷启动ready、配置/数据/素材保留；仅证明该部署方式 |
| 商店与聊天验收 | 从公开源在无项目包的实际SDK宿主新装、更新、卸载/回退及当前do/MMR/出装聊天未验收；共享截图不提供这些证据 |
| 收录草稿 | gscore-index-entry.json字段与tool_plugins分类草稿已生成；官方运行索引42条中尚无Dota2UID，未提交PR |

公开状态来自当日匿名请求：[目标仓库](https://github.com/HBLADEH/Dota2UID)、[Core PyPI](https://pypi.org/pypi/dota2forge-core/json)、[Renderer PyPI](https://pypi.org/pypi/dota2forge-renderer/json)、[Dota2UID PyPI](https://pypi.org/pypi/dota2uid/json)。404表示当前未公开可达，不证明仓库不存在或包名可注册。PyPI是本项目现行分发方案，不是GsCore要求的唯一发布渠道。

## 热安装的额外兼容问题

[冷启动加载](https://github.com/Genshin-bots/gsuid_core/blob/87c06f11ae10c12b3bb8e76b3c6f420c831282a8/gsuid_core/server.py)在导入插件前执行flush_pending_installs；[热重载](https://github.com/Genshin-bots/gsuid_core/blob/87c06f11ae10c12b3bb8e76b3c6f420c831282a8/gsuid_core/utils/plugins_update/reload_plugin.py)没有这一执行步骤。商店克隆后调用热重载，因此即使公开依赖补齐，当前路径也不能保证首次安装成功。

隔离探针执行上述提交的真实依赖检查/队列执行/reload_plugin函数及当前候选guard，开启AutoInstallDep，初始缺三个项目库：依赖被收集，导入前未安装，guard拒绝；显式执行队列的对照通过。SDK注册表、路径组合及安装器效果为合成边界，禁网且未改真实宿主。这确认该版本的控制流问题，不能宣称完成了实机商店安装。未修改上游、弱化版本检查或改变发布策略。

## 收录路径与接续

[官方运行索引](https://docs.sayu-bot.com/plugin_list.json)与GenshinUID-docs的vp提交0b04c49字节一致；[已合并PR #39](https://github.com/Genshin-bots/GenshinUID-docs/pull/39/files)提供新增条目和分类的现行收录实例。没有据此推定完整官方审核清单、审核期限或一定获准；上述运行条件来自实际加载器与本项目验收要求。当前未收录是提交状态，不能用索引草稿当作已上架。

1. 固定拟公开版本，将生成的Dota2UID根目录同步到可公开克隆的独立仓库，确保默认分支、索引link和ICON地址一致。
2. 提供宿主安装器可取得的三个匹配运行包；沿用当前方案时发布并核实0.1.0a2及Python/依赖元数据。切换分发方案需另行决策和验证。
3. 处理并验证热安装依赖执行问题；若选择明确的冷启动安装流程，须在实际干净宿主验证并写清首次安装/重启操作，不能继续宣传直接热安装即可使用。
4. 在拟支持的实际GsCore/Python环境从公开源新装，完成配置、代表性文字/图片聊天及停用/更新/卸载的数据保留验收。扩展Linux或其他版本支持时补相应证据。
5. 完成运行前置条件后，向vp分支的docs/public/plugin_list.json提交新增条目和分类PR，由维护者决定收录。本次未发布包、推送仓库、提交PR或发送聊天。

不要求为本轮核查重拍现有共享出装截图；其余截图属于[展示接续](plugin-showcase.md)，不将未发现的截图数量规范或全部规划能力写成上架硬门槛。

本轮四包离线构建和双端无SDK干净安装通过；统一离线检查退出0，1377测试通过（168.20s）、治理工具96%/Core93%覆盖率，详见[核查任务](../../.agents/tasks/done/2026-10-06-gscore-store-readiness-audit.md)。这些结果不扩大实际宿主验收范围。
