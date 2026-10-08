# AstrBot alpha.6依赖安装失败与a7验证

2026-10-07用户完整日志确认：商店下载Cloud缓存的0.1.0-alpha.6 ZIP，pip通过阿里云镜像安装普通项目包名时返回`No matching distribution found for astrbot-plugin-dota2forge==0.1.0a6`。三个项目的PyPI JSON接口均404。这里只保留错误摘要，不收录完整实例日志。

GitHub分发主分支修复提交为1ce602c8c13aad900b88f0f300222f7a2391a3d2；[a7公开预发行](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a7)保留Python adapter a7和Core/Renderer a4。三个项目依赖使用PEP 508 Release wheel URL和SHA256，第三方HTTPX/Pillow约束保留，见[公开清单](public-requirements.txt)。

统一离线入口1537测试通过（201.62秒），Ruff格式/lint、mypy73文件、治理检查通过；工具96%、Core93%。四包构建和独立wheel导入通过；双端生成清单禁网安装、首配、关闭与绑定重启保留通过。新增离线检查拒绝缺失/篡改的wheel及URL与runtime manifest漂移，映射为保留hash的file URI。

显式在线安装验证使用独立CPython3.12.9 Windows venv，直接pip install -r已发布a7 requirements，无预装项目包；成功取得三个公开wheel和第三方依赖，pip check无冲突，项目版本及导入核验通过。在线发行核验与普通禁网测试分开。7个公开资产经匿名下载均与本地已发布候选字节/SHA256一致，见[摘要](release-assets.json)；主分支requirements也一致。后续本地指南和离线检查修正不覆盖已发布a7文件。

Cloud版本页本轮两次读取超时，未执行商店提交；随后用户确认商店版本已为0.1.0-alpha.7。03:23新日志确认alpha.7/1ce602c的Cloud ZIP下载/解压成功，pip访问github.com:443的Release wheel发生连续15秒连接超时，依赖仍未安装。此时真实部署环境的GitHub访问失败已明确，Python/核心约束和加载尚未验收。旧4.28.2聊天记录不替代本次验证；已装旧库仍按停机安装器/冷启动升级。

用户随后授权SSH诊断部署服务器。凭据仅在内存中传给匹配known_hosts的SSH连接，不写入项目或证据文件。实际Linux Docker使用Python3.12.13、AstrBot源码4.28.1；诊断时GitHub首页及三个Release资产HEAD均HTTP200，未修改代理或网络设置。

使用原alpha.7 requirements与宿主原生57条Core约束，7.21秒安装完成；仅新增adapter a7、Core/Renderer a4，原198个包版本全保留。pip check前后均通过，三个wheel的direct_url记录摘要与公开清单一致；真实SDK入口导入成功。重启AstrBot容器后，实际日志明确Dota2Forge initialized state=awaiting_config，默认配置/数据目录已生成，Token为空；WebUI HTTP200。详见[脱敏部署证据](remote-install.json)。保留原有配置和数据，不发送聊天；Provider、图片与订阅尚未验收。

当前部署安装问题已解除，但未另行点击商店按钮重试完整API流程；网络恢复不等于永久GitHub连通保证。运行包位于容器层，重建后需重新执行依赖清单。任务完成后用户在WebUI填写自己的Token、保存/重载进入使用阶段，凭据不经聊天传递。
