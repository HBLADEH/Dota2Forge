# 双商店收录补证与分发前置条件

Category: architecture
Related task: [核查任务](../../tasks/done/2026-10-05-plugin-store-verification.md)
Related code: [AstrBot 安装器](../../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/install.py)、[Dota2UID 安装器](../../../adapters/Dota2UID/src/Dota2UID/install.py)
Related docs: [商店核查](../../../docs/subsystems/plugin-distribution.md)

## Problem

[10-04建议](2026-10-04-plugin-store-distribution.md)已识别共享业务适合双端、主仓根布局不能直接安装，但未核实GsCore收录方式。用户提供索引仓库和近期PR，需补证并区分商店收录与安装成功；当前还有新的do命令/MMR/出装及资源改动，不能复用旧版本宿主证据作为全部发布验收。

## Decision

本记录补充10-04建议，不改变已实现架构，不代表分发已实施。

GsCore收录路径已由2026-09-27合并的MingChaoBQ PR #39及现场索引核实：向Genshin-bots/GenshinUID-docs的vp分支提交docs/public/plugin_list.json变更，新增plugins条目和合适分类。AstrBot使用官方Cloud发布入口，提交GitHub插件来源。两端均须先具备可直接发现并取得依赖的发布产物。

继续建议Dota2Forge单仓开发、联合检查，由同一版本生成两个独立分发仓库；GsCore仓库名优先Dota2UID，AstrBot为astrbot_plugin_dota2forge。双端共享Core/Renderer不变，业务源码仍由主仓维护。独立仓库是降低安装/更新歧义的推荐，并非两个商店都强制要求拆源码仓库。

以当前薄桥接为基础，先评估发布四个现有wheel，使依赖能够自动取得；这是一种实施方案，商店没有强制要求使用PyPI。分发入口分别提供根main.py/metadata.yaml/_conf_schema.json/requirements.txt和根__init__.py/宿主pyproject/配置说明，包含README与许可证。修正AstrBot元数据repo，使用新的明确版本及已验证的Core/Renderer/适配器版本组合，不用重复0.1.0a1表示不同源码。

GsCore发布清单需处理已有依赖不满足新约束的情况；可评估gscore_auto_update_dep配合总开关与加载时版本检查，不默默接受旧库。Python>=3.12必须明示并在早期给出兼容性错误，不能假定商店所有宿主符合。保留专用数据目录和严格Token校验，但改进首次配置引导：缺配置/Token不应导致难以配置的安装失败，明确待配置状态，配置后能恢复就绪；不要为了上架嵌入开发者凭据。

实施顺序：

1. 生成两端分发产物，审查许可、来源、版本、资源与ZIP大小；统一离线检查和构建。
2. 使锁定依赖可取得，准备兼容宿主的干净安装环境；发布流水线变更单独交维护者评审。
3. 验证首次安装无需本地workspace/预装私有wheel；空Token可配置、配置后基础查询/图片正常。
4. 验证旧版升级、受控关闭/重载/冷启动、卸载及数据保留，覆盖拟支持的Windows/Linux与解释器。
5. 再提交GsCore索引PR、AstrBot Cloud申请；索引合并/申请通过与商店真实安装分别记录。

首个有限版本可发布已实机验收的绑定、玩家、近期及单局图片；若包含当前do/MMR/出装改动，需补对应宿主和真实聊天验收。订阅默认关闭，实测完成前明确实验状态；AI/IMP、Valve补充和Deploy仍按原任务推进，不作为全部必须先完成的门槛。

## Alternatives considered

- 专用发布分支：规范允许AstrBot分支URL，GsCore索引有branch；可行但需根布局，且GsCore目录仍取仓库尾名。当前建议独立生成分发仓库便于两端更新与身份一致。
- 按版本自动携带共享源码：不依赖四个PyPI包，但需要处理命名空间、模块重载、字体体积和许可；须实际证明ZIP<16MB和更新正确。可以作为备选，禁止手工复制后各自维护业务。
- 主仓/adapters子目录直接登记：宿主不执行workspace或安装器，缺发现与依赖步骤，不能满足安装。
- 立即拆成多仓独立开发：增加公共契约、版本和双消费者验证成本，当前没有必要。

## Consequences

业务架构无需重写，仍需新增发行工程和真实安装证据。自动安装不等于零配置，也不保证热更新已生效。共享库/Pillow更新仍须处理进程缓存与Windows DLL占用；schema升级和数据回退单独验证。商店收录由外部维护者决定，不能承诺自动收录。

## Verification

只读核查2026-10-05远端引用、固定源码、实际索引、PR补丁、官方发布/市场规范、PyPI接口和本地安装器。GitHub未鉴权API触发403限流后改用git ls-remote、公开页面及固定提交raw源码，没有绕过权限。现场索引42项、无Dota2UID；四个PyPI接口404。

检查结果见关联任务。此调研阶段未实现分发生成器/新配置状态、未发布包、未登录提交商店、未验收干净商店安装或升级；记录保持proposed。随后已落实第一阶段本地候选，见[实施决策](../implemented/2026-10-05-plugin-distribution-stage1.md)；其余公开分发和实机前置条件仍待完成。
