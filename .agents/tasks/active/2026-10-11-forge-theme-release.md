# 双端远古锻炉主题发行

Status: in_progress

## 目标
按用户授权发布Dota2UID a11 bundled与AstrBot alpha.10，AstrBot根目录和发行说明包含更新日志，并提交Cloud新版本、核实日志显示。

## 非目标
不操作生产宿主、凭据／配置／数据库或真实聊天；不改GsCore索引PR #40；不覆盖既有Release资产或跳过检查。

## 验收
- 主仓主题源码、变更日志打包与证据提交可追溯，CI／离线检查及五包构建通过。
- 双端分发固定源码SHA、四个运行包版本与摘要，隔离安装和产物检查通过。
- 两个分发main／tag／公开预发行附件与候选一致，匿名下载验证。
- AstrBot CHANGELOG.md随根目录和ZIP发布，Cloud更新日志非空，新版本提交及审核状态真实记录。

## 影响模块与决策
[主题实施](../done/2026-10-11-forge-theme-implementation.md)、[更新日志打包决策](../../notes/implemented/2026-10-11-plugin-changelog.md)、[发行指南](../../../docs/cookbook/plugin-release.md)。

## 验证证据
用户明确授权发布两端并要求AstrBot补更新日志。保留两份已有商店任务与全部主题实施修改。主仓PR #12及Dota2UID PR #4均已合并，旧a10未公开；a11包含已审查受控热切换，旧a6–a9首次升级仍冷启动。开工时Cloud为alpha.7 Published，更新日志为空；已有登录态可用。

## 阻塞与下一步
主仓PR #13已合并，四个Python3.12／3.13 CI通过；源码SHA223967ba固定生成双端候选，SDK-free smoke通过。Dota2UID a11与AstrBot alpha.10的main／tag／Release已公开，两端各11个附件匿名下载和摘要通过；[发行证据](../../artifacts/forge-theme-release-v1/README.md)。更新日志已随AstrBot根目录、ZIP与Release说明发布。

Cloud提交已接收：更新操作后返回详情，再次解析显示现有插件当前alpha.10；公共页仍为alpha.7 Published及空更新日志，尚未确认新版上架与日志刷新。保留任务接续此项外部状态；不重复提交，不操作生产宿主或真实聊天。新主题功能与打包已完成。

含更新日志打包的统一离线检查2012项通过，聚合覆盖率92.49%，三组覆盖率均超过80%；分发专项89项通过。初次新增必需文件导致合成源码fixture缺失，补齐fixture后通过；文档预算首轮失败已压缩修复，未解除门禁。最终安装说明更新后另作治理复核和五包重建。

接续只核实Cloud alpha.10公开上架和更新日志显示；GitHub发行已完成，审核／缓存由平台处理，不把提交当审核通过。
