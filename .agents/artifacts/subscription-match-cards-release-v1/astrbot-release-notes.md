# Dota2Forge 0.1.0-alpha.12：订阅比赛详情卡

- 比赛订阅在图片模式发送比赛总览、天辉详情和夜魇详情，突出订阅玩家，并保留事件 ID、来源、抓取时间和有限观察提示。
- 沿用完整比赛报告的数据边界：缺失指标显示未知，表现候选明确为非官方 MVP；相同来源时间只显示一次。
- 全部卡片完成渲染后在一次宿主调用中提交；绘图失败回退同一报告的完整分段文字。发送失败或未知回执保留现有重试边界。
- 渲染、发送、素材替换与关闭协调，插件停止时拒绝尚未提交的订阅发送。

运行组件：AstrBot adapter a12、Core a7、Renderer a7、Assets a1；Python 3.12+、AstrBot >=4.5.0。升级前停止 AstrBot，用其实际 Python 执行 `install_runtime.py` 后冷启动；保留配置、绑定与订阅数据。

M0 预发行；订阅默认关闭。2054 项禁网测试、五包构建及隔离安装通过；真实宿主主动订阅发送与客户端图片压缩另行验收。Cloud 审核状态独立于 GitHub Release。

[安装与更新](https://github.com/HBLADEH/astrbot_plugin_dota2forge/blob/main/INSTALL.md) · [完整更新日志](https://github.com/HBLADEH/astrbot_plugin_dota2forge/blob/main/CHANGELOG.md)
