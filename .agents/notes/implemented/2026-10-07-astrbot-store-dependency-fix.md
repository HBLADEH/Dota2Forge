# AstrBot 商店依赖使用公开 Release wheel

Category: bug-fix
Related task: [商店依赖修复](../../tasks/done/2026-10-07-astrbot-store-dependency-fix.md)
Related code: [分发生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [分发契约](../../../docs/subsystems/plugin-distribution.md)

## Problem
用户补充的AstrBot 4.28.1完整日志确认：Cloud下载alpha.6缓存ZIP，requirements使用普通项目包名，pip通过阿里云镜像返回`No matching distribution found for astrbot-plugin-dota2forge==0.1.0a6`。三个项目包只发布在GitHub Releases，未发布PyPI；2026-10-07三个PyPI JSON接口均404。上层`code 1`只是失败退出码。GitHub主分支更新不会替换Cloud已缓存的alpha.6。

## Decision
AstrBot公开分发requirements改为GitHub Release wheel的PEP 508 URL，并为每个URL附SHA256；第三方httpx/Pillow仍使用版本约束。a7 Release上传Core/Renderer a4 wheels、AstrBot adapter a7 wheel和桥接ZIP。离线smoke核对URL与公开清单一致、校验本地wheel摘要，再映射为保留hash的file URI；缺失/篡改/漂移失败。商店环境直接从GitHub下载，普通测试保持禁网。

适配器版本升为0.1.0a7 / Cloud显示0.1.0-alpha.7，版本要求保持 `>=4.5.0`。不依赖 PyPI，不在插件导入时运行 pip，不改 Core/Renderer或业务逻辑。

## Alternatives considered
- 发布PyPI：需要独立认证、包名占用及后续维护，本轮不增加外部发布面。
- 让用户手动安装 wheel：不能满足官方商店一键安装，作为安装指南补救而非主路径。
- 在导入时自行pip：绕过宿主依赖生命周期和安全审查，不采用。

## Consequences
商店安装需要访问GitHub Release；网络受限环境仍会失败。每次共享包更新必须同步生成新Release和三条hash URL；旧a6资产保留。GitHub Release公开地址和摘要成为分发契约。4.28.1上游requirements预检对URL只检查包名，已装旧库仍按停机安装器/冷启动流程升级；不把新装修复当作热升级保证。

后续用户alpha.7日志确认Cloud ZIP可下载，但GitHub Release连接超时；直链方案仍有此部署网络限制。用户授权SSH诊断，按实际HTTP代理/宿主约束处理，凭据不落盘；未另行授权发布PyPI或更换第三方公共镜像，不自动扩大分发策略。

## Verification
requirements生成、a7构建、公开资产和双端离线smoke证据记录在任务中。alpha.7 Cloud包实际下载通过，随后GitHub曾连接失败；授权SSH诊断时网络恢复，同清单与宿主57条约束安装通过，原198包不变，pip check及摘要/SDK导入通过。实际4.28.1 Linux容器冷启动加载为awaiting_config；用户Token为空，业务/聊天尚未验收。未修改代理或网络，不承诺未来可达；已发布a7资产保留原字节。
