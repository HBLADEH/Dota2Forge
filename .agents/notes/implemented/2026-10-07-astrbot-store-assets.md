# 商店部署的显式本地素材配置

Category: operations
Related task: [素材部署](../../tasks/done/2026-10-07-astrbot-store-assets.md)
Related code: [只读素材加载](../../../packages/dota2forge-renderer/src/dota2forge_renderer/illustrations.py)
Related docs: [AstrBot安装](../../../docs/cookbook/astrbot-public-install.md)

## Problem
用户商店安装alpha.7后可以取得战绩并渲染卡片，但英雄位置均为问号。授权服务器实际没有素材目录，illustration_path为空；既有决策明确Valve游戏图不进入商店ZIP/MIT wheel，默认运行期也不联网补图。

## Decision
沿用显式素材流程及[既有分发边界](2026-10-04-local-dota-illustrations.md)。容器调用原下载器时，英雄/装备请求完成，OpenDota图标镜像访问超时，返回1且未发布清单。转为私有同步同一用户本机2026-10-05素材快照，逐项检查558张PNG和原SHA256；保留实际来源、抓取时间、129项装备404与已有生成背景元数据。

素材放入持久化插件数据目录illustrations-store-v1，配置仅修改illustration_path；敏感配置备份只留服务器，权限0600。使用实际安装Renderer合成离线卡验证，不发送真实聊天。同步公开指南的Docker下载/路径/重载说明，不改变运行包、下载器或公开发行资产。

## Alternatives considered
反复重新下载整个包：已定位单一镜像超时，当前有完整可追溯快照，优先私有同步。将本机游戏图补入商店ZIP：与既有分发决策不符，继续独立配置。把宿主机路径写入容器配置：容器不可见，使用插件数据目录相对路径。

## Consequences
游戏素材仍独立于代码许可；本次快照不等于重新抓取或最新完整历史表，缺图保持占位。清单缓存需要新Renderer实例。数据挂载保留素材，容器重建仍须恢复对应运行依赖；未来网络更新失败不能当作成功清单。

## Verification
本机和服务器逐项解码、摘要检查通过：127英雄、415装备、9段位、5星级、1金币、1背景。129缺图全部为已记录的官方装备404。实际安装a4 Renderer生成780×1560/366425字节FIXTURE战绩卡，英雄区域与无素材占位不同，390px预览人工核验通过。候选配置通过实际适配器校验，修改后其余配置字段及Token相等。冷启动实际日志ready/image，重读配置的五位截图英雄成功解码，WebUI HTTP200；运行包仍a7/a4/a4。统一离线1537测试（186.41秒）、Ruff/mypy、工具96%/Core93%通过。真实聊天新图尚待用户确认，见[部署证据](../../artifacts/astrbot-store-assets-v1/README.md)。
