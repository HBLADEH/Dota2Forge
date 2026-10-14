# 2026-10-15 代码推送与 Dota2UID 测试分支

用户授权“先推送代码，我自己测试一下，AstrBot先不发版”。本轮停止本机私聊测试；没有安装插件、修改宿主配置、调用真实模型或发送平台消息。

## 提交与产物

- 主仓实现：`372b0bb4f0b48ce0167178f10ea0e6542e62d25e`，分支 [codex/stratz-features](https://github.com/HBLADEH/Dota2Forge/tree/codex/stratz-features)。包含共享 Core/Renderer、两端适配器源码、测试、文档与脱敏证据。
- GsCore 测试分发：`d1f1a2bea9fc55146a83b8532a52b2749901503a`，分支 [codex/stratz-features](https://github.com/HBLADEH/Dota2UID/tree/codex/stratz-features)。Core/Renderer a8、UID a15、Assets a1 四份随包 wheel，源码链接固定上述实现 SHA。
- 固定 SHA 的本地产物：`dist/plugin-distributions/stratz-push-20261015/`。生成器同时生成两个候选用于既有契约验证，但只同步/推送 Dota2UID 分发仓库，AstrBot 分发仓库未修改。

两个 main 保持不变：主仓 `0d277b0`，Dota2UID `85b878e`。没有创建 Release/标签、提交 Cloud/商店、合并主分支或发送 PR/Issue 评论。两个开工前已有商店历史任务未暂存、未提交。

## 验证

已有实现统一检查 exit 0：2101 项禁网测试、91.03% 聚合覆盖，Ruff/mypy 与独立覆盖门槛通过，见 [实施证据](../stratz-features-v1/README.md)。本轮运行源码未变，仅更新任务与交付记录；提交前治理/格式/lint/空白与凭据检查通过。

固定 SHA 的生成和双端 SDK-free 隔离消费 exit 0：[build.log](build.log)、[smoke.log](smoke.log)。[提交字节检查](committed-bytes.log)确认 Dota2UID 的 25 个提交文件与候选逐字节一致，4 个 wheel 的提交字节 SHA256 匹配运行清单。Git push 成功并通过远端分支 SHA 复核；CI 状态单独查看，不将本地结果冒称远端通过。

## 自行安装测试

在 GsCore 的 `gsuid_core/plugins/` 中首次安装：

```sh
git clone --branch codex/stratz-features https://github.com/HBLADEH/Dota2UID.git Dota2UID
```

如果已安装该仓库且工作树没有自行改动，可 fetch 后切到该分支；已有本地改动先保留。按 [GsCore 随包安装](https://github.com/HBLADEH/Dota2Forge/blob/372b0bb4f0b48ce0167178f10ea0e6542e62d25e/docs/cookbook/gscore-bundled-install.md) 维护原 Token/namespace，确认当前运行版本后重载，首次/旧协议升级冷启动。候选未创建公开 Release，损坏/缺失 wheel 的下载恢复地址尚不可用；完整随包 wheel 为正常路径。

先测 `do核心状态`、`do菜单`，再测 `do强势`、`do攻略 斧王 3号位 详细`、`do复盘 <比赛ID> [英雄]` 及五轮追问。真实模型召回、历史连续性和平台图片递送仍待用户自测反馈；上游攻略统计位置异常会明确降级，不作为推荐。
