# Dota2UID a10 受控热切换发行准备

Status: in_progress

## 目标
将已验证的 Core a7 / Dota2UID a10 bundled 热切换候选送入维护者评审，并准备匹配的独立分发更新与公开Release资产，使用户可在审核合并后实测。

## 非目标
绕过主仓 scripts 维护者评审，操作生产宿主或真实聊天，改变 GsCore 商店索引 PR #40，或声称尚未完成的Linux/Docker联调通过。

## 验收
- 主仓候选分支/PR包含源码、生成参考、决策、任务和隔离证据；离线检查、构建、distribution smoke与提交SHA可追溯。
- 独立Dota2UID分发候选锁定主仓源码ref与a10/Core a7 wheel摘要；README明确首次旧版冷启动及后续兼容重载边界。
- 只有主仓合并/维护者审核后才发布独立main、tag与GitHub Release；索引未更改。
- 交付包含实际发布状态、安装步骤、SDK环境与生产/聊天未验证项。

## 影响模块与决策
[热切换实现决策](../../notes/implemented/2026-10-10-dota2uid-hot-update.md)、[验收证据](../../artifacts/dota2uid-hot-update-v1/README.md)、[发行指南](../../../docs/cookbook/plugin-release.md)、[Dota2UID分发仓库](https://github.com/HBLADEH/Dota2UID)。

## 验证证据
发行前全量统一门禁2009项通过（456.61s）；后续58项聚焦断言通过，但该部分pytest因覆盖率仅26%触发全仓80%门槛。v10 SDK-free分发smoke、公开SDK隔离原生热切换与401/403 API检查通过。公开发布/合并尚未执行。

## 阻塞与下一步
主仓 scripts 维护者评审是进入main和公开Release的门槛；先完成PR与分发PR的可审查候选，合并授权/审查后完成tag、Release资产和任务归档。
