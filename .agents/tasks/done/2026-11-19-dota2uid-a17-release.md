# Dota2UID a17 GitHub 预发行

Status: done

## 目标
按 2026-11-19 用户授权发布 Dota2UID a17，更新独立分发仓库 main，供用户在 GsCore 测试热更新。

## 非目标
不发布 AstrBot、PyPI 或商店索引，不操作宿主、配置、数据库或真实消息；不带入原工作区独立的 AstrBot 更新改动。

## 验收
- [x] 确认目标 release/tag 未占用，原 Dota2UID main 为 a16。
- [x] 独立的源变更经 PR 和 Linux Python 3.12／3.13 CI 验证。
- [x] 分发仓库 main 已同步，文件树与生成包一致。
- [x] 发行 ZIP 与分发 main 字节一致，复用原 Core 轮包与源码包；固定 tag，校验全部附件并公开为预发行。

## 影响模块与决策
[本地候选](../done/2026-11-19-dota2uid-pillow13.md)、[兼容决策](../../notes/implemented/2026-11-19-dota2uid-pillow13.md)、[随包指南](../../../docs/cookbook/gscore-bundled-install.md)。

## 验证证据
分发基线 main 为 `8cfcfce5630f14135b0362d337e7dfd417b4a024`，公开 a16 的 Core a9 wheel/sdist 摘要已从 Release API 核对。候选前序隔离验证见本地任务。

[源码 PR #26](https://github.com/HBLADEH/Dota2Forge/pull/26) 通过 push 和 PR 的四项 Linux Python 3.12／3.13 CI；固定源码 `986e68090daa7cd17096ad76afa5feff573526ee`，合并为 `4091673dd0273f5d55a7f261fb0c6e0419275278`。发布工作树统一离线 2155 项通过，总覆盖 91.14%，Ruff、mypy 和各独立覆盖门槛通过。真实 Pillow 13.0.0 的双端 SDK-free 分发 smoke 通过。

[分发 PR #8](https://github.com/HBLADEH/Dota2UID/pull/8) 合并至 `f9f1cef2c31140130212890f0b0dabed7e13320c`。25 个生成文件已逐一核对，合并后的 Git tree 与候选一致，归档内部与四个随包 wheel 的 SHA-256 校验通过。

[预发行 v0.1.0a17](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a17) 于 2026-11-19 12:39:36（北京时间）公开；tag 与分发 main 同提交。草稿的 11 个附件验证大小和 SHA-256 后公开，11 个公开附件匿名下载并匹配；ZIP SHA-256 为 `6987a8f6ceb75779f2bbd05d91dba5ecb0d845346d4000c88f59ed25875b9460`。a16 ZIP 摘要未变；未发布 AstrBot a15。原工作区改动保留。

## 阻塞与下一步
目标 Linux GsCore 的热更新和真实查询由用户验收：更新后用 `do核心状态` 查运行版 a17 与 `ready`，再查一条只读业务命令。若提示重启，再走维护窗口冷启动。本次未接触目标宿主。
