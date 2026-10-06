# 实机截图筛选与独立分发

Category: feature
Related task: [截图任务](../../tasks/done/2026-10-05-plugin-screenshots.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)、[验证](../../../tests/test_plugin_distributions.py)
Related docs: [AstrBot说明](../../../adapters/astrbot_plugin_dota2forge/README.md)、[来源](../../../docs/assets/screenshots/README.md)

## Problem
用户提供五张图片并授权按需使用。四张仍显示旧dota命令，玩家卡没有MMR，且绑定/玩家/战绩含身份或关联账号；不能作为当前do/MMR展示。原发行生成器仅携带README与图标，补入本地图片后若不更新打包会产生缺图。

## Decision
仅采用完整且无身份信息的主宰出装原图，保留用户文件并以原始PNG字节复制。其他图不纳入仓库，缺项明确待补；不改字或生成聊天证据。AstrBot说明展示完整出装卡，注明命令输入未入图。

生成器使用按插件声明的审核白名单复制截图到screenshots/，README对应源路径转为插件本地路径；源图及目标文件均进入摘要，继续固定ZIP时间/权限/顺序和16MB检查。缺图在输出前失败。GsCore不携带AstrBot图片。

## Alternatives considered
递归扫描图片目录会自动纳入未审核文件；使用主仓远程图片链接使独立ZIP展示依赖未发布的远端。采用显式本地白名单，避免这两个问题。旧菜单/MMR缺项不适合通过修改图片文字补齐。

## Consequences
AstrBot ZIP增加约0.3MB，仍需实际核对大小。截图体现当次观察，不能扩展为所有平台/权限/API长期稳定验收。出装完整卡无身份信息，保留原始数据与第三方美术权利说明；其他截图需要现行版本且脱敏。

## Verification
目视查看全部源图；出装原图完整、来源/脚注保留，源/目标SHA256一致，780/390px浏览器展示无裁切且可读。测试新增独立README/ZIP本地图片和双摘要核对、GsCore隔离以及缺图无输出；统一入口退出0，Ruff/mypy71文件通过，1376禁网测试通过，scripts96%/Core93%。新AstrBot ZIP1917604 bytes，GsCore原ZIP字节保持；[证据](../../artifacts/plugin-screenshots-v1/README.md)。

2026-10-06用户明确授权GsCore共用此前图片，后续[共用决策](2026-10-06-shared-plugin-screenshot.md)取代本记录的GsCore展示隔离，原始筛选、隐私与真实验收范围保持。
