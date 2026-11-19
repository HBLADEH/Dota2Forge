# Dota2UID a17 GitHub 预发行

Status: active

## 目标
按 2026-11-19 用户授权发布 Dota2UID a17，更新独立分发仓库 main，供用户在 GsCore 测试热更新。

## 非目标
不发布 AstrBot、PyPI 或商店索引，不操作宿主、配置、数据库或真实消息；不带入原工作区独立的 AstrBot 更新改动。

## 验收
- [x] 确认目标 release/tag 未占用，原 Dota2UID main 为 a16。
- [ ] 独立的源变更经 PR 和 Linux Python 3.12／3.13 CI 验证。
- [ ] 发行 ZIP 与分发 main 字节一致，复用原 Core 轮包与源码包；固定 tag，校验全部附件并公开为预发行。

## 影响模块与决策
[本地候选](../done/2026-11-19-dota2uid-pillow13.md)、[兼容决策](../../notes/implemented/2026-11-19-dota2uid-pillow13.md)、[随包指南](../../../docs/cookbook/gscore-bundled-install.md)。

## 验证证据
分发基线 main 为 `8cfcfce5630f14135b0362d337e7dfd417b4a024`，公开 a16 的 Core a9 wheel/sdist 摘要已从 Release API 核对。候选前序隔离验证见本地任务。

## 阻塞与下一步
源 CI 与发行校验完成后公开；目标 Linux GsCore、自动重载和真实查询由用户验收。
