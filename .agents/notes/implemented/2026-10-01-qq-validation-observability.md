# QQ 实机验收的最小观测日志

Category: operations
Related task: [图片交互](../../tasks/active/2026-10-01-image-interaction.md)
Related code: [Dota2UID Runtime](../../../adapters/Dota2UID/src/Dota2UID/runtime.py)
Related docs: [Dota2UID 操作](../../../docs/cookbook/dota2uid.md)

## Problem
Computer Use 可能无法取得 QQ 窗口，需要用户代为执行命令。原 Runtime 没有稳定的 Dota2UID 发送观测，宿主日志无法可靠区分“已生成图片”“发送回调完成”和“列表已提交”。

## Decision
Runtime 使用标准 logging 记录有限事件：生命周期状态、允许的命令名、回复数量、图片数量/字节数/尺寸、渲染回退、发送成功/失败/取消和列表提交。日志不写账号、群号、用户号、昵称、消息正文、图片内容、Token 或异常消息；`operation=invalid` 用于未注册命令。

用户负责在 QQ 中确认图片是否可见、是否被压缩以及分页/详情内容是否正确；日志只作为服务端证据，不能替代 QQ 客户端视觉确认。发送回调完成与列表提交分开记录，失败不代表客户端已显示。

## Alternatives considered
- 只看宿主通用日志：无法稳定关联一次命令和图片尺寸。
- 记录完整 Caller 或消息正文：会暴露平台身份和聊天内容，违反隐私边界。
- 把 bot.send 返回当作 QQ 已显示：回调成功不等于客户端渲染可读。

## Consequences
真实验收可以用命令名、图片尺寸/字节数、发送完成和选择提交事件与用户报告交叉核对。日志仍不能证明压缩后的视觉效果，也不记录具体群聊；用户需提供现象和必要截图摘要。

## Verification
新增禁网日志断言，确认玩家图片发送日志包含命令、`780x850`、图片数量和完成状态，且不含合成账号/用户号。完整治理检查和测试在本轮修改后复跑。
