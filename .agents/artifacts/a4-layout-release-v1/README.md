# 0.1.0a4 验证与发布记录

本轮修正长装备名：图片使用A杖/臂章/祭品等简称，完整名称保留在文字回复；增加阶段/玩家区的底部留白。出装1674px、三人比赛1706px，上限1800px/2MiB。

`render_samples.py`复用共享绘图，使用合成玩家、统计及已有Valve本地素材。样图显式FIXTURE，不是实机截图；第三方美术仍属Valve，不改为MIT。包含长名/图纸/特殊变体、四页十人、未知装备和无素材场景。手机宽390px。

统一离线检查退出0：1532测试通过（152.77秒），Ruff格式/lint、mypy73文件通过，治理工具96%、Core93%。最终宿主元数据文案/仓库地址更新后45项相关测试通过。四包构建、四个独立wheel安装导入、双端无SDK离线安装/首配/重启绑定保留均通过。两端另在全新环境运行公开安装器，从GitHub下载a4组件、pip check与实际PNG绘制通过，见[公开安装](public-install.json)；仍不等于实际宿主/聊天验收。

公开[Dota2UID a4](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a4)（分发提交eb03ae3）与[AstrBot a4](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a4)（分发提交8939503）。25个公开文件及两端各7个资产匿名下载与候选完全一致，见[摘要](public-checks.json)及[源清单](distribution-manifest.json)。AstrBot ZIP 1,921,901 bytes，低于16MB。旧版本资产未覆盖。

[AstrBot Cloud](https://cloud.astrbot.app/plugin/HBLADEH/astrbot_plugin_dota2forge?tab=versions)提交成功，显示v0.1.0a4 / Waiting / 已提交发布，等待安全检查，见[页面证据](cloud-submitted.png)。非审核通过；GsCore PR #40继续待审核。

敏感模式扫描未发现凭据；SteamID格式命中仅常量与合成测试。已有真实截图已审查无身份，新增预览为合成数据；未提交本机配置、数据库或素材包，见[审查范围](privacy-review.json)。

新版本在线Provider字段、生产宿主/真实聊天及Linux仍未验收，未部署生产或发送消息；[任务](../../tasks/active/2026-10-06-a4-layout-release.md)区分已实现与尚未验证。
