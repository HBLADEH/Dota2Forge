# Dota2UID a6 随包发行与部署边界

Category: operations
Related task: [发行部署](../../tasks/active/2026-10-08-dota2uid-bundled-release.md)
Related code: [生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [安装指南](../../../docs/cookbook/gscore-bundled-install.md)

## Problem
用户授权把随包实现整理发布并部署。恢复地址固定在a6 Release，单独更新仓库而不提供四个匹配wheel会使缺包恢复失败。工作区同时包含已实现素材服务与治理扩展，不能为发布跳过维护者审查。

## Decision
源码提交到独立分支并创建审查PR，不自动合并治理变更。生成器支持完整源码SHA，固定分发中的源码文档链接，默认main与旧消费者保持原行为。分发先推送发布分支，完整上传资产并公开预发行，再推进main；旧a4资产保留，Core/Renderer复用已审查的相同字节。

部署使用经核对的现行GsCore实例；先停止宿主并备份专用插件和数据，再部署与发行清单一致的文件、完整冷启动。配置、数据库、素材、全局项目包及GsCore源码均保留。只读验证状态和模块来源，不发送真实聊天或改变订阅归属。

## Alternatives considered
直接合并源码main会绕过治理评审。先更新分发main再慢慢补Release会造成恢复下载窗口，选择资产完整可用后再推进main。只发布不核查实例无法完成用户部署目标；本机旧宿主已停止，监听端口属于SSH，须确认远端目标。

## Consequences
源码PR待维护者审查期间，公开文档固定到可访问的源提交。外部资产可验证不代表商店已收录，也不代表QQ新命令已验收；实际部署和未验证项分开记录。跨schema回退须恢复兼容备份。

## Verification
完整结果记录于[证据目录](../../artifacts/dota2uid-bundled-release-v1/README.md)与关联任务；源码SHA参数已通过默认结果一致、链接固定和非法参数拒绝测试。发布与部署结果以实际操作证据为准。
