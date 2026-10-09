# Dota2UID bundled 受控热切换实施

Status: done

## 目标
按已授权[调研方案](../../notes/proposed/2026-10-09-dota2uid-hot-update.md)实施：具备交接协议的 bundled 版本更新后，原生重载关闭并排空旧任务，启用整组新项目运行库，不重启其他插件。

## 非目标
公开发布、生产部署、修改 GsCore SDK、共享第三方热升级，以及真实聊天发送。旧 a6–a9 首次升级保留冷启动；不能自动保证任意数据库跨版本回退。

## 验收
- 查询/排队/发送/订阅/绘图/素材及已开始的 SQLite 线程全部排空后才切换；关闭超时保留诊断并要求重启。
- 串行交接、模块来源/独占归属、兼容数据契约、冻结入口与配置、整组加载和失败恢复有禁网正反例。
- 期望/准备/活跃版本分开报告；失败/取消不谎报 ready，不自动重发不确定消息。
- 保留配置/绑定/订阅/素材；薄分发/AstrBot回归；统一离线检查、五包构建与隔离分发验证通过。
- 实际SDK隔离副本验证原生reload与权限/唯一注册；无法执行的Linux/Docker/真实聊天明确列出。

## 影响模块与决策
管理/业务桥接、[Runtime](../../../adapters/Dota2UID/src/Dota2UID/runtime.py)、[运行库后端](../../../scripts/gscore_bundled_runtime.py)、Core SQLite线程取消边界、分发与操作文档。实现决策完成后放入 implemented。

## 验证证据
开工HEAD ec66076，保留先前调研三文件与两个未跟踪商店任务记录。不改生产宿主，不操作真实配置或数据库。

实现完成：Core a7 / Dota2UID a10；lock/reference已同步。最终本地候选`dist/plugin-distributions/a10-hot-update-v10`，含canonical五包匹配wheel，未发布。

真实SDK隔离副本基于公开`fb80b874533c23b565a74ebd8549ce09e4742a55`源码，临时host不含原plugins/data/logs；使用既有Python3.13.2 SDK解释器、元数据0.11.0/Pillow11.3，socket/DNS/UDP阻断。最终a10候选首启awaiting_config；原生参数保存后reload达ready；人工持续中的发送任务阻塞至取消清理释放后，原生reload完成Core a7→合成Core a8 wheel、Renderer a5、Assets a1及Dota2UID a10整组替换；新Core代码canary、Runtime类型和四模块来源校验通过。bindings/subscriptions/config三个文件SHA256保持，SV、生命周期hook、管理员配置、管理API401/403、订阅任务各唯一。损坏wheel更新保留新一代活跃业务并恢复管理注册。SDK 641文件摘要未变；无SDK源码patch、真实聊天、Provider或生产数据。[机器记录](../../artifacts/dota2uid-hot-update-v1/native-sdk-validation.json)。合成下一代只存在临时插件目录；公开a10 canonical wheel未修改，合成Core a8不是发行产物。

`uv build --offline --all-packages`五包成功；`smoke_wheels.py`独立安装五包通过；a10 v10双端SDK-free分发smoke通过，最终README生成回归25 passed。统一门禁完整检查退出0：2009 passed/456.61s；scripts94/Core93/Assets92独立覆盖门槛通过。最后补入状态切换期间旧owner回报和并发/订阅取消回归后，runtime/bridge/sender专项58个断言通过；选择性pytest因全仓覆盖率26%触发既有80%门槛退出1。生成README现已分清公开a9冷启动与a10兼容热切换；生产Linux/Docker、真实商店git更新/UI、QQ递送未验证，Docker daemon连接不可用。

## 阻塞与下一步
公开a6–a9用户先停用并完整冷启动安装a10；此后AutoReloadPlugins或手动宿主reload可以切换满足兼容协议的bundled代际。未知共享消费者、旧协议、schema/第三方变化、数据写入后失败和30秒关闭超时仍要求冷启动。本轮未公开发布/部署，也未改商店索引；Linux/Docker和真实聊天联调留待后续发行/运维授权。
