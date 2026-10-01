# GsCore 部署文件与重载故障恢复

Category: operations
Related task: [宿主图片生命周期](../../tasks/done/2026-10-02-gscore-image-lifecycle.md)
Related code: [发现桥接](../../../adapters/Dota2UID/src/Dota2UID/host_entry.py.template)
Related docs: [本机接入](../../../docs/cookbook/dota2uid.md)

## Problem
10-01 的原生重载清理了旧命令、Hook和管理路由，随后因进程中的Core公共导出缺少MatchParseState而失败。运行时与磁盘wheel不能仅以相同的0.1.0a1版本号判定一致。接着在宿主运行期间安装解析了Pillow升级，卸载遇到占用的11.3.0 DLL失败，留下Dota2UID目录及Pillow Python文件缺失。10-02收到的两条停用事件没有进入插件；它们的user_pm=1也不满足pm=0管理命令。

## Decision
- 保留配置、绑定库、发现入口；只在本机保存指纹，不提交真实配置/数据/日志。
- 无索引/无依赖重装明确Core、Renderer、Dota2UID wheel，避免恢复Python源码时同时触碰占用的第三方DLL。
- 从原始11.3.0 wheel核对全部现存DLL并补回缺失文件；不覆盖不同内容的文件。安装器生成的RECORD不按上游wheel逐字比较。11.3.0只作为恢复中间态，不放宽Renderer的Pillow12依赖。
- 以宿主原有SDK使用用户手动登录的会话；会话文件保存的是sha256摘要，不能当作Bearer。停止/重载仍执行原有管理员校验，不提升QQ权限。
- 锁定Pillow升级须在旧宿主进程退出后执行，再冷启动。临时本机恢复页/重启命令需还原并清理。恢复完成后重新验收ready→stopped/client_closed=true→reload→ready；失败重载后进程退出不等同旧Runtime.close已执行。

## Alternatives considered
- 继续从QQ发停用：注册已丢失且权限不符，不能释放旧运行期。
- 强行覆盖占用DLL或放宽Pillow版本：破坏安装一致性，采用退出后升级。
- 只重载发现入口：不保证清除共享包的旧进程导入缓存，先冷启动恢复。

## Consequences
冷启动短暂中断所有GsCore插件；不修改宿主源码、权限、凭据和绑定。后续升级先确认stop成功、完成安装与独立导入，再选择受控重载或冷启动。

## Verification
三个本地wheel已恢复；旧Pillow仅作中间恢复态。用户重新登录后冷启动成功，Pillow12.3.0安装与独立PNG生成通过，四包内容逐文件匹配wheel。管理员API两轮stop均返回stopped/client_closed=true、reload均ok=true、最终ready；配置/绑定库/发现入口指纹未变、临时重启设置已还原。[脱敏证据](../../artifacts/gscore-image-lifecycle-v1/README.md)仅含生命周期信息；用户随后确认QQ菜单、账号、详情均正常且图片可读，仅为单会话样本。
