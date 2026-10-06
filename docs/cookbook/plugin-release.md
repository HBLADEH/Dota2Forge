# 本地插件发行候选准备

已实现四包0.1.0a3、双端薄桥接分发、版本检查、首次配置和隔离安装。GsCore已公开GitHub Releases运行包，通过固定隔离SDK验收并提交索引PR #40，见[执行记录](gscore-store-publish.md)；AstrBot尚未公开发布。[初始核查](gscore-store-readiness.md)与[阶段一任务](../../.agents/tasks/done/2026-10-05-plugin-distribution-stage1.md)保留历史边界。

## 生成与审查

按[开发指南](development.md)安装锁定workspace后运行统一离线检查与四包构建。发行生成器读取包配置/宿主模板，不导入或启动宿主：

```powershell
uv run --locked python scripts/build_plugin_distributions.py --output dist/plugin-distributions/0.1.0a3-public-runtime-v1 --astrbot-repo https://github.com/HBLADEH/astrbot_plugin_dota2forge --gscore-repo https://github.com/HBLADEH/Dota2UID --gscore-wheels .tmp/gscore-store-release-a3-wheels
```

两URL是本候选目标，尚未由此命令创建或同步远端。生成结果：

公开GsCore模式另传--gscore-wheels .tmp/gscore-store-release-a3-wheels，并使用新的输出目录，例如0.1.0a3-public-runtime-v1。读取三个已审查wheel元数据和SHA256，生成install_runtime.py/runtime-wheels.json/INSTALL.md；wheel本身上传GitHub Releases，不塞入桥接ZIP。根README的操作链接转为本地INSTALL.md；步骤见[公开安装](gscore-public-install.md)。原包名模式不附此安装器，继续要求其索引依赖可取得。

插件README从两个适配器说明生成，注入当次版本与目标仓库；主仓文档链接转为完整URL，MIT许可保留本地链接。共享[主宰图标](../assets/branding/juggernaut-icon-v1.png)分别为GsCore根ICON.png与AstrBot根logo.png；GsCore索引avatar/cover指向目标main的ICON.png，远端未同步时尚不可用。已审查截图按白名单复制到对应根screenshots/，README图片路径转为本地，源图/目标均纳入摘要和ZIP大小检查，缺图在输出前失败。当前双端共用AstrBot主宰出装卡，GsCore说明标明原宿主，[其余待补](plugin-showcase.md)；原始聊天图片不自动收录。

```text
dist/plugin-distributions/0.1.0a3-public-runtime-v1/
  astrbot_plugin_dota2forge/  # main.py、metadata、Schema、requirements、许可、README、logo.png
    screenshots/hero-items.png # 已审查AstrBot实机图
  Dota2UID/                 # __init__.py、宿主pyproject、配置示例、许可、README、ICON.png
    screenshots/hero-items.png # 共用上述AstrBot原图
  astrbot_plugin_dota2forge.zip
  Dota2UID.zip
  gscore-index-entry.json   # 仅新增条目/分类的草稿，不能覆盖完整官方索引
  manifest.json            # 输入来源与产物SHA256、本地候选状态
```

两个根目录均含release.json和标准库版本检查；它们锁定该次Core、Renderer与对应适配器的确切版本。生成器保留宿主兼容声明，替换目标repo/author/version；第三方HTTPX/Pillow约束取自四包元数据，消费者约束漂移会失败。

ZIP条目顺序、时间戳和权限固定；相同输入字节重复生成一致。输出完整暂存后才就位，已有目录只接受完全相同内容；改变、缺项或额外文件会失败并保留原目录。检查manifest后再同步分发仓库。薄桥接ZIP须通过16,000,000 bytes保守上限，不携带字体、Pillow、独立美术素材包或本机配置；运行资源由Renderer wheel提供。实机截图中的第三方画面权利见[截图来源](../assets/screenshots/README.md)，不因加入说明转为MIT美术。

## 配置与升级边界

GsCore首次Runtime启动使用独占创建写入空的data/Dota2UID/config.toml，不覆盖已有文件。两端合法配置但空Token为awaiting_config；不创建HTTP客户端、绑定/订阅库或后台业务任务，命令给出本机配置位置。非法配置仍failed，不能作为空Token接受。

填写Token并确认独立namespace后重载：GsCore先显式停用；AstrBot保存配置后重载。旧实例关闭，新实例重新读取配置并ready；现有实例不轮询凭据文件。配置/身份/订阅语义继续遵守双端[GsCore](dota2uid.md)/[AstrBot](astrbot.md)指南。

GsCore清单同时生成project.dependencies和gscore_auto_update_dep，后者让三个指定库检查升级约束；仍需宿主至少一个自动依赖总开关开启。当前GsCore87c06f1冷启动执行依赖队列，商店热重载只收集而未执行，缺包会被入口拒绝；[隔离复核](gscore-store-readiness.md)已确认该路径问题，需处理并验收。生成入口在任何SDK或运行库导入前拒绝Python<3.12、缺包和三个项目库版本不匹配，不代替停机/冷启动。手动桥接安装器不附带商店guard。

共享库升级先停用并退出宿主，再安装新包、更新桥接和冷启动；Pillow升级需避免Windows DLL占用。版本元数据不证明旧进程导入缓存已更新。a3公开升级、SDK原生卸载及配置/绑定/订阅库保留已隔离验证；跨schema回退与真实商店界面仍待验收。

## 本地隔离安装

先构建四包，将锁定版本的HTTPX及其依赖、对应解释器/平台的Pillow wheel显式下载到dist。下载属于安装准备，可联网；普通测试与下面检查仅用本地wheel，不查索引。依赖版本以uv.lock为准；缺wheel明确失败。

```powershell
uv build --all-packages
uv run --locked python scripts/smoke_wheels.py
uv run --locked python scripts/smoke_plugin_distributions.py --candidate dist/plugin-distributions/0.1.0a3-public-runtime-v1 --wheels dist
```

后者先核对产物摘要，为两端分别创建无项目包的新venv，使用生成清单安装，命令固定offline/no-index/no-cache。独立进程以-I/-B执行版本检查、空Token首配、配置后新实例就绪、绑定/关闭/重启保留，不在候选中写字节码；HTTPX使用拒绝所有请求的合成transport，不读真实Token或发送聊天。

这一检查没有宿主SDK，不等同商店真实安装、公开下载可达、Linux/所有解释器兼容或实际权限/图片上传验收。GsCore公开包/入口、固定SDK组件与升级/卸载已验收，索引PR #40待审核；QQ/真实商店界面与AstrBot Cloud申请分别接续。CI与发布流水线变更单独交维护者评审。
