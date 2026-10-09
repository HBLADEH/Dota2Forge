# 自动素材下载设计

Status: done

## 目标
回答现状并交付首次自动准备、管理员补下载/更新及失败恢复的可实施设计，覆盖AstrBot和Dota2UID。

## 非目标
本轮不实现运行代码、不升级服务器或发布商店版本；不改变现行Renderer纯本地读取及素材独立许可边界。

## 验收
设计区分现有脚本与未来自动功能；明确默认行为、自定义路径兼容、空Token场景、权限、来源、部分失败、缓存、发布/切换、取消及宿主关闭。检查两个已实现消费者和公开安装器/分发清单的影响，提出具体离线用例与实施顺序。

## 影响模块与决策
[设计提案](../../notes/proposed/2026-10-07-managed-illustration-download.md)、[现有下载器](../../../scripts/download_dota_assets.py)、[Renderer契约](../../../docs/subsystems/renderer.md)、[AstrBot Runtime](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/runtime.py)、[Dota2UID Runtime](../../../adapters/Dota2UID/src/Dota2UID/runtime.py)、[分发契约](../../../docs/subsystems/plugin-distribution.md)。

## 验证证据
已读四包架构、两端配置/生命周期及现有下载器。现状为显式脚本下载；无后台素材任务/管理命令。2026-10-07服务器镜像超时导致整包未发布，作为部分失败设计的具体依据。

已交付提案与独立实施任务：默认auto/manual/off、兼容自定义路径、空Token准备、管理员三个入口、固定来源/代理、有限重试/续作、partial快照、原子指针、整组渲染锁及关闭所有权。核对AstrBot的_dispatch_lock和Dota2UID的_send_lock，避免在查询锁外替换正在绘图的实例。

统一入口exit0：1537项禁网测试（179.44秒）、Ruff格式315文件/lint、mypy73源文件及工具96%/Core93%覆盖率通过。文档/提案没有改变现有运行代码；该结果不验证尚未实现的自动下载。[检查证据](../../artifacts/managed-illustration-download-design-v1/README.md)。

## 阻塞与下一步
设计完成；自动下载、管理命令、共享assets包均未实施/联调/发布。按[实施计划](../active/2026-10-07-managed-illustration-download.md)接续；未来新增共享包时治理配置按根规则维护者评审，当前不修改门禁或服务器。
