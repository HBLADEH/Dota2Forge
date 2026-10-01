# GitHub 推送、主分支合并与工作区切换

Status: in_progress

## 目标
按用户授权推送现有实现，通过GitHub PR合并图片/历史详情与最新验收记录，并把本地切换到同步的main，后续直接在主分支操作。

## 非目标
不发布包、不修改分支保护/权限、不强推、不删除开发分支，不把本次Git交付当作AstrBot/IMP等后续功能完成。

## 验收
- [x] 核对干净工作区、GitHub账号权限、实际远端main和现有PR。
- [x] 同步远端main，保留已有提交和修改，无冲突。
- [x] 根据main运行统一离线门禁，确认提交范围与隐私/治理边界。
- [ ] 推送开发分支，创建或更新PR，并挂接到当前聊天。
- [ ] 等待Python3.12/3.13 CI通过，以核对的分支HEAD合并到main。
- [ ] 切换本地main，确认与origin/main同步、工作区干净，并推送交付记录。

## 影响模块与决策
[图片任务](2026-10-01-image-interaction.md)、[历史详情](2026-10-01-historical-match-detail.md)、[宿主验收](../done/2026-10-02-gscore-image-lifecycle.md)、[治理边界](../../../docs/subsystems/governance.md)。

## 验证证据
2026-10-02用户明确授权使用gh整理提交推送、合入主分支并在主分支继续。当前GitHub账号具有仓库ADMIN权限；已有PR#1将STRATZ/Dota2UID基础闭环合入远端main d7452c5。余下56622f8、ae0067f、a19603f分别记录图片/详情规划、实现和本机恢复/验收。

原工作区干净。git fetch后将origin/main合入开发分支，无冲突且无内容变化。当前插件提供PR CI诊断能力；写操作使用已登录gh CLI。PR描述需清楚列出shared_paths治理/工作流扩展与保留的独立80%门槛，便于用户维护者审阅。

uv run --locked python scripts/check_governance.py --base origin/main通过：813项禁网测试、Ruff、mypy36源文件、治理与两组独立80%门槛；综合96.27%。差异未包含.env、SQLite或原始聊天；OFL字体/合成样图和脱敏验收摘要随功能入库。

## 阻塞与下一步
执行main基线门禁，推送/创建PR，检查两版本CI，再按用户授权合并并切回main；不再次索取已经给出的合并许可。
