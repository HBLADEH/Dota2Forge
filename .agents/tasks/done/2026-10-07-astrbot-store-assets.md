# AstrBot 商店安装后的本地素材部署

Status: done

## 目标
诊断商店安装的近期战绩卡英雄占位，在用户授权服务器准备可追溯本地素材并配置实际宿主。

## 非目标
不将 Valve 美术加入公开插件或 MIT wheel，不发送真实聊天，不修改凭据、绑定或订阅。

## 验收
核实素材目录及 illustration_path；显式下载后验证清单、摘要和 PNG；仅修改素材路径并使宿主重新加载；实际安装 Renderer 可解码英雄、装备和 UI。同步安装说明并运行统一离线检查。

## 影响模块与决策
[素材指南](../../../docs/cookbook/illustrations.md)、[安装指南](../../../docs/cookbook/astrbot-public-install.md)、[既有分发决策](../../notes/implemented/2026-10-04-local-dota-illustrations.md)、[本轮部署决策](../../notes/implemented/2026-10-07-astrbot-store-assets.md)、[下载器](../../../scripts/download_dota_assets.py)。

## 验证证据
实际配置 illustration_path 为空，服务器没有素材包。容器显式下载英雄/装备后访问 raw.githubusercontent.com 的图标时超时，下载器返回1，未发布清单。改为同步同一用户本机2026-10-05素材快照，558张PNG已用真实Illustrations核对解码/摘要；保留来源、抓取时间、129项官方装备404及生成背景元数据。

统一离线入口通过：1537项测试（186.41秒），Ruff/mypy及工具96%/Core93%覆盖率检查通过。素材在持久化illustrations-store-v1，配置仅修改illustration_path；敏感备份只留服务器0600，其余字段/Token不变。服务器全部素材摘要/解码通过，实际Renderer生成FIXTURE战绩卡且英雄像素区别于占位，390px人工QA通过。

目标AstrBot冷启动ready/image、WebUI HTTP200，重读配置确认五位截图英雄成功解码；运行包仍a7/a4/a4。详见[脱敏证据](../../artifacts/astrbot-store-assets-v1/README.md)。

## 阻塞与下一步
本轮部署完成，无阻塞。用户重新发送/do战绩验证真实聊天新图；未发送聊天、未查询Provider，未公开发布新素材或文档。129项官方装备404继续占位。商店完整API重试和订阅不属于本轮验收。
