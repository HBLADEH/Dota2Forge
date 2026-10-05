# AstrBot 出装截图采用证据

用户授权按需使用本机五张截图。本轮只采用完整且无身份信息的主宰出装卡；菜单/绑定/玩家/战绩仍显示旧dota入口，玩家无MMR，部分包含账号或聊天身份，未复制入仓库。不修改源图片、不生成或改写实机数据、不发送聊天、不发布远端。

- [来源与范围](../../../docs/assets/screenshots/README.md)：审查后的原始PNG780×1530、302705 bytes，无附加PNG元数据，源/目标字节及SHA256一致。
- [核对摘要](review-summary.json)：候选全部来源/产物摘要匹配，重复生成一致，AstrBot ZIP1917604 bytes（低于16,000,000），GsCore ZIP字节保持。
- [视觉QA](visual-qa.png)：浏览器加载780px完整原图与390×765手机宽展示，目视阶段、文字、来源和脚注可读且无裁切。静态预览不属于真实聊天客户端截图。
- [统一离线检查](check-governance.log)：退出0，治理/Ruff格式与lint/mypy71文件通过；1376测试通过（196.89秒），scripts96%、Core93%。新增独立ZIP本地图片与双摘要、平台隔离、缺图无输出检查。

AstrBot README展示卡片并明确命令输入未入图。发行生成器白名单携带原图到screenshots/，转换本地图片链接，不扫描原始目录。生成候选为dist/plugin-distributions/0.1.0a2-showcase-v1；旧候选不覆盖。原本机插件README备份后同步说明与图片，未更改运行库、桥接或配置，无需重启；不宣称宿主内Markdown查看器已验收。

其他现行do菜单、绑定/账号、MMR玩家、战绩页与取页、两阵营详情、配置图、GsCore图片以及出装命令输入均待补。仅凭这张卡不推定其他平台、权限、动态命令捕获或长期API稳定性；接续见[截图清单](../../../docs/cookbook/plugin-showcase.md)。
