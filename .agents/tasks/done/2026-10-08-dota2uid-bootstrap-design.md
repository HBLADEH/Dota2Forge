# Dota2UID 聊天安装核心设计

Status: done

## 目标
设计 URL 安装后可用的单条管理指令，用于取得并部署匹配项目运行库；消除核心缺失时指令入口也无法加载的循环依赖。交付可评审提案，不把方案描述为现有功能。

## 非目标
本轮不实现、发布或部署，不改变治理门禁，不自动重启整台宿主，不在运行中替换宿主共享第三方依赖，不修改绑定与业务存储。

## 验收
- 明确 bootstrap 与业务入口的依赖边界、权限和命令行为。
- 明确固定版本/摘要、下载/安装、冷启动、失败和重复执行语义。
- 比较宿主环境安装与插件私有运行库目录，列出兼容限制。
- 列出源码修改范围、离线测试及真实宿主验收要求。

## 影响模块与决策
[入口模板](../../../adapters/Dota2UID/src/Dota2UID/host_entry.py.template)、[版本guard](../../../scripts/plugin_bootstrap.py)、[发行生成器](../../../scripts/build_plugin_distributions.py)、[安装器](../../../scripts/gscore_public_runtime.py)、[分发契约](../../../docs/subsystems/plugin-distribution.md)。遵守[已有冷启动决策](../../notes/implemented/2026-10-06-gscore-public-release.md)，设计见[随包bootstrap提案](../../notes/proposed/2026-10-08-dota2uid-bundled-bootstrap.md)。

## 验证证据
已保留全部已有工作区修改。当前生成器在入口最前执行guard；缺包直接抛异常，管理和业务指令均未注册。现有安装器写宿主环境，要求宿主停止。本轮完成子代理只读设计复核，未运行下载、pip安装或宿主操作。

用户追加尽量不改GsCore、允许寻找其他方案。已比较宿主pip、私有目录下载、随包运行库、上游/PyPI及独立worker；推荐随分发携带匹配项目wheel，在数据目录准备不可变运行库快照，管理入口先注册，恢复命令固定来源/hash并严格主人权限。根第三方依赖与本项目依赖声明分离；宿主第三方冲突明确拒绝，不在运行中替换DLL或清空模块缓存。

本地候选四个wheel均py3-none-any，合计13,841,202 bytes，主要为Renderer字体；最终商店产物体积未测。当前a4公开三组件与a5候选四组件的范围在提案中区分。

新增提案/任务通过check_repository(ROOT)文档、链接、预算、架构与生成漂移复核。本轮仅文档变更；上一排查轮统一离线1608项通过后源码未改，未重复全套测试。

## 阻塞与下一步
设计交付完成；实施仍需修改生成器、无核心bootstrap、业务生命周期注册与私有包加载，完成离线及实际GsCore Windows/Linux/Docker验证，并另行发行。本任务done只表示设计完成，提案仍proposed；安装指令尚未实现、未发布、未部署。
