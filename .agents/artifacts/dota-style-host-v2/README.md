# 深色卡片与背景本机部署证据

2026-10-05用户授权部署和聊天实测，并选择自己在手机/QQ发命令，由Agent核对两端日志。保留工作区已有修改；无外部代码/包发布，不保存真实聊天、身份、凭据或业务响应。

## 构建与安装

背景生成任务的1144项禁网检查已通过。`uv build --all-packages`和`uv run --locked python scripts/smoke_wheels.py`本轮再次通过，四包分别在无索引环境安装导入。

初始GsCore/AstrBot没有进程或8765/6185监听；没有对存活旧实例跳过stop。两端专用数据目录backups/dota-style-v2-20261005-041210保留配置、数据库、发现桥接、原三个包及dist-info；未把敏感备份写入仓库。安装前确认仍已停机；无索引/无依赖重装各自三个明确wheel，Pillow12.3.0、HTTPX0.28.1不变。

更新GsCore发现入口及AstrBot四份资源；使用既有[逐文件检查](../subscriptions-host-v1/verify_install.py)核对六份安装包和双端桥接均匹配构建/源码。

## 独立资源与就绪

两端分别配置本机数据目录illustrations-v2；各复制manifest与543张PNG（127英雄、415装备、1生成背景），每张摘要验证，129个官方装备缺项保留。manifest保持英雄/装备/catalogs来源；新背景摘要与[生成记录](../dota-style-v2/header-generation-v2.json)一致。配置只增加illustration_path，原凭据/绑定/订阅设置保留，数据库在启动前指纹未变。

实际宿主Python载入安装包，GsCore/AstrBot均生成780×1450菜单并确认本地header进入解码缓存，分别309068/310192 bytes；Pillow/HTTPX版本不变。PNG在各自本机validation-style-v2目录，属于无Provider的菜单验证。

隐藏启动原GsCore模块入口与AstrBot桌面入口；新日志明确GsCore lifecycle ready/image、AstrBot initialized ready，监听8765/6185，OneBot反向WS监听6199。GsCore进程由venv解释器的原生Python子进程承载，未启动第二套Core。

最小状态和安装结果见[结构化记录](deployment.json)。

## 聊天验收

用户确认AstrBot `/dota菜单`正常展示图片，测试的其他指令也正常返回对应图标。基线后的AstrBot日志提取到静态命令名dota帮助、dota战绩、dota玩家；未见插件RenderError、ConfigurationError或旧版卡片类型冲突标记。OneBot反向WS已建立连接。客户端显示依据用户反馈；日志没有逐次图片发送计数，不据此补写数量或尺寸。具体分页、五人详情和手机文字可读性未获本轮逐项确认。

GsCore已部署并ready，8765仍在监听；AstrBot插件页显示既有GsCore桥接关闭，本轮保持该状态，未建立8765连接，新增日志没有Dota命令。GsCore聊天验收尚未完成，不把两端安装PNG验证或AstrBot成功记为GsCore聊天成功。

本轮统一离线入口重跑通过：1144项禁网测试，Ruff格式/lint、mypy62源文件，聚合覆盖率92.72%、scripts97%、Core92%。初次因Dota2UID指南超过文档预算在测试前失败，移除本轮新增的重复部署段落后通过；失败与通过日志均保留，详见[检查摘要](checks.json)。没有修改测试、policy、治理脚本或门槛。

完整进度见[任务](../../tasks/active/2026-10-05-dota-style-host-deployment.md)。
