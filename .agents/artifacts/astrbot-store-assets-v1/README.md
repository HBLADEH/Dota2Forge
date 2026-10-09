# AstrBot商店安装后的素材配置

2026-10-07用户提供正式部署的战绩卡截图，数据/卡片已有，英雄图为问号。授权SSH检查确认illustration_path为空，插件数据目录没有素材。截图涉及真实账号/聊天，因此不收录原图、原始日志或身份。

原下载器显式运行时取得英雄和装备，随后raw.githubusercontent.com上的OpenDota图标镜像发生SSL握手/读取超时，返回1且没有发布manifest。没有把网络失败标为404缺图。采用同一用户本机2026-10-05已下载的完整快照做私有同步，保留Valve官方来源、OpenDota镜像来源、抓取时间、版权和生成背景来源。

558张可用PNG本机与服务器均用实际Illustrations逐一校验摘要/解码；127英雄、415装备、9段位、5星级、1金币、1背景，129项官方装备404保留。传输档案仅含清单列出的资源和RIGHTS.txt，不含配置或真实数据。档案SHA256为0be99271135a5d4355380a72a81ea0b7c88fbf91c4af1ae6480405fee7032f46，原manifest SHA256为7013656e48ce333be8cec9e3a1f20b54bc80ef47732519795e5d0c86583093e8。

实际Linux/Python3.12.13、Renderer0.1.0a4生成FIXTURE战绩卡780×1560/366425字节，并与无素材图比较英雄区域像素；390px预览人工核验英雄/金币/背景正常。合成图仅留在被忽略的本地素材预览目录，不收录Valve图片。详见[素材验证](validation.json)。未调用Provider或发送聊天。

持久化路径为容器内data/plugin_data/astrbot_plugin_dota2forge/illustrations-store-v1。实际适配器load_config接受该相对路径；配置只改变illustration_path，其余字段/Token相同，敏感备份仅在服务器保存并限制0600，见[配置摘要](config-change.json)。不记录凭据、Token、地址、绑定或订阅内容。

统一离线[完整日志](offline-checks.log)通过1537测试（186.41秒）、310文件Ruff格式/lint、mypy73源文件、工具96%/Core93%覆盖率。后续纯文档/证据更新的[治理静态检查](governance-final.log)通过，不重复普通测试。

目标AstrBot容器冷启动后running，实际日志为lifecycle state=ready reply_mode=image及Dota2Forge initialized state=ready。重启后读取配置并加载manifest，原截图五位英雄ID16/26/58/92/131均成功解码；WebUI HTTP200，三个运行包版本仍a7/a4/a4，见[启动证据](startup.json)。真实平台新图反馈等待用户重查，商店ZIP没有因此新增游戏素材。

本轮容器临时工作目录与宿主传输档案已在核对目标路径/摘要后移除；持久化素材和服务器私有配置备份保留，SSH已关闭。安装说明修正仅在本地工作区，未另行对外发布。
