# 自动素材下载设计验证

2026-10-07用户要求检查自动下载能力并设计功能。现有scripts/download_dota_assets.py为显式手工工具；两端Runtime仅注入本地illustration_path，没有素材任务或管理命令。设计读取实际配置、下载器、权限/生命周期和分发清单，不访问服务器或发送聊天。

[提案](../../notes/proposed/2026-10-07-managed-illustration-download.md)保持proposed，覆盖两端默认auto、独立共享素材服务、后台ensure、管理员管理入口、partial恢复及受控快照切换。[实施任务](../../tasks/active/2026-10-07-managed-illustration-download.md)为planned；第五个共享包及相关治理配置尚未创建或更改。

本轮统一离线入口exit0，1537项测试通过（179.44秒）；315文件Ruff格式、Ruff lint、mypy73源文件及工具96%/Core93%覆盖率检查通过，见[完整日志](offline-checks.log)。该证据仅证明设计文档与现有工作区通过检查，不证明未来的自动下载、增量更新、取消/锁/热切换或两端首装已经实现。

设计任务归档后再次核对治理文档限额、链接、边界与生成参考，见[最终治理检查](governance-final.log)。本轮仅新增设计/实施计划并在素材指南注明现状和提案；既有未提交的依赖修复与素材部署改动保留。没有执行运行代码、服务器升级或外部发布。
