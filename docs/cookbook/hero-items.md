# 英雄热门出装

双端源码已实现，需同时更新Core、Renderer、适配器wheel和发现桥接后使用；2026-10-05本机双端均已升级0.1.0a2并恢复ready/image。[GsCore](../../.agents/artifacts/gscore-current-deployment-v1/README.md)正则/桥接及合成卡验证通过，尚无客户端连接，真实聊天待验收。无需绑定玩家账号：

```text
do斧王出装
doAM出装
do影魔出装
do出装 Shadow Fiend
```

中文全名、英文名、常见简称均可；大小写/空格/连字符不影响匹配。有歧义的简称返回候选，例如do猴子出装提示幻影长矛手/齐天大圣，请再用全名查询。Dota2UID通过GsCore on_regex具名捕获英雄；AstrBot动态正则接受裸命令和/doAM出装，静态do出装仍遵循宿主唤醒前缀。

输出[OpenDota职业比赛物品购买统计](https://docs.opendota.com/)，分出门/前期/中期/后期各前5项，包含中文物品名、次数、来源和抓取时间。0、空统计、缺失和请求失败分别显示；未提供位置、补丁、窗口、总样本和观测时间，均标未知。热门不等于最优出装或购买顺序，不能由次数计算胜率/出场率。默认图片，绘制失败回退同一结果文字。匿名API仍可能限流或不可用，失败不发成功统计、不自动重试。

2026-10-05显式只读联调英雄1/2成功，四阶段分别15/12/34/35项和16/16/30/41项；归一化服务保留未知观测时间，客户端关闭。[成功摘要](../../.agents/artifacts/hero-builds-v1/opendota-validation.json)只含公开英雄/结构与抓取时间。后续补查出现UNAVAILABLE，说明一次成功不能证明长期可用；普通测试使用MockTransport且禁网。

运行统一检查、四包构建及隔离安装导入：

```sh
uv run --locked python scripts/check_governance.py --all
uv build --all-packages
uv run --locked python scripts/smoke_wheels.py
```

STRATZ攻略验证及首版方案见[攻略源](hero-guides.md)；出装端口和缺失语义见[契约](../subsystems/hero-items.md)。来源故障、歧义、两端图片/文字回退和桥接捕获均离线验证。用户已提供AstrBot完整主宰实机卡，并要求两端README共用原图，[图片及范围](../assets/screenshots/README.md)已记录；命令输入画面、GsCore聊天、其他平台和长期API稳定性仍待验证。
