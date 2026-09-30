# 工程治理运行契约

## 自动执行

[policy](../../.agents/policy.json) 由严格 JSON Schema 校验：未知字段、未知版本、非法或不存在的包路径会失败。路径必须覆盖 workspace 全部包。Schema 和 policy 自身属于需要维护者评审的工程代码。

字符数按 Unicode 非空白字符计算，根 AGENTS.md 同时限制行数。检查普通 Markdown 行内链接、引用式链接定义和 Markdown 标题锚点；跳过代码示例与外部 URL。未覆盖 HTML 链接、自定义显式锚点和任意 Markdown 扩展语法。原始规划不参与事实文档预算。

架构检查从 pyproject.toml 读取分发名和导入路径，禁止 Core 引用平台、禁止两适配器互相依赖或引用对方宿主。覆盖静态 import、常量 `__import__` / `importlib.import_module`（含常用别名）以及运行、可选、开发和构建依赖声明。计算拼接的动态导入、传递依赖、运行时对象跨层和重复业务逻辑需评审兜底。领域层内部边界在业务结构形成后补充规则。

决策记录验证目录状态、日期文件名、分类、章节和三个关联链接。`--all` 要求存在 implemented 决策；`--base` 对敏感路径改动额外要求改动一份 implemented 决策。敏感路径检查偏保守；检查器不能判断记录是否充分解释了变更。非平凡改动与记录的语义关联由评审负责。

包参考从 TOML 生成，不执行应用模块导入。AstrBot 的配置、命令和 AI Tool 注册表仍未实现；Dota2UID 的宿主入口和命令属于适配器实现，不在包参考表中重复列出。

Ruff、mypy、pytest 均为必需检查。pytest 禁网并采集治理工具、Core 和 Dota2UID 的语句/分支覆盖率；聚合门槛 80%，policy 保持治理工具与 Core 两个独立 80% 报告。Dota2UID 独立覆盖率另按 [操作步骤](../cookbook/dota2uid.md) 核验。缺少工具、无数据或非零退出不能忽略。Dota2UID 已有消费者与离线宿主桩测试，AstrBot 仍为骨架；真实进程加载/生命周期另列任务证据，不由骨架 wheel 测试代替。

## CI 与托管控制

GitHub Actions 的 `offline` job 使用 Python 3.12 和 3.13，运行锁定依赖安装、统一检查、构建与干净环境 wheel 导入。拉取请求使用真实目标分支 SHA 计算影响范围。工作流无发布动作，仅请求读取仓库权限。

公开仓库为 [HBLADEH/Dota2Forge](https://github.com/HBLADEH/Dota2Forge)，默认分支为 main。M0 初始提交的 [GitHub CI](https://github.com/HBLADEH/Dota2Forge/actions/runs/36615343368) 已通过 Python 3.12 / 3.13 检查、构建与 wheel 安装验证。分支保护尚未配置，维护者仍需实际配置并验证：

1. 默认分支要求 PR 合并，禁止直接推送及强推。
2. 将 `offline (3.12)`、`offline (3.13)` 设置为必需检查。
3. 至少一名维护者审批并驳回过期审批。
4. 配置真实维护者为 policy、schema、scripts、workflow 的 CODEOWNERS，并要求其审批。
5. 启用可用的 Secret scanning / Push protection，验证权限与套餐支持。

当前没有自动凭据扫描器、语义化变更分类、消息快照、运行时日志留存或平台生命周期门禁；密钥禁止入库属于协作规则，不能宣称已有完整自动保护。

操作见 [开发指南](../cookbook/development.md)。
