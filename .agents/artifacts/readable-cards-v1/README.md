# 出装与比赛详情合成预览

所有玩家、比赛与购买次数均为合成数据，来源标记 FIXTURE；不是聊天截图或真实战绩。Valve 图像来自原有本地资源包，版权归 Valve；不因预览加入仓库而转为 MIT。

[出装手机预览](hero-items-phone.png)、[比赛第一页](match-1-phone.png)、[缺失数据](match-missing-phone.png)由当前共享 Renderer 生成。原图为780px宽，手机预览390px宽；[尺寸记录](render-checks.json)包含每图字节和文本边界数。检查覆盖四阶段各五件装备、十名玩家四页、已知/空/未知装备、缺少整个素材包两种情况。

复现：`uv run --locked python .agents/artifacts/readable-cards-v1/render_samples.py --illustration-path .dota2forge-assets`。素材目录来自已有[下载指南](../../../docs/cookbook/illustrations.md)，普通测试使用合成图片且禁网。

已检查手机预览，正文/双行装备名/统计与底部来源不重叠；图像上限保持780×1600、2MiB。文本边界检查随实际绘制执行。新增字段与中文模式标签未做在线或宿主聊天联调，本轮未改生产安装。

[PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)已改为中文标题/描述，商店介绍与安装提示通过提交7e31756更新；远端JSON摘要9ff07e15e051aeee6f6788d4f51297df1bc4114e与本地一致，验证仅两个展示字段变化，其余索引内容保留。本地生成器同步相同文案。

首轮完整测试1526通过、1失败：安装说明在Windows为CRLF，而发行生成器按既定规则输出LF，旧测试错误要求原始字节相同。测试改为LF/CRLF输入各自严格核对规范化UTF-8/LF输出，未改生成行为或门槛；首轮日志保留为check-governance-first.log。最终[统一检查](check-governance.log)退出0：1528项测试通过（136.89秒），Ruff格式/lint、mypy73文件通过，聚合覆盖93.40%，治理工具96%、Core93%。
