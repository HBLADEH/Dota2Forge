# GsCore 公开分发与商店收录执行

Status: done

## 目标
按用户授权顺序公开Dota2UID分发/匹配运行包，处理安装路径，完成实际隔离SDK验收后提交索引PR。用户选择QQ命令后续自行测试。

## 非目标
不提交AstrBot商店申请，不部署a3到生产，不切换路由或发送QQ，不把合成Provider/帧采集当真实聊天。保留原工作区修改、旧公开资产/tag；不变更治理/CI门禁。

## 验收
- [x] 独立public/main根仓库与固定a3运行包公开，12文件及七资产匿名取得、SHA256匹配。
- [x] 明确热安装依赖队列限制，提供公开CLI/停机/冷启动；干净实际SDK公开安装及配置恢复通过。
- [x] 实际SDK代表性PNG/文字、失败/权限、调度及关闭；公开a2→a3修复升级、冷加载恢复、原生卸载及数据保留通过。
- [x] 提交vp索引[PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)，已附加当前任务，未合并。
- [x] 文档/note/生成参考同步，统一离线检查与四包构建、双端隔离安装通过。

## 影响模块与决策
[执行记录](../../../docs/cookbook/gscore-store-publish.md)、[公开安装](../../../docs/cookbook/gscore-public-install.md)、[分发契约](../../../docs/subsystems/plugin-distribution.md)、[发行生成器](../../../scripts/build_plugin_distributions.py)、[公共安装器](../../../scripts/gscore_public_runtime.py)；[已验证发行决策](../../notes/implemented/2026-10-06-gscore-public-release.md)。

## 验证证据
[0.1.0a3公开发行](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a3)包含三wheel/三sdist/薄桥接ZIP，无实际配置、数据库、缓存或另一端适配器。PyPI未认证，采用GitHub Releases；PyPI三个项目仍404。

a2公开安装发现fastembed0.7.4/Pillow冲突，未以pip退出0通过；a3支持Pillow>=11.3,<13，CLI保留其他宿主包有效Pillow约束，安装后pip check。原a2资产/tag不动。Pillow11.3下424测试通过；统一uv run --offline --locked python scripts/check_governance.py --all退出0，1398 passed，Ruff/mypy及两覆盖率门槛通过；四包构建与双端无SDK隔离安装通过，[证据目录](../../artifacts/gscore-store-release-v1/README.md)。

实际SDK固定87c06f1/0.11.0、Windows/Python3.13.2；从锁定SDK恢复无项目库环境，公开安装a3/Pillow11.3成功。首次awaiting_config无客户端/任务，填写合成配置后SDK重载ready；原生Trigger/SV/Bot、管理拒绝、PNG/文字/超时、任务/关闭通过。公开a2→a3修复、冷加载绑定恢复、原生卸载、新进程不再发现均通过；配置及两库SHA256完全不变。SDK源码与函数未改，Provider/出站边界为合成HTTP/内存采集，未启动HTTP/WS监听或发送真实消息。

索引只改docs/public/plugin_list.json，+17/-1，原42插件不变；目标vp，提交8e865205510fc9e37b3ef26b68d6b80d3f8e563b，PR OPEN/MERGEABLE。

## 接续边界
等待维护者审核与合并；真实商店界面安装、QQ现行命令由用户后续验收，订阅真实推送、Linux/其他宿主仍未验证。直接热安装缺包未修上游，需指南CLI/冷启动。生产维持a2及现有AstrBot独立开启/GsCore桥接关闭。本任务完成明确授权的提交范围，不代表已上架或QQ验证完成。
