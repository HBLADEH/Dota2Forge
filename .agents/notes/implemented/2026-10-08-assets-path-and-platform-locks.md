# 素材 Windows 路径等价与跨平台文件锁检查

Category: bug-fix
Related task: [a6发行部署](../../tasks/active/2026-10-08-dota2uid-bundled-release.md)
Related code: [素材校验](../../../packages/dota2forge-assets/src/dota2forge_assets/validation.py)、[素材锁](../../../packages/dota2forge-assets/src/dota2forge_assets/store.py)、[运行库锁](../../../scripts/gscore_bundled_runtime.py)
Related docs: [素材契约](../../../docs/subsystems/assets.md)、[运行库契约](../../../docs/subsystems/gscore-bundled-runtime.md)

## Problem
发行统一检查出现合成素材 ranks/1 的 path 失败。定位到 Windows 在并发创建目录期间，Path.resolve 的 WinAPI 从目录不存在切换到文件不存在，偶尔保留扩展路径前缀；root.resolve 使用普通DOS前缀，等价目录被 containment 检查误拒绝。独立进程插入真实 parent.mkdir 可确定性复现，不能靠随机重跑宣称修复。

Linux CI另在mypy阶段失败：os.name判断不能裁剪平台类型分支，msvcrt只在Windows有锁属性；Linux的fcntl忽略反成unused-ignore。测试尚未运行，不能归咎于依赖或放宽门槛。

## Decision
统一 Windows 普通与扩展DOS/UNC路径命名空间后检查根目录包含关系，仍拒绝未知设备命名空间、越界和符号链接。保留部分缺失与就绪的真实状态语义。文件锁用类型检查器可识别的sys.platform分支，各平台继续使用原生锁；移除失效忽略，不改变锁行为或覆盖率门槛。

## Alternatives considered
重复测试直到偶然通过无法证明修复。接受partial或跳过路径守卫会掩盖真实问题。统一禁用文件锁或放宽mypy会削弱并发与平台保证，均未采用。

## Consequences
Assets a1及随包后端在首次公开前重建，草稿资产和清单摘要同步更新；Core/Renderer a4不变。新增命名空间、越界、设备路径与并发目录回归，Linux和Windows类型检查独立验证。

## Verification
具体命令、确定性回归、最终统一离线门禁及公开资产摘要见[发行证据](../../artifacts/dota2uid-bundled-release-v1/README.md)。原失败状态保留用于原因追踪，未删断言或自动接受快照。
