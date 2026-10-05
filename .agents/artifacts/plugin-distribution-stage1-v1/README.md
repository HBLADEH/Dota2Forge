# 商店发行准备第一阶段证据

2026-10-05，本地候选0.1.0a2。沿用已有未提交工作区，未改变其他任务的实现，未操作宿主、远程仓库、公开包索引或商店。

## 产物

[摘要](verification.json)记录四包sdist/wheel与两个桥接ZIP的大小/SHA256；[候选清单](manifest.json)保留源码输入和输出摘要。[GsCore条目](gscore-index-entry.json)仅为新增条目/分类草稿，不能替换完整官方索引。两个GitHub URL是计划目标，尚未由本任务创建或同步。

本机候选位于`dist/plugin-distributions/0.1.0a2`，四包构建产物位于`dist`；不将这些被忽略的本机文件作为文档链接。AstrBot ZIP 6960 bytes，GsCore ZIP 5497 bytes。桥接不携带业务源码、字体、第三方二进制、Valve美术、真实Token或本机配置；Renderer wheel为13,725,493 bytes并含字体/OFL。

## 验证

统一入口为`uv run --offline --locked python scripts/check_governance.py --all`。[首次门禁尾段](first-gate-tail.log)为1372项禁网测试通过、综合覆盖率93.28%、scripts 96%/Core 93%；mypy71文件通过。[完整最终门禁](offline-checks.log)覆盖缓存修正后的源码，最终状态见摘要。

`uv build --offline --all-packages`成功；`scripts/smoke_wheels.py`四包在干净无SDK环境安装/导入和资源出图成功。`scripts/smoke_plugin_distributions.py`实际使用候选清单，为两个插件分别在新venv固定offline/no-index/no-cache安装：三个项目包确切a2、Pillow12.3.0、HTTPX0.28.1及其依赖。以-I/-B启动的子进程验证缺Token等待、无客户端、填写配置后新实例ready、绑定保存、关闭及新实例恢复账号123，MockTransport拒绝全部HTTP请求。

首次隔离验证遗留两个bootstrap字节码文件，重复生成按契约拒绝额外文件；修正为-B，仅清理本任务生成的两份缓存，复验安装和重复生成成功，源码/产物内容未变。SDK桩覆盖生成入口的命令注册、权限、图片发送及关闭；缺包/a1/Python低版本均在SDK导入前拒绝。

## 边界与接续

无宿主SDK的隔离检查不证明商店能取得依赖或真实宿主兼容。没有进行真实a1→a2升级、卸载/schema回退、跨平台安装或聊天联调。公开运行包、分发仓库同步、拟支持宿主的干净安装/升级验收完成后，再处理商店申请；订阅真实推送仍属其他任务。

步骤见[发行指南](../../../docs/cookbook/plugin-release.md)，实施验收见[任务](../../tasks/done/2026-10-05-plugin-distribution-stage1.md)。
