# GsCore 图片生命周期验收与部署恢复

Status: done

## 目标
恢复失效的本机 Dota2UID 部署，验证图片版本的管理员停用、重载、冷启动和资源关闭。

## 非目标
不修改 GsCore 核心、权限等级或凭据，不删除绑定数据，不将宿主成功等同 QQ 压缩或 AstrBot 验收。

## 验收
- [x] 从脱敏日志定位停用无回复的原因，核对已安装文件。
- [x] 保留配置/绑定库/发现入口指纹，恢复 Core、Renderer、Dota2UID 及 Pillow 缺失文件。
- [x] 在旧进程退出后安装锁定 Pillow 12.3.0，正常冷启动，恢复临时重启配置。
- [x] 验证 ready → stopped/client_closed=true → reload → ready，重复一次检查资源关闭与注册恢复。
- [x] 独立 PNG 生成、安装文件核对、配置和绑定库完整性通过；依赖约束按各包声明核对。
- [x] 用户复测 QQ 菜单、账号和直接 ID 详情均正常、图片可读；已同步 active 任务和事实文档。
- [x] 运行统一离线门禁并整理脱敏交付记录入本次提交。

## 影响模块与决策
[图片任务](../active/2026-10-01-image-interaction.md)、[历史详情](../active/2026-10-01-historical-match-detail.md)、[接入步骤](../../../docs/cookbook/dota2uid.md)、[宿主基线](../../../docs/subsystems/gscore-host.md)。

## 验证证据
2026-10-02 查阅本机日志：10-01 19:29:30 的重载清除3个生命周期Hook和2条路由后因MatchParseState导入失败中断；10-02 01:33:42/01:34:29 收到dota停用事件，user_pm=1，未命中pm=0管理处理。上轮失败安装另留下Dota2UID目录缺失和Pillow Python文件缺失。

三个本地wheel经无索引/无依赖安装恢复。匹配旧Pillow11.3.0 DLL后补回缺失文件；用户重新登录后正常重启，退出旧进程再安装锁定12.3.0。独立导入与780×1050菜单PNG通过；四包内容逐文件匹配wheel，配置/绑定库/发现入口指纹未变化，临时重启设置已还原。[证据](../../artifacts/gscore-image-lifecycle-v1/README.md)记录两轮stop/reload最终ready/image。

用户确认QQ菜单、账号和详情均正常、图片可读；Runtime日志另确认菜单/账号图片准备与发送完成。临时恢复页/脚本已删除。统一入口813项禁网测试、Ruff、mypy36源文件及治理通过；综合96.27%、Core约99%、scripts约97%，两组独立80%门槛通过。仅修改文档/证据，未改业务代码；宿主安装匹配现有已验证wheel，不重复构建。

## 阻塞与下一步
本任务完成，宿主最终ready/image。AstrBot平台接入、IMP/经济序列和治理维护者评审留在后续任务；多账号、长期运行和异常压缩未验证。失效旧钩子的进程退出不记作插件关闭成功。
