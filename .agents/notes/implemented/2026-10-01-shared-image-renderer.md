# 共享图片 Renderer 与同次数据文本回退

Category: architecture
Related task: [图片交互](../../tasks/active/2026-10-01-image-interaction.md)
Related code: [共享 Renderer](../../../packages/dota2forge-renderer/src/dota2forge_renderer/)
Related docs: [Renderer 契约](../../../docs/subsystems/renderer.md)

## Problem
原计划要求图片优先、同次数据回退及跨适配器复用。样图技术QA已完成，但此前将确认误解为必须等待用户审批，阻止了常规可逆实现。当前持续目标授权自主决定；采用已有浅色780px/5场参数作为首轮基线，不记录成用户已批准。新增包还超出了旧治理只有Core/适配器两类路径的结构。

## Decision
- 独立dota2forge-renderer依赖Core和Pillow12；Core无必选运行依赖、禁止反向依赖Renderer/Pillow，Renderer无SDK/适配器/HTTP/SQL/环境依赖。普通导入不加载字体或资源，平台消息转换只在Dota2UID发现桥接。
- MenuCard/PlayerCard/RecentMatchesCard/StatusCard/MatchDetailCard输入不可变Core结果，PNG ImageArtifact保存bytes/MIME/尺寸。780px、最高1600px、最大2MiB；文字边框超界或重叠失败，长昵称省略，未知英雄保留ID，未知装备/0空槽区分。
- 完整Noto Sans CJK SC Regular固定提交和SHA256、OFL随包；cmap用于缺字降级U+编码，不用预览子集支撑任意昵称。127个公开英雄ID/中文名记录Valve来源/抓取时间/响应SHA256。美术未许可，不打包第三方英雄/装备图像；先用原创问号占位。
- AsyncRenderer最多一条绘制线程、四个等待者；to_thread及shield保留取消后的线程所有权。close是独立shield任务，等待旧线程完成再清理字体/资源；不因调用者取消遗失关闭。未知程序错误传播，只有RenderError触发文本回退。
- Dota2UID默认reply_mode=image，可配置text；旧配置省略该项使用image。handle仍生成文本供诊断，dispatch发送TextReply/ImageReply；正常数据取得后先准备同次文本，再渲染整组图片，任一图片失败则整组回退，不新增Provider请求。发送失败不重发、不提交新列表。
- dota菜单/帮助列已启用命令；管理员项仅可信user_pm精确整数0启用。玩家/近期/状态和按两队拆页详情消费同一Renderer，保留来源/抓取/未知观测时间，北京时间与分钟/秒。文本与卡片共用格式化函数，fixture不假冒STRATZ。
- 初始最多两页；100场查询后的取页与序号使用已有有界选择状态。宿主send返回不证明平台递送；QQ压缩/会话/重载单列实测，不用桩替代。
- 治理新增shared_paths角色，保留严格schema/完整包覆盖/既有门槛，补Core反向依赖及共享SDK/适配器反例。四包wheel检查仍无索引/无SDK；显式stage命令先下载当前锁定Pillow wheel，CI准备阶段调用，普通pytest不联网。policy/schema/scripts/workflow变更需维护者评审。

## Alternatives considered
- 重复适配器绘图：资源与缺失语义会漂移，采用独立共享包。
- 每页发送时再尝试渲染：后页失败会混合部分图/文本，先生成完整组再发送。
- 用预览子集/本机字体：昵称缺字或部署不一致，选择完整OFL字体及显式降级。
- 取消时丢弃线程或自动重发：可能泄漏并发/重复消息，保留所有权，不重试发送。

## Consequences
新增约16MiB字体及Pillow运行依赖，Dota2UID wheel需连同Renderer安装；AstrBot仍为骨架，尚未实消费。共享API可复用不代表AstrBot已支持。英雄/装备实际图标与新宿主QQ联调仍缺，整体两个任务继续in_progress。

## Verification
实际生产包九张合成卡片与390px预览已生成，[QA](../../artifacts/image-interaction-v1/production/qa.json)检查尺寸/文字边框/文件大小，人工检查裁切/重叠。32项Renderer与10项图片适配测试通过，覆盖100场、中文、缺资源、未知、取消线程、同次回退和发送失败。最终统一门禁/构建结果记录于任务；没有修改真实宿主或发送外部聊天。
