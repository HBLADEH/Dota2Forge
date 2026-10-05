# 商店发行准备第一阶段

Status: done

## 目标
按用户授权逐步落实分发建议，先生成双端可审查的本地发行产物，补首次配置状态与依赖版本检查，为后续发布和真实商店验收准备条件。

## 非目标
本阶段不发布PyPI/远程仓库、不提交商店申请、不操作现有宿主或发送消息；不改变policy、CI及治理脚本，不把桩或本地wheel安装当作真实商店通过。

## 验收
- [x] 保留已有工作区；四包使用0.1.0a2，锁文件和生成参考一致。
- [x] 确定性生成两端根发现目录、依赖清单、许可、配置说明和校验清单；失败不覆盖现有产物。
- [x] 生成桥接在SDK/运行库导入前核对Python及锁定版本，不接受旧库；GsCore清单覆盖指定库升级。
- [x] 两端合法空Token为awaiting_config；GsCore首次创建完整空配置且保留已有文件；非法配置仍failed。
- [x] 禁网测试覆盖生成、旧库拒绝、配置恢复与双端消费；统一门禁、四包构建和干净清单安装通过。
- [x] 同步文档与实施决策，交付本地产物和下一阶段真实安装/发布待办。

## 影响模块与决策
[分发建议](../../notes/proposed/2026-10-05-plugin-store-readiness.md)、[实施决策](../../notes/implemented/2026-10-05-plugin-distribution-stage1.md)、[商店核查](../../../docs/subsystems/plugin-distribution.md)、双端适配器、包配置、发行脚本和测试。保持Core/Renderer无宿主SDK边界。

## 验证证据
开始时大量未提交源码/文档/资源变更保留；policy、CI和治理脚本未修改。产物位于本机`dist/plugin-distributions/0.1.0a2`，AstrBot ZIP 6960 bytes，GsCore ZIP 5497 bytes，GsCore索引条目为草稿。输入/输出及四包SHA256见[证据](../../artifacts/plugin-distribution-stage1-v1/README.md)。

统一入口`uv run --offline --locked python scripts/check_governance.py --all`最终退出0：治理、Ruff、mypy71文件、1372项禁网测试通过；综合覆盖率93.28%，scripts96%/Core93%独立门槛通过。四包`uv build --offline --all-packages`及SDK缺失隔离wheel验证通过。

候选清单在两个新venv中offline/no-index/no-cache安装通过；版本、空配置等待、新实例恢复、账号123绑定持久化和关闭通过。首次验证残留两份字节码触发重复生成失败；修为-B，仅清理本任务缓存后两端验证/原样重建通过。失败记录未掩盖；生成器拒绝覆盖契约保持。

## 阻塞与下一步
本阶段完成本地候选及首配闭环。尚未公开运行包/分发仓库、更新真实宿主或提交商店。下一阶段确认公开依赖取得及拟支持宿主的干净安装；再验收真实a1→a2升级、关闭/重载/冷启动、卸载/数据保留、Windows/Linux和新命令图片/权限聊天场景。订阅真实推送仍待原任务验收。上述通过后再提交GsCore索引PR和AstrBot Cloud申请。
