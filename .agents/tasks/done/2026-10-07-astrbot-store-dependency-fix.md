# AstrBot 商店依赖安装修复

Status: done

## 目标
修复商店缺包分发清单，使用固定SHA256的Release wheel直链；接续用户授权的SSH部署诊断，安装缺失运行包并验证加载。

## 非目标
不把包发布到PyPI，不修改Core/Renderer逻辑，不触碰无关服务或商店外的GsCore流程，不发送真实聊天。

## 验收
- [x] AstrBot requirements 使用公开 Release URL 和 hash，第三方依赖保持版本约束。
- [x] 构建、离线测试、双端隔离安装通过，公开 a7 资产摘要一致。
- [x] 用完整日志确认错误原因，GitHub a7已公开。
- [x] 用户确认商店显示0.1.0-alpha.7。
- [x] 容器实际下载alpha.7。
- [x] 部署环境恢复下载，安装缺失组件并验证真实宿主加载。

## 影响模块与决策
[分发生成器](../../../scripts/build_plugin_distributions.py)、[隔离 smoke](../../../scripts/smoke_plugin_distributions.py)、AstrBot分发仓库和安装文档；[修复决策](../../notes/implemented/2026-10-07-astrbot-store-dependency-fix.md)。

## 验证证据
用户完整日志确认Cloud下载alpha.6缓存ZIP，阿里云pip源返回astrbot-plugin-dota2forge==0.1.0a6无匹配版本；三个PyPI JSON接口404。a7已生成/公开，requirements改为GitHub Release wheel URL+SHA256；分发主分支提交1ce602c。Cloud旧ZIP不会随GitHub主分支更新。

统一离线检查1537项通过（201.62秒），Ruff/mypy73文件通过，治理工具96%、Core93%。四包构建/独立wheel导入、双端禁网安装/首配/关闭/绑定保留通过。离线URL映射保留摘要，缺失/篡改/清单漂移回归验证通过。

全新CPython3.12.9环境直接pip安装公开requirements成功，pip check无冲突，三个项目版本核验通过；不依赖workspace或手动预装项目包。7个a7资产匿名下载及公开requirements与已发布候选摘要一致；[证据](../../artifacts/astrbot-store-dependency-fix-v1/README.md)。已发布a7文件保留，不覆盖发行资产。

用户授权SSH诊断的Linux Docker实际为Python3.12.13、AstrBot源码4.28.1。当前GitHub首页/Release HEAD恢复可达，使用原a7 requirements和宿主57条Core约束安装成功（7.21秒），仅新增三个项目包；原198包版本全保留，pip check通过，wheel摘要匹配。真实SDK导入与AstrBot容器冷启动成功，日志明确initialized state=awaiting_config；WebUI HTTP200，空Token配置自动生成。[部署证据](../../artifacts/astrbot-store-dependency-fix-v1/remote-install.json)不含凭据、身份或聊天。

## 阻塞与下一步
当前安装/加载问题已解除；用户需在WebUI本机填写stratz_token、保存并重载后使用。未发送真实聊天、查询Provider或验收图片/订阅；未修改代理/网络设置，未来GitHub可达性仍依赖部署网络。运行包安装在容器层，重建容器需重新按清单安装。Cloud ZIP下载和SSH下同清单pip安装已验证，但商店按钮完整重试未另行执行。主仓修复/文档仍留在工作区，未在本轮提交或发布。
