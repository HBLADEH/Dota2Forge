# AstrBot README 实机截图

Status: done

## 目标
按用户授权选用D:/bot/img实机图片，补入AstrBot插件README，并同步独立分发包中的图片、链接及来源摘要。

## 非目标
不改写截图中的命令或业务数据，不提交原始聊天身份，不把旧dota图当作现行do/MMR验收；不更新GsCore宿主、不发布远端或发送聊天。保留既有工作区修改和源图片。

## 验收
- [x] 查看五张源图，筛选版本、完整性与身份泄漏。
- [x] 将无身份信息的完整出装原图保存为AstrBot展示图片并嵌入README。
- [x] 分发生成器携带图片，重写本地展示路径，纳入摘要与ZIP大小检查；补充有效验证。
- [x] 同步实机范围、待补截图及许可来源，运行统一离线检查。

## 影响模块与决策
[AstrBot说明](../../../adapters/astrbot_plugin_dota2forge/README.md)、[截图清单](../../../docs/cookbook/plugin-showcase.md)、[发行生成器](../../../scripts/build_plugin_distributions.py)。延续[说明与图标](../../notes/implemented/2026-10-05-plugin-readmes-icon.md)和[本机部署](../../notes/implemented/2026-10-05-astrbot-screenshot-update.md)。

## 验证证据
五张源图目视查看：菜单/绑定/玩家/战绩为旧dota入口，玩家无MMR；绑定/玩家含聊天身份与账号，战绩含账号及比赛ID，不复制入仓库。出装为780×1530完整主宰四阶段卡、OPENDOTA来源、时间及未知/非最优提示，无身份信息，可原图采用。不记录真实身份或账号。

采用原图SHA256与本机来源一致，PNG无附加元数据；README和本机插件说明已同步，不重启运行库。浏览器780px/390px展示均加载完整卡片，无裁切，目视文字可读。[证据](../../artifacts/plugin-screenshots-v1/README.md)含QA和摘要。

新候选dist/plugin-distributions/0.1.0a2-showcase-v1重复生成一致，AstrBot ZIP1917604 bytes，GsCore ZIP1622100 bytes且保持原字节；全部输入/输出摘要匹配。新增本地图片/双摘要/平台隔离及缺图无输出验证。统一入口退出0：Ruff/mypy71文件通过，1376禁网测试通过（196.89秒），scripts96%、Core93%。

## 阻塞与下一步
已交付可用出装图与对应说明、候选，不发布远端。现行do菜单、绑定/账号、MMR玩家、战绩分页、两阵营详情、配置图及GsCore截图保留待补，出装命令输入也未入图；后续按清单接续。用户源文件未修改，旧图未进入仓库。
