# do 指令、MMR 预估与攻略源调研证据

2026-10-05。双端现有入口改do；do查询复用原玩家请求，并在图片/文本显示共享Core的静态社区段位区间估算。品牌、导入名、HTTP管理路径和既有图片素材保持原意；未部署宿主或发送消息。未知/未定级不估算，冠绝只给5620+下界，段位可能滞后，不保证实际分数落在区间。

## 离线与构建

- [统一检查记录](offline-checks-run4.log)：治理、Ruff、mypy63源文件、1254项禁网pytest通过；综合覆盖率92.79%，scripts97%/Core93%独立门槛通过，估算领域100%。[完成任务](../../tasks/done/2026-10-05-command-mmr-guide-survey.md)记录边界和接续。
- [构建日志](build.log)：四个包的sdist/wheel成功。
- [wheel验证](wheel-smoke.log)：四个包各自在隔离环境安装/导入成功，宿主SDK缺失，使用已有Pillow wheel离线安装。
- 首轮262项针对性禁网测试通过；全量发现玩家卡日志旧高度断言850，更新为960并保留1600px/2MiB限制。Ruff格式及换行失败分别保留于[首轮](offline-checks.log)、[重跑](offline-checks-retry.log)、[换行检查](offline-checks-final.log)；没有删除断言或放宽门槛。

## 视觉

[复现脚本](render_samples.py)使用生产PillowRenderer及已有本地Valve/生成背景包，输出到被忽略的.dota2forge-assets/previews-command-mmr-v1。共43张卡片：两张菜单、35种星级段位、冠绝、未定级和未知/非法编码，均有390px预览。[结构QA](qa.json)记录尺寸/文件大小/文字框：菜单780×1450，管理员780×1580，玩家780×960，最大306963 bytes。Renderer实际绘制时验证文字边界及重叠。

人工检查传奇1星、冠绝完整手机卡及菜单：do查询/其余do入口可读，3080–3233/5620+（仅下界）、原徽章星级、来源/抓取/未知观测时间与非精确说明完整，没有遮挡。均为account123合成数据，不保存真实账号或聊天截图。本机Bot发送和客户端压缩未验证。

## 在线调研

[获取摘要](source-probes.json)保存匿名HTTP公开请求的状态、结构及版本，无Token/玩家响应。D2PT两个JSON接口403；Spectral目录123个.build文件、许可及抽样200，最新commit2026-08-09，抽样敌法辅助7.41e；OpenDota英雄1出装接口200，四阶段计数。OpenDota猜测的源码spec路径404保留，不用该失败路径证明API能力；接口能力依据官方文档及真实itemPopularity响应。社区MMR计算页面200并核对阈值。

搜索抓取可读D2PT页面7.41f，但本机403不能解释成生产稳定接口。Spectral为CC BY-NC-SA 3.0，且位置/补丁滞后；STRATZ官网介绍攻略与GraphQL，但本轮没有带Token验证攻略schema。详情及建议见[方案](../../../docs/cookbook/hero-guides.md)，攻略没有实现。
