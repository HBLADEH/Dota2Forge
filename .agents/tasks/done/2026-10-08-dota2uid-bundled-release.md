# Dota2UID a6 随包发行与部署

Status: done

## 目标
用户授权整理发布部署：将[已实现随包方案](../done/2026-10-08-dota2uid-bundled-bootstrap.md)发布到 HBLADEH/Dota2UID，并在确认的现行 GsCore 实例备份、部署及验证；不修改 GsCore 原逻辑。

## 非目标
不发布 AstrBot a8，不改聊天路由、凭据、身份或订阅归属，不发送真实消息，不覆盖旧发行资产，不合并需维护者评审的治理变更。

## 验收
- [x] 匹配四 wheel、许可证、分发清单与摘要，来源提交可审查；旧 a4 资产保留。
- [x] 分发 main 与 a6 Release 一致，匿名下载、缺 wheel 的真实公开恢复与冷启动验证。
- [x] 确认现行宿主目标；停用/停止、专用备份、部署、冷启动与数据/素材保留证据。
- [x] 管理状态及业务 ready/awaiting_config、客户端关闭与权限边界明确；真实 QQ 验收不冒充完成。
- [x] 源码/文档/任务整理与必要检查，公开链接和当前部署事实同步。

## 决策与范围
[生成器](../../../scripts/build_plugin_distributions.py)、[安装契约](../../../docs/subsystems/gscore-bundled-runtime.md)。共享 Core/Renderer a4 wheel 与旧发行逐字节相同，Assets a1 与 Dota2UID a6 首次公开；恢复 URL 固定 v0.1.0a6，四 wheel 均须在此 Release 提供。保留全局旧项目包，冷进程只加载匹配私有模块。

## 开工证据
已保留大量既有 workspace 修改，统一检查1740项已通过。GitHub已登录发布账号，Dota2UID main仍a4，a6未存在。原本机宿主 D:/bot/gsuid_core 已停止；8765由SSH转发监听，不能当作本机宿主，部署目标正在只读核查并向用户询问。

## 验证与交付
已公开a6，main/tag db123704，源码f585ed3、[PR #7](https://github.com/HBLADEH/Dota2Forge/pull/7)保留评审。17文件与11资产匿名验证一致，真实缺wheel管理恢复、Windows SDK原生URL+tag安装与冷启动通过；SDK源码/Pillow原生文件未变。

商店索引PR #40同步a6安装提示，单字段深比较确保其它插件/索引元数据不变；申请仍OPEN，未合并。

现行Linux/Docker GsCore SDK7f1bee79/Python3.12.12已私有备份并冷启动a6，17分发与91私有文件摘要一致，全局四项目包仍缺省；源树与HTTPX/Pillow不变。原UID数据不存在，新配置Token为空，启动awaiting_config、匿名管理401。首轮SSH替换因属主权限失败并恢复旧实例，改用同镜像断网维护进程完成专用目录切换和属主保留；未改其它容器/插件/路由/凭据或发送消息。

统一禁网1766 passed/265.77s，Ruff351/mypy83，总覆盖92.99%，scripts94/Core93/Assets92；Linux CI3.12/3.13通过，五包/双端smoke通过。门禁发现的Linux锁类型和Windows路径竞争均有修复与确定性证据，未放宽断言。[完整证据](../../artifacts/dota2uid-bundled-release-v1/README.md)。

## 接续
用户在现行服务器配置STRATZ Token后停用/重新加载，并验收QQ新指令；已登录管理API、其它SDK与跨schema回退待验证。商店及治理维护者审核继续等待，不以本任务done代表这些外部审核完成。
