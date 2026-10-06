# Git 提交使用公开别名与隐私邮箱

Category: security
Related task: [隐私修正](../../tasks/done/2026-10-06-git-identity-privacy.md)
Related code: [项目包配置](../../../pyproject.toml)
Related docs: [开发指南](../../../docs/cookbook/development.md)

## Problem
用户要求修正此前提交暴露的个人身份。仅改本机Git配置不会改变公开历史，仅加mailmap也不能清除原始提交元数据。

## Decision
使用HBLADEH与GitHub提供的账号隐私邮箱，针对确认属于本人的旧身份改写author/committer/tagger；保留他人身份、时间、提交信息和文件树。先建立本地bundle和私有映射，逐条核对树与消息不变，再用精确旧ref值作为force-with-lease条件并原子推送。

范围为本人控制的Dota2Forge、Dota2UID、AstrBot分发和GenshinUID-docs fork。无命中仓库无需改写；fork只处理自己的商店PR提交范围，不重写上游分支。改写导致提交SHA和后代SHA变化，受影响旧签名不能继续验证；标签引用同步，现有二进制发行资产不重新上传。

全局与相关本地检出配置使用公开别名/隐私邮箱，避免再次暴露。审计旧身份、邮箱与恢复对象仅留在本机忽略目录，公开记录不重复这些值。历史文档中的SHA仍代表原执行快照，不篡改为当时不存在的新SHA。

## Alternatives considered
- 仅修改Git配置：只保护后续提交，不能修复已公开记录。
- 添加mailmap：部分界面可能显示别名，但原始对象仍含旧身份，不能满足本次修正。
- 删除仓库重建：会破坏PR/发行与协作关系，不采用。

## Consequences
其他已有克隆须先保留本地修改再同步新历史。GitHub只读PR refs、旧SHA对象缓存和第三方克隆可能保留原身份，强推不能承诺彻底擦除，必要时由用户联系GitHub Support。本次未修改代码行为或生产部署。

## Verification
以Git对象级树/消息比对、分支标签远端回读、PR关联及发行资产摘要验证；无需重跑业务测试，文档治理单独检查。完成状态见关联任务。
