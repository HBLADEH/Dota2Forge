# Dota2UID 后台配置验收与发行

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

## 公开发行与离线检查

[a7 Release](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a7) 已公开，分发 main/tag 为 `dd57b64b37b9f9e2cb98b561c62640bc6ddd154c`，发行源码为 `3a2f6d0c8c3739d7a8da38cc4e116dc94d327023`。最终随包代码与四个 wheel 逐字节等于上述 SDK v3 候选；仅 README/INSTALL 固定源码链接并对齐验收文案，不能将两份文档旧 SHA 与最终发行 SHA 混同。

[发行清单](release-assets.json)与[摘要](SHA256SUMS)对应 9 个载荷，3 个共享组件的 wheel/sdist 保留 a6 已公开字节，没有替换以前的 Release。最后统一禁网检查 **1930 通过 / 274.38s**，Ruff359、mypy83，总覆盖93.01%，scripts94/Core93/Assets92；五包构建与最终 v3 wheel/双端分发 smoke 通过。发行源码的 [Linux CI](https://github.com/HBLADEH/Dota2Forge/actions/runs/37823879846) 和 [PR CI](https://github.com/HBLADEH/Dota2Forge/actions/runs/37823886687) 均在 Python3.12/3.13 成功。

[匿名公开验收](public-validation.json)验证仓库18文件及11资产真实下载、API摘要、size、9载荷 checksum、ZIP完整树和4wheel元数据一致。全新 CPython3.12.9 只安装 HTTPX0.28.1/Pillow12.3.0及6个传递依赖，真实随包后端完成本地准备、缺wheel的4条固定URL恢复、冷启动指针复用、4个私有包导入、OFL与菜单绘制。第三方232个源码/原生文件摘要未变，无TOML loader 的空Token等待→显式关闭→新实例ready通过；没有 SDK、真实 Provider 或聊天连接。

## 生产部署与宿主自更新

[部署记录](deployment.json)保留私有备份 `/srv/data/services/bot-stack/backups/dota2uid-a7-20261008T184023Z`。仅更新 Dota2UID；从固定tag克隆、验证main与18文件后，停机备份插件、专用数据与所属服务JSON，使用缓存镜像/禁网维护容器轮换并保留owner，冷启动通过，无回滚。首次验收SDK7f/0.11.0、HTTPX0.28.1、Pillow11.3及其原生摘要保持，部署没有SDK改写或全局pip操作。

后续复核发现原基线发生漂移：[失败记录](production-drift-postflight.json)保持 `passed=false`，未修改原门禁。原有[定时维护](host-auto-update.json)启用了Core03:40更新、Plugins04:10更新、Core04:40重启；部署后已有日志包含自动更新与依赖安装，现行容器于UTC20:40启动，对应北京时间04:40。SDK前进至 `fb80b874533c23b565a74ebd8549ce09e4742a55`/0.11.1、Pillow12.3.0；这些设置未由部署修改，没有自行回退SDK或关闭维护。

[当前宿主审计](current-host-validation.json)另立精确fb提交/全源码摘要及当前依赖/26个Pillow原生文件摘要判定。11关键模块字节不变，所消费server/logger函数AST不变，工作树符合HEAD；a7的18文件、11参数密码标志、旧TOML摘要、四私有包完整清单及匿名HTTP200/401仍通过。[启动证据](production-startup.json)只输出已知状态，观察到awaiting_config且无已知插件错误码，不输出原始日志或身份。原生Token仍为空，无认证生产API会话；后台真实点击、有效Token查询及QQ递送仍待验收。

## 新SDK源码补验与商店

[fb源码补验](current-sdk-validation.json)使用公开新SDK源码的隔离副本和最终公开候选，验证原生11参数、真实session_store权限401/403、保存快照、停用API/原生重载ready、单配置组、完整归档无合成Token、其他API及工作日志canary、四私有包和shutdown。解释器仍为CPython3.13.2，已装SDK元数据0.11.0/Pillow11.3；继承Pillow低于新SDK声明>=12，该smoke只验证配置/追踪消费接口，不能描述为生产0.11.1/Pillow12.3的同构全环境验证。生产12.3符合SDK下限及Dota2Forge的>=11.3,<13范围，公开后端另有12.3验证；原SDK639源码/Pillow摘要保持。

[商店PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)保持OPEN；[索引核验](store-validation.json)只修改installMsg，提交 `2befe5b7785419e98f6d5f2aa8d498fa9d1cfdbf`，其余索引字段深比较不变。[源码PR #7](https://github.com/HBLADEH/Dota2Forge/pull/7)保持OPEN，先前治理规则仍需维护者评审；未合并、未发送评论。
