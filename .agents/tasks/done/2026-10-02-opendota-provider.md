# OpenDota 独立补充与交叉核验

Status: done

## 目标
按规划Step10实现OpenDota玩家、近期、按ID详情Provider，复用Core归一化契约；提供显式双来源核验，保留两份数据和差异，不自动换源或拼接。用户授权休息期间独立推进可离线实现任务。

## 非目标
更改已运行Bot配置、发真实消息、查询私人账号、自动解析、Valve、缓存/重试、IMP、订阅、AI、Deploy。在线样本与真实Bot验收不作为普通测试前提。

## 验收
- [x] 阅读来源决策、Core契约与公开API源码，确定字段、缺失和错误语义。
- [x] 实现注入HTTP/Clock的OpenDota Provider，明确有限超时、限流、取消和客户端所有权。
- [x] 独立详情保留解析证据/匿名/缺失；数据不完整不伪装为完整或无比赛。
- [x] 显式交叉核验返回各自来源结果及可比较差异；一侧失败不能被另一侧成功覆盖。
- [x] 检查现有STRATZ、Renderer及双端消费者兼容，禁网HTTP响应测试覆盖失败和边界。
- [x] 同步契约、安装/使用步骤和实现决策；统一门禁、四包构建与隔离wheel通过。

## 影响模块与决策
[Core](../../../packages/dota2forge-core/)、[来源策略](../../notes/implemented/2026-09-30-provider-selection.md)、[实现决策](../../notes/implemented/2026-10-02-opendota-cross-check.md)、[契约](../../../docs/subsystems/opendota.md)、规划Step10。

## 验证证据
保留AstrBot全部未提交修改。核对公开OpenAPI31.1.0与odota/core commit295a76ecdcbe90345fc6373a005280353bac015e的API/spec/playerFields/web/time/utility；没有查询真实账号或读取凭据。新增80项禁网合成测试覆盖三端口、限流/超时/取消、继承凭据移除、匿名/缺失、来源冲突与双端/Renderer消费。原STRATZ文本标记回归失败后按来源保留原提示，未改旧断言。

最终统一入口通过Ruff format/lint、mypy45源文件、914项禁网测试（综合95.97%，Core与治理工具独立80%门槛通过）；四包build及无SDK/无索引隔离wheel smoke通过，git diff --check通过。新版三wheel在临时目录经实际AstrBot4.28.2 SDK验证依赖重载后菜单PNG、11命令、GreedyStr与重复关闭，不更新运行宿主。

## 阻塞与下一步
本任务的SDK增量完成，运行Bot继续STRATZ，未注册OpenDota/核验命令、未在线验证Provider。用户暂停人工测试，AstrBot剩余权限/直接ID验收保留原active任务。后续按Step11独立定义来源缓存、明确刷新和有限重试，再推进IMP/订阅等；不将接口实现或公开schema读取当作线上数据通过。
