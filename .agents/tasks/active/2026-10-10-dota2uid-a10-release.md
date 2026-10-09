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
主仓PR [#12](https://github.com/HBLADEH/Dota2Forge/pull/12)，source branch commit `779b92d4ca06b6ed5664812d46d6922a78dda9b8`；Python3.12/3.13各两次CI均通过，等待维护者评审。独立分发PR [#4](https://github.com/HBLADEH/Dota2UID/pull/4)，commit `eb02ca3b49c1c16dbf8758d48e688ea311c83d94`，以该主仓source SHA固定生成，等待主仓审查后再合并。

发行候选 `dist/plugin-distributions/a10-release-v1` 通过双端 SDK-free smoke。9个发布载荷及校验清单已暂存于忽略目录 `.tmp/a10-release-assets-v1`；manifest暂记两个PR head SHA，正式Release前必须改为实际main merge SHA并重算SHA256。GitHub `v0.1.0a10` Release尚不存在，没有公开上传任何资产。

统一门禁完整检查2009 passed/456.61s；scripts/Core/Assets覆盖率94/93/92。最后增补58个适配器运行时/桥接/send断言均通过；该选择性pytest因全仓覆盖率26%触发项目80%门槛退出1。双端最终本地候选smoke、真实SDK隔离原生热切换、Ruff/mypy和治理检查通过。Linux/Docker及真实QQ未验证。

## 阻塞与下一步
主仓scripts维护者评审是进入main和公开Release的门槛。PR #12与#4目前均OPEN/CLEAN、无reviewDecision；主仓CI通过。待维护者审查并按依赖顺序合并主仓与分发PR后，更新release-assets.json/SHA256SUMS为两个main merge SHA，匿名核验11个Release载荷，创建prerelease `v0.1.0a10` 并上传资产；商店索引PR #40仍独立待审，本任务不改索引或生产宿主。
