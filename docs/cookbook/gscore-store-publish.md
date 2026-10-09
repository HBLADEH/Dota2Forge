# GsCore 公开发行执行记录

2026-10-06，用户授权按上架核查顺序执行。已公开[分发仓库](https://github.com/HBLADEH/Dota2UID)及[0.1.0a3运行包](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a3)，完成隔离SDK安装与生命周期验收，提交[商店索引PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)。PR目标vp，仅新增Dota2UID条目和tool_plugins分类，原42个插件不变；目前OPEN，待维护者审核，尚未上架。

2026-10-08另行授权的[a6随包发行与部署](../../.agents/artifacts/dota2uid-bundled-release-v1/README.md)已完成；PR #40的installMsg与说明同步新安装/状态恢复入口，其他索引元数据不变，仍待审核。以下章节保留a3当轮的历史验证与边界，a6使用[随包指南](gscore-bundled-install.md)。

## 公开分发与安装

独立仓库只维护生成结果，业务仍由主仓共享Core/Renderer与独立适配器维护。默认main，根入口、guard、依赖清单、版本、空配置示例、README、许可、ICON与共享截图齐全；另附公开安装器、固定wheel摘要和本地INSTALL.md。没有提交实际配置、数据库、缓存，也未提交或改写主仓既有工作。

本机缺PyPI发布认证，采用已登录GitHub Releases；三个wheel、三个sdist及薄桥接ZIP共七个资产已匿名下载并匹配SHA256，12个公开根文件与候选字节一致。PyPI三个项目仍404，不声称已发布PyPI。前次a2资产/tag保留，发行说明添加兼容提醒。

首次公开a2安装发现Pillow冲突：SDK锁定fastembed0.7.4要求<12，原Renderer要求>=12.3，pip退出0不能证明环境兼容。修正版a3支持Pillow>=11.3,<13；安装器读取目标环境包元数据，保留其他宿主包对Pillow的有效约束，排除被替换的项目包，并以pip check作为成功条件。

当前GsCore87c06f1商店热重载仍只收集缺包、未在导入前执行依赖队列。本轮验证并提供明确的停机/公开安装器/冷启动流程，不改上游、不在import中联网、不弱化guard。原生pyproject保留包名和版本约束；步骤见[公开安装指南](gscore-public-install.md)。直接热安装仍不能代替这套流程，索引installMsg与PR说明均已注明。

## 隔离SDK验收

环境固定GsCore0.11.0/87c06f11ae10c12b3bb8e76b3c6f420c831282a8、Windows/Python3.13.2，位于D:/bot/gscore-store-validation-0.1.0a2；目录名保留创建时版本，最终运行包为a3。使用SDK锁文件恢复干净依赖，清除三个预装项目库后从公开仓库/Releases安装，Pillow保留11.3，pip check通过。未复制生产配置、数据或素材，SDK源码与函数未改。

实际执行SDK插件发现/导入、冷启动hook、原生reload、Trigger解析、SV权限、Bot PNG编码、ASGI管理接口拒绝未认证请求及原生卸载。首次空Token为awaiting_config且没有客户端/任务；填写合成Token后停用/重载ready。菜单、绑定、玩家、两页战绩、列表序号单局、主宰出装均产生有效PNG；文字回复与上游超时失败可区分。调度开启时仅注册一次，停用/关闭移除任务并关闭全部客户端。

公开a2→a3升级复现并修复Pillow冲突；新进程冷启动恢复绑定。SDK原生卸载只删除发现目录，随后新进程不再发现插件。配置、绑定和订阅库三个SHA256在升级、重启、卸载前后完全相同，[脱敏证据](../../.agents/artifacts/gscore-store-release-v1/README.md)。

上述为隔离SDK组件与生命周期验收，未启动HTTP/WS监听服务；Provider响应和出站传输分别使用合成HTTP fixture与内存帧采集器，无真实API或QQ消息。用户已选择QQ新命令后续自测，本轮保持AstrBot独立插件启用、GsCore桥接关闭。共享截图仍来自此前AstrBot实机，不替代GsCore递送证明。

## 本地检查与接续

统一离线入口退出0：1398测试通过，Ruff格式/lint、mypy72源文件及两组覆盖率门槛均通过；Pillow11.3下Renderer与双端消费者另424项通过。四包离线构建与双端无SDK分发隔离安装通过。完整证据与[交付任务](../../.agents/tasks/done/2026-10-06-gscore-store-release.md)对应。

维护者合并、真实商店界面安装、QQ新命令、订阅真实推送及Linux/其他SDK版本仍未验收。订阅默认关闭；英雄攻略、AI Tool、IMP与Deploy尚未实现。生产实例仍为此前a2，本轮未部署a3到生产或切换路由。
