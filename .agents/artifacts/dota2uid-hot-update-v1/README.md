# Dota2UID a10 热切换实施验收

本目录记录本地候选与隔离验证，不含真实凭据、身份或聊天记录。[任务](../../tasks/done/2026-10-10-dota2uid-hot-update.md)、[决策](../../notes/implemented/2026-10-10-dota2uid-hot-update.md)。a10/Core a7 未公开发布或部署。

## 真实 SDK 隔离副本
[脚本](check_sdk.py)与[机器记录](native-sdk-validation.json)使用已下载的公开 GsCore `fb80b874533c23b565a74ebd8549ce09e4742a55` 源码副本，复制到新系统临时目录，排除 plugins/data/logs/环境文件。既有SDK解释器为CPython3.13.2、发行元数据gsuid-core0.11.0、Pillow11.3；这验证所消费接口，不是生产0.11.1/Pillow12.3同构环境。无需SDK函数替换，也不在真实宿主pip安装。

首启awaiting_config、原生配置保存→活跃reload→ready、唯一SV/hook/订阅调度通过。只在临时目录构造不同版本的合成Core a8 wheel：canonical a7内容保留，仅改元数据、增加可执行canary并重新计算RECORD/SHA256；不是第二个公开发行。真实原生reload自动关闭a7旧业务，四包均来自新代际，新Runtime类型及canary证明内存代码替换，配置/绑定/订阅三文件摘要保持。随后错误wheel摘要更新失败，恢复旧业务SV与唯一调度；最终关闭完成。

641个SDK源码文件摘要前后保持。socket连接/DNS/UDP在导入SDK前禁用，asyncio内部loopback提前创建。没有启动HTTP/WS监听或连接Provider/QQ；绑定只调用Runtime和临时SQLite。新候选中的配置/管理接口仍由原生权限依赖保护，真实API权限边界另依赖此前与统一测试证据，不把本脚本等同平台聊天验收。

## 构建与离线验证
五包离线构建通过，独立新venv逐包安装/导入通过，双端SDK-free分发smoke通过。当前本地候选为dist/plugin-distributions/a10-hot-update-v3；最终检查结果及后续候选指纹见任务。测试保留发送不确定语义、旧a6–a9协议拒绝、准备失败保留、导入失败回退、改写数据拒绝回退、关闭超时、并发重载和模块来源拒绝。

## 未验证项
Docker Desktop daemon不可用，未做Linux/Docker热切换。真实商店UI/Git更新、QQ实际图片/订阅递送未验收；本轮没有公开发布、生产部署或消息发送。旧a6–a9首次升级必须冷启动，schema/第三方变化不能由上述兼容案例推断可热升级。
