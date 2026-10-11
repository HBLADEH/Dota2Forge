# 双端说明与截图预发行

Category: operations
Related task: [发行任务](../../tasks/done/2026-10-12-plugin-readme-release.md)
Related code: [生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [发行指南](../../../docs/cookbook/plugin-release.md)

## Problem
双端 README、七张已审查截图和居中导航已经准备，用户进一步授权复核后分别发布。旧公开版本不能体现这些文档，AstrBot Cloud 还需要重新解析新版仓库。

## Decision
仅将适配器提升至 AstrBot 0.1.0a11（宿主 alpha.11）和 Dota2UID 0.1.0a13；Core a7、Renderer a6、Assets a1 不变。保持 M0 预发行标记和现有两端安装模式，发布新的 tag 与附件，不覆盖旧版。源码通过 PR/CI 后以固定 SHA 生成候选，图片保持审查后字节。

## Alternatives considered
只更新分发 main 不创建新版本，会使 ZIP、Cloud 版本和安装组件缺少对应记录；覆盖旧版附件会破坏既有固定摘要安装契约。因此采用独立新版本。

## Consequences
本次是说明与分发更新，不改变业务或数据格式。原 GsCore 图在两端注明真实来源，不算 AstrBot 聊天验收。主仓 README 的过时发行和 IMP/素材现状同步修正。用户授权涵盖本次 GitHub 发布和 Cloud 更新；不延伸到生产部署或消息发送。

## Verification
统一离线2013项、最终分发专项89项、源码四项CI及双端SDK-free smoke通过；两端main/tag/ZIP和每端11附件完整匿名核对通过。Cloud只提交一次，已接收并显示Reviewing；审核结果由平台处理，不能宣称已上架。具体证据见关联任务；实际宿主升级及主动订阅推送另行验收。
