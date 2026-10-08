# Dota2UID a6 发行与部署证据

用户于2026-10-08授权整理发布部署。[发行任务](../../tasks/done/2026-10-08-dota2uid-bundled-release.md)、[实现验收](../dota2uid-bundled-bootstrap-v1/README.md)。

已公开 [a6 Release](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a6)，main/tag为db1237042b9366298c176873342d97f3c590fee6；发行源码f585ed310d6dd444c9046fba9fb8313ffc90c193，[源码PR #7](https://github.com/HBLADEH/Dota2Forge/pull/7)保留治理维护者评审。Core/Renderer a4与旧资产相同，旧a4七资产未改，未发布AstrBot a8。

最终ZIP15,690,004字节，SHA256 21bd7f8960d38ae3500e474a8fbfb3f2abbe398ad6549fc0cff6e0aeba326e7b。[最终审查](release-final-review.json)验证17文件、四wheel、MIT/OFL、109来源摘要与重生成一致；[资产清单](release-assets.json)和[匿名验证](public-assets-validation.json)覆盖11个Release资产、main/tag及17个公开文件。匿名下载使用无认证系统代理，初始直连失败单列为路由尝试，未使用账号Token。

[公开恢复](public-validation.json)覆盖无项目/SDK包的新venv、真实管理恢复与冷启动；实际Windows SDK副本验证公开恢复、生命周期关闭及原生URL+tag安装，四模块来自私有代际。实际SDK使用既有测试解释器，不冒充全新SDK环境。原SDK与Pillow原生文件摘要不变。

[部署](remote-deployment.json)将现行Linux/Docker gscore从a4薄分发换为a6，私有备份位于记录中的服务器backups目录。原Dota2UID数据不存在；首次生成空Token配置及素材目录，未覆盖用户数据。[检查](remote-postflight.json)确认17分发SHA、91条私有文件完整清单、MIT/OFL及四版本，全局项目包仍未安装，HTTPX0.28.1/Pillow11.3未变；SDK7f1bee79源码前后摘要相同。[启动证据](remote-startup.json)为awaiting_config、无安装错误，管理接口匿名401。

第一次SSH直接替换受容器文件属主阻止，旧实例已恢复；最终使用同一现有镜像的断网临时维护进程，仅备份/轮换专用插件目录并保留原属主。没有修改GsCore逻辑、其它插件/容器、凭据或路由；原定时更新开关保留，SDK版本并非永久冻结。

最终[统一禁网检查](offline-checks.log)1766 passed /265.77s，Ruff351文件、mypy83文件；总覆盖92.99%，scripts94%/Core93%/Assets92%。Linux CI Python3.12/3.13通过；五包构建、新venv wheel与双端分发smoke通过。发行审查发现并修复跨平台锁类型检查与[Windows确定性路径竞争](windows-path-race-diagnosis.json)，未放宽守卫或门槛。

真实QQ新命令、已登录管理API、跨schema回退及其它SDK版本未验收；生产配置尚无STRATZ Token，不声称业务ready。未发送真实消息，商店索引仍待审核。

[商店PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)安装提示已同步a6随包/主人状态恢复入口，避免新分发调用已删除的旧安装器；fork提交3c02296。仅修改Dota2UID的installMsg，所有其它索引元数据深比较不变，PR保持OPEN待审核。
