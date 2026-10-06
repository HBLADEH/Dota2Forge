# AstrBot 兼容版本下界验证

市场声明从`>=4.28.2,<4.29`改为`>=4.5.0`，不再以一次本机验收版本限制用户安装。上游v4.5.0的本插件公开导入路径均已只读核对；实际宿主/OneBot验收仍只有v4.28.2，不能据此声称全部版本实机通过。

统一离线检查1537项通过（161.54秒），Ruff/mypy通过，治理工具96%、Core93%。分发/桥接/包元数据相关50项通过；a6候选双端无SDK隔离安装通过。AstrBot适配器为Python0.1.0a6，Cloud版号0.1.0-alpha.6，Core/Renderer保持a4。

[AstrBot a6预发行](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a6)的七个资产匿名下载均与候选一致，详见[摘要](release-assets.json)。商店更新需用户重新登录后提交；未更新生产实例或重发旧版本。
