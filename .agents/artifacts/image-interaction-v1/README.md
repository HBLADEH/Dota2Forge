# 图片交互样图 v1

这是样图确认阶段的离线 Pillow 原型，不是生产 Renderer。数据全部为合成 fixture；没有访问玩家 Provider、配置、凭据或宿主。原型、字体子集和 PNG 共用这一版本目录。

- [总览](samples/overview.png)：菜单、玩家概况、近期战绩和绑定状态。
- [战绩第 1 页](samples/recent-1-mobile.png)、[第 2 页](samples/recent-2-mobile.png)：默认 10 场，每页 5 场。
- [未知玩家](samples/player-missing-mobile.png)、[空列表](samples/recent-empty-mobile.png)：不把缺失数据画成零。
- [QA 数据](samples/qa.json)：记录文字边界、预期昵称省略、PNG 大小、字体覆盖和 100 条布局检查。

画布 780 px，手机预览 390 px；标题 42 px、内容 28–40 px、辅助信息 26 px（390 px 下为 13–20 px）。浅灰信息区、炭黑标题，绿/红/琥珀分别标识胜/负/未知，同时有文字，不单靠颜色。来源 fixture、抓取时间和未知观测时间可区分；所有时间明确北京时间 UTC+8，时长保留分钟/秒。长昵称单行省略属于当前待确认版式。

菜单记录制作样图时的已注册命令，不列图片翻页或管理员功能。后续已在代码中实现 `dota比赛 <比赛ID>` 文本入口，尚未部署到宿主；生产 Renderer 接入时需同步菜单和战绩卡查询提示。数据卡的比赛 ID 可以核对，不承诺真实历史覆盖。

## 字体与资源

字体源：[Noto Sans CJK SC Regular](https://github.com/notofonts/noto-cjk/blob/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf)，固定提交 `f8d157532fbfaeda587e826d4cd5b21a49186f7c`，上游 OTF SHA256 `2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b`。Copyright 2014-2021 Adobe。

随样图附 [OFL 1.1](assets/OFL.txt) 和已改内部名称的 [Dota2Forge Preview CJK](assets/preview-cjk.otf) 子集，约 67 KB，仅覆盖已知样图字符；子集保持 OFL，不适用于任意生产昵称。生产 Renderer 需要完整字体和缺字策略，不能把本子集当成完整中文字体。

2026-10-01 通过 [Valve 公开英雄列表](https://www.dota2.com/datafeed/herolist?language=schinese) 核对 1/2/5/21/44 对应敌法师/斧王/水晶室女/风行者/幻影刺客；未知 ID 保留原数值，未知英雄不推断。没有打包 Valve/第三方图像；灰色问号是自绘缺图占位，主题也为本项目原创。后续全量名称映射及英雄/装备美术资源仍需版本、来源与许可记录。

## 复现

已缓存脚本依赖时可完全离线生成：

```sh
uv run --offline --no-project .agents/artifacts/image-interaction-v1/preview.py
```

首次去掉 `--offline` 安装脚本声明的 Pillow 12.3.0、fontTools 4.60.1；这是独立脚本环境，不改 workspace 依赖或锁文件。生成器本身不联网，不参与普通 pytest 的应用覆盖率。用 `--output <目录>` 复核输出；字体有许可证与 SHA256，但 PNG 一致性只在同解释器/Pillow/字体版本下比较。

从本地原版字体重建子集：

```sh
uv run --offline --no-project .agents/artifacts/image-interaction-v1/preview.py --prepare-font <原版OTF路径>
```

[展示契约草案](../../notes/proposed/2026-10-01-renderer-preview-contract.md) 记录生产包、文本回退与大列表发送边界，均待实施。QQ 实机压缩、分页发送、停用与重载没有由样图验证。
