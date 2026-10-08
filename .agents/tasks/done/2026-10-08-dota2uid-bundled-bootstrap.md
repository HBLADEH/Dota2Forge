# Dota2UID 随包运行库与聊天恢复实施

Status: done

## 目标
按用户授权实现[随包bootstrap设计](../../notes/proposed/2026-10-08-dota2uid-bundled-bootstrap.md)：URL分发携带匹配项目wheel，核心缺失时仍可诊断和恢复，保持GsCore源码与全局项目包环境不变。

## 非目标
不发布或部署到生产、不发送真实消息、不自动重启宿主、不升级共享第三方DLL、不变更治理门禁；保留现有开发中修改及AstrBot原分发路径。

## 验收
- [x] 无Core管理入口、主人权限、Token等待、停用/关闭与业务注册幂等。
- [x] 固定wheel/摘要与安全解压、不可变快照、离线资源检查、文件锁/并发/取消、失败保留旧数据。
- [x] bundled生成器与SDK-free干净安装验证；宿主项目依赖不再全局pip，原模式/AstrBot兼容。
- [x] 统一离线检查、构建及实际GsCore隔离生命周期验证；真实宿主/平台未验证项明确记录。
- [x] 契约、指南、版本与note同步，未把候选写成已公开功能。

## 影响模块与决策
[发行生成器](../../../scripts/build_plugin_distributions.py)、[管理桥接](../../../adapters/Dota2UID/src/Dota2UID/bundled_host_entry.py.template)、[标准库后端](../../../scripts/gscore_bundled_runtime.py)、[bootstrap契约](../../../docs/subsystems/gscore-bundled-runtime.md)。保留旧薄入口/guard及AstrBot路径；平台生命周期只留在适配器。决策见[实施note](../../notes/implemented/2026-10-08-dota2uid-bundled-bootstrap.md)。

## 验证证据
2026-10-08用户授权实施。已检查dirty工作区并分配互不重叠的后端、桥接、生成器任务；未操作GsCore生产实例或发布仓库。

统一禁网入口通过：1740 passed / 245.13s，Ruff 346文件、mypy 83文件；总覆盖92.95%，scripts94%、Core93%、Assets92%。新增后端80、桥接35、bundle分发17项；五包构建、五个新venv wheel安装与双端SDK-free分发smoke通过。首次全套发现工作区仍装a5及两个固定版本夹具不同步，更新为a6并修夹具后重跑通过，未放宽断言或门禁。

Windows实际SDK0.11.0/87c06f11源码隔离副本、CPython3.13.2/Pillow11.3.0，五阶段验证权限/参数拒绝、Token等待、配置重载、live reload、幂等准备、管理员API、冷启动、关闭和原生卸载；绑定/配置保留，原SDK源码摘要不变。模拟相同wheel但清单变化验证旧进程拒绝新代际、冷启动恢复，不等同真实发行升级。修复非-B导入pyc与certifi补零误判。[完整证据](../../artifacts/dota2uid-bundled-bootstrap-v1/README.md)。

## 尚未验证与接续
源码候选a6未发布/部署，现有公开a4不会自动获得新命令。真实商店URL安装、Release恢复下载、QQ递送、跨schema回退及Linux/Docker实际SDK尚未验证；本机Docker daemon不可用。外部发行和生产操作需另有任务授权。候选为dist/plugin-distributions/a6-bundled-v4，尺寸与摘要见证据JSON。
