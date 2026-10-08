# 自动素材下载实施证据

2026-10-07。用户授权实施[任务](../../tasks/active/2026-10-07-managed-illustration-download.md)，现已完成本地实现、离线验证与服务器隔离验证；[决策](../../notes/implemented/2026-10-07-managed-assets-service.md)及[使用指南](../../../docs/cookbook/illustrations.md)同步。既有依赖修复、手动素材部署和设计改动均保留。

## 本地候选与离线检查

新增独立dota2forge-assets 0.1.0a1，接入AstrBot 0.1.0a8和Dota2UID 0.1.0a5；Core/Renderer仍0.1.0a4。两端默认image/auto，提供do素材状态、管理员do下载素材/do更新素材；空Token可准备公共素材，自定义目录优先，text/manual/off无隐式下载。托管缓存验证后发布不可变快照，整组分页完成后切换，关闭等待旧Renderer、请求及文件线程。

最终运行以下命令，全部exit0：

```sh
uv run --locked python scripts/check_governance.py --all
uv build --all-packages
uv run --locked python scripts/smoke_wheels.py
uv run --locked python scripts/smoke_plugin_distributions.py --candidate dist/plugin-distributions/managed-assets-a8-a5-v2 --wheels dist
git diff --check
```

统一入口1608测试通过（223.17秒），Ruff格式/lint通过，mypy82源文件通过；总覆盖93.03%，治理工具96%、Core93%、Assets92%，三组80%门槛通过。五包独立wheel安装/导入与双端SDK-free隔离分发通过；分发测试使用合成公共素材HTTP响应，Provider请求禁用，验证首次后台准备、空Token、重复启动、状态、持久化和关闭。专项还覆盖UI失败后partial/续作、404与其他错误、冷却、进程锁、崩溃恢复、取消及旧Renderer清理等待。

本地候选目录为dist/plugin-distributions/managed-assets-a8-a5-v2，非商店已发布版本。每个宿主固定Core/Renderer/Assets/自身适配器四个Release URL和SHA256；未回退裸PyPI包名。候选与wheel版本、摘要及检查结果保存在[离线摘要](offline-verification.json)，完整文件和源码摘要保存在候选manifest.json；ignored dist目录可按发布指南重建。没有覆盖公开a7同版本wheel。

## 真实公共素材下载

在用户授权的AstrBot Linux容器内建立独立临时库和素材根，使用专用无玩家认证客户端、默认并发/期限/预算直接下载真实公共源，不修改生产配置、数据库或插件，不重启服务或发送聊天。

54.3秒处理686项：127英雄、415装备、9段位、5星级及1金币，共557张可用PNG；129装备返回HTTP404，单独标记missing，无其他下载失败。素材总字节22,880,181；关闭释放租约，重开验证完整快照并在禁止新HTTP的factory下ensure返回空任务。

既有Core/Renderer a4对新隔离快照成功生成780×728、82,701字节的合成战绩卡；hero_id 2/16/26/58/92/131均可解码为256×144，包含用户截图对应英雄。未保存真实玩家战绩或游戏PNG至Git。

两端SDK-free Runtime在同一Linux容器、独立素材根中复用完整快照，空Token保持awaiting_config且assets=ready；重复start/close与关闭释放租约通过。此检查不等同实际宿主注册、真实首次Runtime联网或聊天验收。运行探针对应构建时的候选；随后旧Renderer取消等待边界的补充修正以最终离线测试/重建候选验证。

[真实验证JSON](live-verification.json)不含服务器地址、凭据、身份或生产路径。服务器与容器临时验证目录已清理。

## 待评审与联调

第五包的policy/schema/checker独立边界与覆盖率配置需维护者评审；保留原门槛并新增Assets80%，未获得评审或发布批准。候选未提交外部发布，生产仍沿用既有插件/素材配置。

实际注册宿主的首次自动下载、热重载/关闭、真实聊天及商店新版本索引尚未联调。UI网络失败与增量恢复已离线验证，尚未在真实网络故障下注入验证。自动服务不生成装饰背景、不做HTTP字节续传或周期全量更新；来源404继续使用占位。
