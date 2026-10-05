# 长装备名排版与 0.1.0a4 发布整理

Status: done

## 目标
修复出装/比赛卡长装备名拥挤，整理当前全部项目成果并提交，更新四包版本与 Dota2UID 发行；准备 AstrBot 独立公开分发，按用户选择发布。

## 非目标
不改变生产聊天路由或发送消息，不合并商店PR，不把离线/合成图当作宿主验收，不覆盖已有版本资产。

## 验收
- [x] 常用装备简称和自适应换行、足够留白；全名称表、长ID、手机预览验证。
- [x] 四包0.1.0a4元数据/锁/依赖一致，统一离线检查、构建及隔离安装通过。
- [x] 整理当前代码、文档与证据，检查敏感信息，提交到可评审分支并推送。
- [x] Dota2UID新发行及AstrBot发布准备/用户选择结果记录，公开资产可核对摘要。

## 影响模块与决策
[图片契约](../../../docs/subsystems/renderer.md)、[分发契约](../../../docs/subsystems/plugin-distribution.md)、双端README、分发生成器/运行安装器及测试；[本轮决策](../../notes/implemented/2026-10-06-a4-layout-and-astrbot-release.md)。

## 验证证据
统一离线入口1532测试通过（152.77秒），Ruff/mypy73文件及覆盖率门槛通过；最终元数据45项相关检查通过。全名称表两格宽无裁字，出装1674/三人比赛1706px；手机预览已检查。

四包构建/独立wheel导入、双端禁网安装/首配/重启保留绑定通过；两端全新环境通过公开安装器安装a4、pip check及PNG绘制。25个公开文件及14个发行资产匿名下载匹配摘要，AstrBot ZIP 1,921,901 bytes。代码已提交0622dd7并推送codex/a4-layout-release，后续验收文档提交8d77835；[主仓PR #4](https://github.com/HBLADEH/Dota2Forge/pull/4)供维护者评审，尚未合并。

[Dota2UID a4](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a4)分发提交eb03ae3；[AstrBot a4](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a4)分发提交8939503。Cloud已提交v0.1.0a4，显示Waiting/等待安全检查；[证据](../../artifacts/a4-layout-release-v1/README.md)记录公开摘要/安装/图片/隐私审查。旧资产与既有工作保留。

## 阻塞与下一步
已完成修复、提交、版本更新、两端预发行及授权的AstrBot申请。等待主仓PR/两端商店审核；未改生产实例。新版在线字段、真实聊天、Linux及订阅递送尚未验收，CI结果另由PR展示。
