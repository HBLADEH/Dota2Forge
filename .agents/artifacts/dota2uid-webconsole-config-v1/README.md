# Dota2UID 后台配置隔离 SDK 验证

2026-10-09，本地 a7 v3 候选在真实 GsCore SDK 源码隔离副本通过四阶段功能与隐私验证：[机器记录](native-sdk-validation.json)固定候选逐文件 SHA256 与结果。本次隔离验证没有发布、生产部署、真实 STRATZ 请求或聊天平台连接；尚未验收生产后台浏览器点击。

## 环境与方法

SDK checkout 为 `87c06f11ae10c12b3bb8e76b3c6f420c831282a8`，发行元数据 gsuid-core 0.11.0；解释器 CPython 3.13.2，Pillow 11.3.0。源码复制到系统临时目录，排除真实 data、plugins、配置与环境文件；使用既有隔离 SDK 解释器，不能描述为全新 SDK 环境。原 SDK 的 639 个 Python 文件与 Pillow 原生文件摘要前后相同，没有宿主 pip 操作。

验证调用真实发现器、StringConfig、FastAPI 参数配置 GET/POST、session_store、权限依赖、停用接口、原生 reload 与生命周期。会话由 SDK session_store 创建合成管理员和普通用户 fixture，不替换认证依赖或 SDK 类方法；Dota2UID 的配置对象保存入口使用插件校验包装并委托原生写入。外部 socket 与 DNS 被阻断。账号绑定输出只收集内存 WebSocket frame，使用合成身份，不代表真实 QQ 递送。

## 通过结果

- 项目运行库加载前注册 11 个参数；删除随包 wheel 后仍可取得配置。Token 标记 `secret`，配置归属 Dota2UID。
- 实际 API 拒绝匿名和普通用户保存、读取；敏感 GET 拒绝 query Token。非法类型、超限数值与非法平台映射保存失败且 JSON 字节不变。
- 空 Token 启动为 awaiting_config；后台保存后原 Runtime 保持等待。实际停用后原生重载读取新值并达到 ready/text；第二轮重载仍只有一个配置组。
- 合法 TOML 的合成 Token、命名空间、回复方式和超时值首次写入原生 JSON，旧 TOML 字节保持。随后 JSON 为主，新进程读取它而不重新使用旧 TOML 的空 Token。
- 掩码 Token 回传保留旧值；合成账号绑定在重载及新进程中保留；SDK 关闭完成且无订阅调度任务残留。
- Flush 原生 HTTPTrace 写队列后，所有 SDK 日志和 HTTPTrace 归档均无合成 Token。无关 API 的响应和工作日志 canary 仍能在归档中找到；冷启动和已有 ASGI stack 的热安装均通过，重载后参数接口仍受保护。

`secret` 是前端视觉隐藏：管理员 API 与配置文件仍含明文，未声称加密存储。v1 中间候选的 stdout/stderr 未见合成 Token，但补查 HTTPTrace 归档发现泄漏：原生参数 GET 的 `value/default` 没有被 SDK 脱敏。最终候选使用插件所属路径的 ASGI ConfigTraceGate 跳过响应正文追踪；原生接口、鉴权、响应及其他路径的追踪继续执行。最终验收扫描全部归档并保留无关路径 canary，不再只核对 stdout/stderr。

## 现行日志中间件兼容范围

[独立类验证](trace-class-validation.json)加载现行 `7f1bee79e66cb8c1b8e07cce15631021920193dd` 与 `87c06f11ae10c12b3bb8e76b3c6f420c831282a8` 的真实 HttpTraceMiddleware 源码。两个文件 SHA256 相同；使用合成路由、鉴权及 stub collector，复现未保护时的响应凭据预览，并验证冷启动/已有 stack 的路径保护、401、GZip、其他路径追踪和 SDK 类方法不变。该记录没有导入现行完整 SDK 应用，也没有验证其原生归档落盘；应与前述 `87c` 整体 SDK 的真实鉴权、生命周期和归档验证分别解读。
