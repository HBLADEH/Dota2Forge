# 自动素材下载实施计划

Status: active

本地实施与验证完成；待维护者评审及生产宿主/商店发行联调。

## 目标
按[提案](../../notes/proposed/2026-10-07-managed-illustration-download.md)实现双端首次自动下载、管理员ensure/update/status及受控快照切换，解决商店新装英雄占位和UI镜像失败连带整包问题。

## 非目标
不把游戏图片放进wheel；不在Renderer/普通查询中联网；不自动生成背景、不新增Provider请求或主动群发；首版不做HTTP字节续传/周期全量更新。

## 验收
1. 新装image/auto后台下载，空Token仍awaiting_config但素材可准备；text/manual/off及旧自定义路径无隐式网络。两端严格配置、现有消费者和管理命令权限均验证。
2. 导入/构造无I/O；transport/时钟/文件系统可注入，普通测试禁网。覆盖4并发、期限/重试/429、冷却、单任务及真实进程锁争用/退出释放；独立客户端不带Token、代理显式注入、状态/日志不泄漏凭据。
3. 只有404成为missing；超时/403/损坏为失败状态。模拟全部UI源不可用仍发布可用英雄/装备partial；保留旧图原时间，未完成文件可续作，已验证完整快照启动不联网。
4. 验证ID/源/重定向/路径/摘要/PNG/清单/磁盘边界；取消、写入中断、指针更新前后进程退出都保留完整旧或新快照。失败不捏造完成百分比。
5. 一组分页固定快照，更新后下一组加载新图、不增加Provider请求；关闭等待旧线程和下载所有权，STOPPING后无切换。两端冷启动/重复start/stop/reload逐一验收。
6. 第五个包及policy/验证配置按根规则维护者评审；不降低门槛。两端guard、固定URL/hash、四组件清单/CLI/离线smoke同步，拒绝漏包/错误extra/篡改资产/两端互换。
7. 统一离线、五包构建/独立wheel、双端隔离新装/升级通过后，真实首次后台下载/部分网络失败/自定义路径/图片与关闭单独联调。实际素材和凭据不作为普通测试前提。

## 影响模块与决策
[共享素材服务](../../../packages/dota2forge-assets/)、[现有下载器](../../../scripts/download_dota_assets.py)、[AstrBot](../../../adapters/astrbot_plugin_dota2forge/)、[Dota2UID](../../../adapters/Dota2UID/)、[分发生成器](../../../scripts/build_plugin_distributions.py)、[公开安装器](../../../scripts/gscore_public_runtime.py)。Core/Renderer源码保持既有边界；下载、验证与缓存进入独立第五包，两端只持有配置、权限、后台生命周期与快照切换。[实施决策](../../notes/implemented/2026-10-07-managed-assets-service.md)记录公共契约、缓存/重试及治理变更。

## 验证证据
2026-10-07用户授权实施，保留依赖修复/素材部署/设计的已有未提交改动。双端默认image/auto、三条管理命令、独立共享包及四组件分发均已实现。

- 最终统一离线入口exit0：1608测试通过（223.17秒）、Ruff格式/lint、mypy82源文件、总覆盖93.03%，治理工具96%/Core93%/Assets92%。五包构建/独立wheel与双端SDK-free隔离分发均通过。
- 用户授权服务器内独立临时目录真实下载54.3秒：127英雄、415装备、15界面图，共557张可用PNG；129装备HTTP404单独记录，无其他失败。重开完整快照不联网；合成战绩卡成功，截图对应英雄可解码。
- 两端SDK-free Runtime在Linux容器验证空Token、重复启动、完整快照复用及关闭释放租约。离线测试覆盖UI网络失败/续作、整组切换与等待旧Renderer关闭。新自动功能未替换生产插件或发送聊天；隔离目录已清理。

命令、候选版本/SHA256、真实联调范围与限制见[实施证据](../../artifacts/managed-illustration-download-v1/README.md)。

## 阻塞与下一步
第五包的policy/schema/checker变更须维护者评审，门槛未降低。候选AstrBot a8/Dota2UID a5/Assets a1尚未发布；下一步为评审后真实注册宿主的首次自动下载、热重载/关闭及聊天验收，再按授权发行并核验商店索引。验收6的评审与7的生产宿主联调尚未完成，不以SDK-free验证替代。
