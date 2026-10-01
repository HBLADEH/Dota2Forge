# GsCore 图片版本生命周期验收

2026-10-02（北京时间）在现有 CPython 3.13.2/GsCore 实例完成部署恢复、冷启动及两轮受控停用/重载。[核对结果](verification.json)只包含状态、版本、时间及生命周期日志；没有聊天事件、身份、凭据或原始响应。

故障链：旧重载清理Hook/管理路由后发生MatchParseState导入错误；运行期间安装又因Pillow DLL占用中断，留下部分包缺失。收到dota停用事件但未命中插件；事件权限1也不满足停用命令的主人权限0。

先无索引/无依赖恢复三个明确本地wheel，匹配旧Pillow11.3.0 DLL后补回缺失文件。用户手动登录WebConsole后，临时同源验收页复用宿主GsHubPlugin SDK发送Bearer请求。正常宿主重启执行现存关闭钩子；旧进程退出后恢复脚本安装Pillow12.3.0，独立导入/PNG验证成功，再启动同一宿主环境。原先已丢失的Dota2UID旧关闭钩子不记作成功执行。

冷启动日志ready/image；两轮管理员API验收均为ready/client_closed=false → stop返回stopped/client_closed=true → reload返回ok=true → status返回ready/client_closed=false。每轮清理3个旧Hook和2条路由，重跑1个start Hook。

Core/Renderer/Dota2UID/Pillow的已安装包内容逐文件匹配相应wheel；独立菜单PNG为780×1050、111106字节。Dota2UID配置/绑定库/发现入口SHA256指纹未变化；临时重启配置已恢复。临时验收页和恢复脚本在收尾删除，凭据不由脚本读取/输出。

两轮重载后，用户确认原QQ会话菜单、账号和直接ID详情均正常、图片可读；客户端结果以用户反馈为据，不记录身份/比赛ID或保存聊天截图。Runtime另记录菜单/账号图片准备和发送完成。临时恢复页/脚本已删除；统一离线入口813项测试、治理/Ruff/mypy/独立覆盖率门槛通过。该单会话样本不代表全部平台/压缩算法，也不代表AstrBot生命周期通过。见[完成任务](../../tasks/done/2026-10-02-gscore-image-lifecycle.md)与[原因](../../notes/implemented/2026-10-02-gscore-wheel-recovery.md)。
