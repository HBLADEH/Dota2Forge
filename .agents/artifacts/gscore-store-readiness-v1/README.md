# GsCore 商店前置条件核查证据

2026-10-06只读核查0.1.0a2-shared-showcase-v1。[结果与接续](../../../docs/cookbook/gscore-store-readiness.md)区分本地候选、公开分发和实际商店安装；[任务](../../tasks/done/2026-10-06-gscore-store-readiness-audit.md)。

- [public-checks.json](public-checks.json)：当日匿名HTTP状态、固定上游提交、索引摘要与包版本。运行索引200/42条、无Dota2UID，目标仓库/三个项目PyPI接口404；第三方依赖有匹配版本。git ls-remote核实GsCore master为87c06f11ae10c12b3bb8e76b3c6f420c831282a8，文档vp为0b04c492105a1d1e53c66d1727e8dd5deaa62e3e。
- [local-checks.json](local-checks.json)：全部候选来源/输出摘要、入口guard、README本地链接/截图来源、无真实配置/数据库；四包文件匹配当前源码，已有dist wheel与本次重建SHA256一致。
- [build.log](build.log)：uv build --offline --all-packages --out-dir .tmp/gscore-store-readiness-wheels，退出0，四包wheel/sdist构建成功；没有发布包。
- [isolated-install.log](isolated-install.log)：uv run --offline --locked python scripts/smoke_plugin_distributions.py --candidate dist/plugin-distributions/0.1.0a2-shared-showcase-v1 --wheels dist，退出0。两端各自新venv离线安装本地wheel，SDK不存在；HTTP请求全部拒绝。验证版本guard、空Token、配置后ready及绑定重启保留，不代表真实SDK商店安装。
- [hot-install-probe.json](hot-install-probe.json)：提取固定上游源码中的check_pyproject/process_dependencies/flush_pending_installs/reload_plugin函数，配合真实候选guard，在开启自动依赖安装但缺三个项目库时执行热重载。收集依赖而未执行安装，guard拒绝；显式flush对照通过。探针退出0；注册表/路径组合/安装器效果合成，网络禁用，没有修改宿主或执行真实下载。
- [offline-checks.log](offline-checks.log)：uv run --offline --locked python scripts/check_governance.py --all退出0，275文件格式、Ruff、mypy71文件、1377禁网测试（168.20s），治理工具96%/Core93%覆盖率。归档后的[文档/仓库治理复核](final-document-checks.log)单独记录。

本机手动安装升级/SDK隔离渲染证据沿用[部署记录](../gscore-current-deployment-v1/README.md)，截图来源沿用[共享截图记录](../shared-plugin-screenshot-v1/README.md)。未验证公开依赖下载、实际商店新装/更新/卸载、当前GsCore聊天或新增平台支持。
