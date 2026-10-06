# 0.1.0a4 装备名称留白与双端公开分发

Category: feature
Related task: [发行任务](../../tasks/done/2026-10-06-a4-layout-release.md)
Related code: [图片引擎](../../../packages/dota2forge-renderer/src/dota2forge_renderer/engine.py)
Related docs: [分发契约](../../../docs/subsystems/plugin-distribution.md)

## Problem
长装备名第二行与购买次数、下一名玩家间距不足，用户反馈阿哈利姆神杖等显示拥挤。要求整理当前项目成果、升级并提交代码，同时授权推进AstrBot商店申请。

## Decision
图片使用审核过的简称：A杖、A杖福佑、臂章、祭品、风杖、大炮、术士魔典；肉山/消耗品变体保留区别。图纸保留图纸后缀，文字回复继续显示完整原名和ID。整个本地名称表在108/124px两种格宽下严格验证不裁字，未知ID保留完整数字，无法容纳则文本回退。

卡片仍宽780px；出装阶段步长252px，图名与次数留白，卡高1674；比赛玩家区步长340px，三人页1706px。图片高度上限改为1800，2MiB限制不变；这是按用户要求增加留白的输出契约变化，双端与边界测试同步，不放宽验证门槛。所有卡片共享相同资源路径和生命周期。

四包统一0.1.0a4，最低项目依赖同步更新。用户已授权GitHub发行与AstrBot商店申请；新增AstrBot公开分发模式，复用既有显式CLI安装器，按插件身份白名单绑定对应仓库及三个包，不在import中联网。固定版本/SHA256下载、保留宿主Pillow约束与pip check继续执行；PyPI未发布，首次仍须退出宿主、安装运行组件再冷启动，不能宣传一键热安装。

AstrBot与Dota2UID各有独立分发仓库、安装文档及自己的adapter wheel；Core/Renderer共享。旧发行资产不覆盖，商店未审核不称上架。开发仓库整理采用codex分支与PR，治理工具/流程未改；分发脚本在PR中供维护者评审。

## Alternatives considered
- 仅缩小字体：手机阅读恶化；保留26px最低字号，以简称和留白解决。
- 图片仅省略号：不能判断长装备，改为全名称表无截断检查。
- AstrBot将项目依赖改成无版本URL：宿主更新策略不保证升级已安装包，沿用有版本清单及显式CLI，诚实说明步骤。

## Consequences
图片略变长，十人仍四页；具体宿主图片压缩效果待聊天验收。首次公开AstrBot为预览版，不扩大宿主>=4.28.2,<4.29兼容声明。公开组件安装、SDK实测、Cloud提交/审核分别记录。

## Verification
整个装备表、已知简称/图纸、未知ID和新高度边界测试；手机合成预览、四包构建、双端隔离安装与统一检查由[发行任务](../../tasks/done/2026-10-06-a4-layout-release.md)记录。没有以旧a3或a2验收冒充新版本，未操作生产宿主。
