# Dota2Forge 项目策划书

> 品牌统一：总项目 Dota2Forge；核心 Dota2Forge Core；AstrBot 插件 Dota2Forge / `astrbot_plugin_dota2forge`；GsCore 插件 Dota2UID；部署整合 Dota2Forge Deploy。
> “Dota2Forge —— 将 Dota 2 数据锻造成可复用的 Bot 能力。”
> 本文件保留功能规划，实施现状见 [README](README.md)。治理补充要求先实施 M0；M0 后按 Core → Dota2UID → AstrBot 的顺序推进。

> 面向 Codex / AI Coding Agent 的工程实施文档\
> 项目阶段：M0 已交付，STRATZ Core 与 Dota2UID QQ 首个宿主闭环已实现\
> 优先级：STRATZ Core 闭环 → Dota2UID / GsCore → AstrBot → 扩展能力 → Integration Pack

---

## 1. 项目概述

### 1.1 项目名称

**Dota2Forge**

Dota2Forge 是一个面向 Dota 2 的开源 Bot 业务核心与多框架适配项目。

项目目标不是把业务代码绑定在某一个 QQ Bot 框架中，而是将 Dota 2 的数据访问、领域模型、战绩分析、账号绑定、战报生成、订阅检测等核心能力独立出来，再分别通过 Adapter 接入 AstrBot、GsCore 等宿主框架。

最终形成：

```text
                         Dota2Forge
                            │
                  ┌─────────┴─────────┐
                  │                   │
             Dota2Forge Core       Deployment
                  │
          ┌───────┴───────┐
          │               │
     AstrBot Adapter   GsCore Adapter
          │               │
       AstrBot           GsCore
          │               │
          └────── QQ / IM ─┘
```

项目优先完成业务核心以及 AstrBot、GsCore 两套适配实现，整合部署包放在最后阶段完成。

---

## 2. 项目目标

### 2.1 核心目标

构建一套与 Bot 框架无关的 Dota 2 业务核心，使以下能力可以被 AstrBot、GsCore、未来其他平台共同复用：

- Steam / Dota 2 玩家账号绑定
- SteamID32 / SteamID64 / Account ID 转换
- 玩家信息查询
- 最近比赛查询
- 单场比赛详情查询
- 英雄数据查询
- 物品数据查询
- 排位 / 段位数据
- 玩家常用英雄和英雄池统计
- 胜率、KDA、GPM、XPM 等基础统计
- 战报数据模型
- 战绩图片 / 卡片渲染
- 新比赛检测
- 比赛结束订阅通知
- 后续 AI 分析所需的结构化上下文
- 后续攻略、英雄分析、版本信息能力

### 2.2 平台目标

第一阶段支持：

```text
Dota2Forge Core
├── AstrBot Adapter
└── GsCore Adapter
```

后续支持：

```text
Dota2Forge Core
├── AstrBot Adapter
├── GsCore Adapter
├── REST API
├── CLI
├── Discord Adapter
├── Telegram Adapter
└── Web
```

### 2.3 部署目标

最终提供三种部署模式：

```text
AstrBot Edition
GsCore Edition
Full Edition
```

其中默认不要求用户安装全部组件。

---

## 3. 非目标

第一阶段明确不做：

- 不让 Core 直接依赖 AstrBot
- 不让 Core 直接依赖 GsCore
- 不让 Core 直接处理 QQ / OneBot 消息
- 不在 Core 内实现常驻 Bot 进程
- 不在 Core 内启动无限循环 Scheduler
- 不把所有框架逻辑塞进一个插件
- 不为了兼容框架而在业务层大量使用 `if framework == ...`
- 不在第一阶段实现复杂 Web 前端
- 不在第一阶段实现完整 AI Agent
- 不在第一阶段追求所有 Dota 2 数据源全覆盖

---

# 4. 核心设计原则

## 4.1 Core First

所有真正与 Dota 2 有关的逻辑必须优先进入：

```text
dota2forge_core
```

Adapter 只负责宿主框架相关能力。

---

## 4.2 Framework Agnostic

Core 中禁止出现：

```text
AstrBot
GsCore
NapCat
OneBot
QQ
Discord
Telegram
```

相关类型或依赖。

错误示例：

```python
async def query_match(event: AstrMessageEvent): ...
```

正确示例：

```python
async def get_recent_matches(
    account_id: int,
    limit: int = 10,
) -> list[MatchSummary]: ...
```

---

## 4.3 Ports & Adapters

整体采用：

**Hexagonal Architecture / Ports & Adapters**

```text
                    ┌─────────────────┐
                    │   AstrBot       │
                    │   Adapter       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │                 │
                    │  Dota2Forge Core  │
                    │                 │
                    └────────▲────────┘
                             │
                    ┌────────┴────────┐
                    │    GsCore       │
                    │    Adapter      │
                    └─────────────────┘
```

Core 定义业务接口。

Adapter 实现平台输入输出。

---

# 5. 推荐仓库形式

## 5.1 第一阶段采用 Monorepo

项目初期不建议拆多个仓库。

推荐：

```text
Dota2Forge/
├── packages/
│   └── dota2forge_core/
│
├── adapters/
│   ├── astrbot/
│   └── gscore/
│
├── deploy/
│   ├── astrbot/
│   ├── gscore/
│   └── full/
│
├── tests/
│
├── scripts/
├── docs/
│
├── pyproject.toml
├── README.md
├── LICENSE
└── .github/
```

原因：

- Core 和 Adapter 可以同步修改
- 一个 PR 完成跨模块调整
- CI 更容易统一
- 避免早期多仓库版本同步问题
- Codex 更容易理解完整上下文

项目稳定以后，再考虑拆分：

```text
dota2forge-core
Dota2UID
astrbot_plugin_dota2forge
dota2forge-deploy
```

---

# 6. 推荐目录结构

```text
Dota2Forge/
│
├── packages/
│   └── dota2forge_core/
│       └── src/
│           └── dota2forge_core/
│               │
│               ├── api/
│               │   ├── base.py
│               │   ├── stratz.py
│               │   ├── opendota.py
│               │   └── steam.py
│               │
│               ├── domain/
│               │   ├── player.py
│               │   ├── match.py
│               │   ├── hero.py
│               │   ├── item.py
│               │   ├── rank.py
│               │   ├── binding.py
│               │   └── subscription.py
│               │
│               ├── ports/
│               │   ├── repository.py
│               │   ├── cache.py
│               │   ├── renderer.py
│               │   └── provider.py
│               │
│               ├── services/
│               │   ├── account_service.py
│               │   ├── player_service.py
│               │   ├── match_service.py
│               │   ├── hero_service.py
│               │   ├── statistics_service.py
│               │   ├── subscription_service.py
│               │   └── analysis_service.py
│               │
│               ├── usecases/
│               │   ├── bind_player.py
│               │   ├── query_player.py
│               │   ├── get_recent_matches.py
│               │   ├── get_match_detail.py
│               │   ├── get_hero_stats.py
│               │   └── poll_new_matches.py
│               │
│               ├── rendering/
│               │   ├── player_card.py
│               │   ├── match_card.py
│               │   ├── match_list.py
│               │   └── hero_card.py
│               │
│               ├── resources/
│               │   ├── heroes.json
│               │   ├── items.json
│               │   └── localization/
│               │
│               ├── utils/
│               │   ├── steam_id.py
│               │   ├── datetime.py
│               │   └── retry.py
│               │
│               ├── exceptions.py
│               ├── config.py
│               └── __init__.py
│
├── adapters/
│   │
│   ├── astrbot/
│   │   ├── src/
│   │   │   └── astrbot_plugin_dota2forge/
│   │   │       ├── plugin.py
│   │   │       ├── commands/
│   │   │       ├── storage/
│   │   │       ├── scheduler/
│   │   │       ├── ai_tools/
│   │   │       └── config.py
│   │   ├── metadata.yaml
│   │   └── pyproject.toml
│   │
│   └── gscore/
│       ├── src/
│       │   └── Dota2UID/
│       │       ├── __init__.py
│       │       ├── commands/
│       │       ├── storage/
│       │       ├── scheduler/
│       │       ├── ai_tools/
│       │       └── config.py
│       └── pyproject.toml
│
├── deploy/
│   ├── astrbot/
│   ├── gscore/
│   └── full/
│
├── tests/
│   ├── core/
│   ├── astrbot/
│   ├── gscore/
│   └── integration/
│
└── docs/
```

---

# 7. Dota2Forge Core 设计

## 7.1 Core 职责

Core 负责：

```text
Dota 2 API
数据模型
业务逻辑
数据转换
账号绑定业务规则
比赛分析
统计计算
渲染数据
订阅检测逻辑
缓存策略接口
数据库接口
```

Core 不负责：

```text
命令注册
QQ消息
框架权限
框架生命周期
框架 Scheduler
框架配置 UI
```

---

# 8. 数据源设计

2026-09-30 用户确认：以免费、易用和实际数据质量选型，不要求数据源服务端开源。以下选型中 STRATZ 基础 Provider 已实现并只读联调，其他补充及扩展能力仍为规划：

| 数据源 | 职责 | 接入阶段 |
| --- | --- | --- |
| STRATZ | 默认主源：玩家、当前段位、最近比赛；后续按比赛 ID 查询详情、IMP 和时间序列 | 首个联网闭环 |
| OpenDota | 独立补充、基础战绩与交叉核验 | 首个宿主闭环之后 |
| Valve Steam Web API | 按需补充账号解析和官方基础比赛数据 | 出现明确缺口时 |

首轮不做自动 fallback、跨源字段拼接或后台抓取。段位冲突分别标明来源和时间，不取较高段位，也不让补充源旧值覆盖主源。明确隐私拒绝时不换源绕过限制。精确 MMR 不作为可保证能力，估算分数与排行榜名次单独标注；IMP 为 STRATZ 的表现指标。

[实测](.agents/tasks/done/2026-09-30-stratz-evaluation.md) 的 20 场基础数据一致，STRATZ 15 场有详细经济/购买记录，OpenDota 为 2 场；用户确认 STRATZ 段位为当前值，OpenDota 对应先前段位。单账号样本不构成全站时效保证。历史总场次和经济序列须明确各自统计口径。

STRATZ 采用 GraphQL、Bearer Token 与已验证的 User-Agent: STRATZ_API；检查 HTTP 状态之外还需检查 GraphQL errors、部分数据及缺失字段，HTML 403 不能直接认定账号私密或凭据失效。动态读取秒/分/时/日额度头并遵守最紧窗口；本次 Token 的 8/秒、150/分钟、1500/小时、15000/天仅为观测值，不是所有 Token 的固定配额。OpenDota 免费接入无需付费 Key，本次元数据为 3000/天、60/分钟。展示保留来源链接。

HTTP 与配置放在基础设施/组合入口，所有 API 必须通过 Provider 抽象；详细原因见 [选型决策](.agents/notes/implemented/2026-09-30-provider-selection.md)，首轮验收见 [STRATZ 接入任务](.agents/tasks/done/2026-09-30-stratz-provider.md)。GC、自建全量 OpenDota、录像解析服务和 GSI 不作为首个闭环依赖。缓存、重试和自动回退后续另行定义与验收。

后续详情扩展的示意（不是当前公共契约；当前端口见 [ports.py](packages/dota2forge-core/src/dota2forge_core/ports.py)）：

```python
class MatchProvider(Protocol):
    async def get_match_detail(
        self,
        account_id: int,
        match_id: int,
    ) -> MatchDetail: ...

    async def get_recent_matches(
        self,
        account_id: int,
        limit: int,
    ) -> list[MatchSummary]: ...
```

STRATZ 的 PlayerProvider 和 MatchProvider 已实现基础概况、段位与最近比赛，并完成独立只读联调。2026-10-01 新增独立 MatchDetailProvider/MatchDetailService 与最小详情模型，已只读核对列表外旧比赛；Dota2UID 的直接 ID、最后已发送列表序号/取页和图片/文本消费已离线验证。共享 Renderer/详情卡代码已实现，新命令/图片 QQ 验收仍依 [历史详情任务](.agents/tasks/active/2026-10-01-historical-match-detail.md) 推进。OpenDota 实现在后续补充阶段，当前尚未实现。

业务层只依赖：

```text
MatchProvider
```

不直接依赖 STRATZ。

---

# 9. 领域模型

第一阶段至少定义：

```text
Player
PlayerProfile
PlayerBinding

MatchSummary
MatchDetail
MatchPlayer

Hero
HeroStatistics

Item
ItemBuild

Rank

Subscription
SubscriptionEvent
```

示例：

```python
@dataclass(slots=True)
class MatchSummary:
    match_id: int
    account_id: int
    hero_id: int

    kills: int
    deaths: int
    assists: int

    gpm: int | None
    xpm: int | None

    duration: int
    started_at: datetime

    is_win: bool
```

---

# 10. 用户身份模型

不要把 QQ ID 当成业务主键。

定义统一平台身份：

```python
@dataclass(slots=True)
class PlatformIdentity:
    platform: str
    user_id: str
```

例如：

```text
platform = astrbot
user_id  = 123456789

platform = gscore
user_id  = 123456789
```

绑定关系：

```text
PlatformIdentity
       │
       ▼
Dota Account ID
```

这样未来可以扩展 Discord 等平台。

---

# 11. Repository 抽象

业务层禁止直接执行数据库 SQL。

定义：

```python
class BindingRepository(Protocol):
    async def get_binding(
        self,
        identity: PlatformIdentity,
    ) -> PlayerBinding | None: ...

    async def save_binding(
        self,
        binding: PlayerBinding,
    ) -> None: ...
```

其他：

```text
SubscriptionRepository
MatchRepository
PlayerRepository
CacheRepository
```

---

# 12. AstrBot Adapter

## 12.1 定位

AstrBot Adapter 是：

```text
AstrBot
   ↓
Dota2Forge Core
```

之间的桥梁。

插件名称建议：

```text
astrbot_plugin_dota2forge
```

---

## 12.2 AstrBot Adapter 职责

负责：

- AstrBot 命令注册
- 获取发送者 ID
- 参数解析
- Core UseCase 调用
- 消息发送
- 图片发送
- AstrBot 配置
- AstrBot Scheduler
- AstrBot AI Tool 注册
- AstrBot Storage Adapter

禁止重新实现：

```text
STRATZ请求
比赛解析
SteamID转换
统计算法
战报业务数据
```

---

## 12.3 第一阶段命令

建议 MVP：

```text
/dota help

/dota bind <SteamID>
/dota unbind
/dota me

/dota recent
/dota recent 20

/dota match <MatchID>

/dota hero <Hero>

/dota rank
```

中文别名：

```text
dota帮助
dota绑定
dota解绑
dota战绩
dota最近
dota比赛
dota英雄
dota段位
```

---

# 13. GsCore Adapter

## 13.1 定位

GsCore 版本名称：

```text
Dota2UID
```

定位：

```text
GsCore
  ↓
Dota2Forge Core
```

---

## 13.2 GsCore Adapter 职责

负责：

- GsCore 指令注册
- Event 转换
- GsCore UID / 用户绑定接口整合
- GsCore 数据库存储实现
- GsCore Scheduler
- GsCore 图片发送
- GsCore 配置管理
- GsCore AI Tool
- GsCore WebUI 配置接口

GsCore Adapter 同样不重复实现 Dota 2 核心业务。

---

# 14. 一套代码同时适配 AstrBot / GsCore

目标关系：

```text
                MatchService
                     │
        ┌────────────┴────────────┐
        │                         │
 AstrBot Command             GsCore Command
        │                         │
      QQ消息                    QQ消息
```

例如两个 Adapter：

```python
result = await core.match_service.get_recent_matches(account_id)
```

调用的是同一个 Core。

框架不同的只有：

```text
输入
身份
配置
生命周期
消息发送
Scheduler
数据库实现
```

---

# 15. Scheduler 设计

Core 禁止自己长期运行无限循环。

Core 只暴露：

```python
async def poll_new_matches() -> list[NewMatchEvent]: ...
```

框架负责定时触发：

```text
AstrBot Scheduler
        ↓
poll_new_matches()

GsCore Scheduler
        ↓
poll_new_matches()
```

Core 返回：

```text
NewMatchEvent
```

Adapter 决定：

```text
发到哪个群
@谁
发送文本还是图片
```

---

# 16. 渲染系统

推荐分两层：

```text
Core
└── Render View Model

Shared renderer package
└── Pillow/HTML renderer

Adapter
└── Send Image
```

第一阶段图片切片优先使用：

```text
Jinja2
HTML
Playwright / Chromium
```

或者 Pillow。

优先保证 Pillow 路径可独立运行，以便实现：

- 图片帮助菜单
- 玩家概况卡片
- 最近战绩列表
- 比赛详情卡片
- 玩家主页
- 英雄数据卡
- 段位卡片

Renderer 返回：

```text
bytes
Path
ImageArtifact
```

渲染层只返回 ImageArtifact/bytes/Path；Adapter 决定发送文本或图片，渲染失败时使用同次数据的文本回退。

图片首轮只消费已验证的玩家与最近比赛模型；历史详情在按比赛 ID的 MatchDetail 契约完成后接入，不把 recent 的有限列表当作完整历史。

---

# 17. AI 能力预留

第一阶段不必实现完整 AI Agent，但 Core 必须预留：

```python
async def build_player_analysis_context(...)
async def build_match_analysis_context(...)
async def build_hero_analysis_context(...)
```

返回 JSON / DTO：

```json
{
  "match": {},
  "player": {},
  "statistics": {},
  "timeline": {},
  "items": []
}
```

后续 AstrBot / GsCore 分别注册自己的 AI Tool。

---

# 18. 缓存策略

Dota 数据中很多资源无需重复查询。

建议：

```text
Hero Metadata
Item Metadata
Patch Metadata
Player Profile
Match Detail
```

支持 TTL Cache。

Core 定义：

```python
class CachePort(Protocol):
    async def get(...)
    async def set(...)
```

第一阶段提供：

```text
MemoryCache
SQLiteCache
```

后续：

```text
RedisCache
```

---

# 19. 错误模型

统一异常：

```text
Dota2ForgeError

├── ProviderError
├── RateLimitError
├── AuthenticationError
├── PlayerNotFoundError
├── MatchNotFoundError
├── BindingNotFoundError
├── InvalidSteamIdError
└── RenderingError
```

Core 不返回：

```text
“查询失败啦~”
```

Core 返回异常。

Adapter 决定用户文案。

---

# 20. 配置设计

以下通用键为配置规划，Core 不读取环境变量。已实现的独立联调入口使用 STRATZ_TOKEN、STRATZ_ACCOUNT_ID 和有限 STRATZ_TIMEOUT_SECONDS，见 [配置步骤](docs/cookbook/stratz.md)。STEAM_API_KEY 按需启用，OPENDOTA_API_KEY 仅为可选付费能力，免费默认部署不要求提供。REQUEST_TIMEOUT、CACHE_TTL 的宿主配置与缓存契约待后续实现。

Core Config：

```text
STRATZ_TOKEN
STEAM_API_KEY
OPENDOTA_API_KEY

REQUEST_TIMEOUT
CACHE_TTL
DEFAULT_MATCH_LIMIT
```

Adapter Config：

```text
command_prefix
group_whitelist
subscription_enabled
scheduler_interval
render_enabled
```

敏感信息禁止提交 Git。

提供：

```text
.env.example
```

---

# 21. 日志

统一使用 Python logging。

建议结构化日志：

```text
provider
operation
account_id
match_id
duration_ms
result
```

Token / API Key 不允许进入日志。

---

# 22. 测试策略

## Core

必须重点测试：

```text
SteamID转换
胜负判断
KDA计算
比赛数据解析
Provider响应转换
订阅新比赛检测
Repository行为
```

目标：

```text
Core ≥ 80% coverage
```

---

## Adapter

测试：

```text
命令参数解析
Core返回值到消息转换
异常到用户提示转换
```

---

## Integration

通过 Mock Provider 测试：

```text
AstrBot
   ↓
Core
   ↓
Mock STRATZ
```

和：

```text
GsCore
   ↓
Core
   ↓
Mock STRATZ
```

禁止 CI 依赖真实 STRATZ API。

---

# 23. 开发阶段规划

---

## Phase 0：仓库初始化

目标：

建立工程骨架。

任务：

- 创建 Monorepo
- pyproject.toml
- Ruff
- Pyright / mypy
- pytest
- pre-commit
- GitHub Actions
- LICENSE
- README
- .env.example
- docs/

验收：

```bash
pytest
ruff check .
```

全部通过。

---

# Phase 1：Dota2Forge Core MVP

优先级：最高。

实现：

### API

- Steam ID 工具（已有严格 Account ID / SteamID64 值与转换；新输入形式另行验证）
- 首轮：STRATZ PlayerProvider / MatchProvider，先完成玩家、当前段位、最近比赛
- 宿主基础闭环后：按比赛 ID 的 STRATZ 单场详情；IMP、经济/购买序列随后逐项核对；新增公共模型须先检查消费者
- 后续：OpenDota 独立补充与交叉核验
- 按需：Valve Steam Web API，不作为首轮必需依赖

本 Phase 列表是完整功能范围；首个交付切片以 [STRATZ 任务](.agents/tasks/done/2026-09-30-stratz-provider.md) 为准，完成后先接 Dota2UID，不等待 Renderer、双数据源或全部 Domain/UseCase 实现。

### Domain

- Player
- Match
- Hero
- Item
- Rank

### Services

- AccountService
- PlayerService
- MatchService
- HeroService

### UseCases

```text
BindPlayer
GetPlayer
GetRecentMatches
GetMatchDetail
GetHeroStats
```

### Repository

先提供：

```text
SQLite
```

### Renderer

至少实现：

```text
RecentMatchesCard
MatchDetailCard
PlayerCard
MenuCard
```

Phase 1 验收：

Core 可以在完全不安装 AstrBot / GsCore 的环境中运行：

```python
client = Dota2Forge(...)

player = await client.get_player(...)
matches = await client.get_recent_matches(...)
```

---

# Phase 2：GsCore Adapter / Dota2UID

优先级：高。

实现：

```text
Dota2UID
```

必须复用：

```text
dota2forge_core
```

实现：

- GsCore Event Adapter
- GsCore Repository
- GsCore Config
- GsCore Scheduler
- GsCore UID 系统适配
- GsCore 图片消息
- GsCore 图片菜单、玩家卡、近期战绩卡和详情卡
- GsCore Help
- GsCore WebUI 配置

Phase 2 验收：

用户部署：

```text
NapCat
GsCore
Dota2UID
```

即可完整使用 Dota2 Bot。

不要求 AstrBot。

---

# Phase 3：AstrBot Adapter

优先级：高。

实现：

```text
astrbot_plugin_dota2forge
```

命令：

```text
dota绑定
dota解绑
dota战绩
dota最近
dota比赛
dota英雄
dota段位
```

实现：

- AstrBot Config
- AstrBot User Identity
- AstrBot SQLite Repository Adapter
- 图片发送
- 图片菜单、玩家卡、近期战绩卡和详情卡
- 错误提示
- Scheduler
- 新比赛检测

Phase 3 验收：

普通用户安装：

```text
NapCat
AstrBot
astrbot_plugin_dota2forge
```

即可使用 Dota2 Bot。

不需要安装 GsCore。

---

# Phase 4：订阅系统

实现：

```text
比赛结束提醒
段位变化
每日战报
玩家追踪
```

Core：

```python
poll_new_matches()
poll_rank_changes()
```

Adapter 负责 Scheduler 和发送。

---

# Phase 5：AI / 攻略

实现：

```text
比赛复盘
玩家风格分析
英雄池分析
出装问题分析
攻略查询
```

Core 提供结构化上下文。

AstrBot / GsCore 分别接自己的 AI 系统。

---

# Phase 6：Integration Pack

最后再做。

---

# 24. 整合包设计

不要做一个“所有组件强制安装”的单一版本。

提供三个 Profile。

---

## 24.1 AstrBot Edition

```text
NapCat
  │
AstrBot
  │
astrbot_plugin_dota2forge
  │
Dota2Forge Core
```

目录：

```text
deploy/astrbot/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 24.2 GsCore Edition

```text
NapCat
  │
GsCore Adapter
  │
GsCore
  │
Dota2UID
  │
Dota2Forge Core
```

目录：

```text
deploy/gscore/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 24.3 Full Edition

可选高级模式：

```text
NapCat
   │
AstrBot
   │
GsCore Adapter
   │
GsCore
   │
Dota2UID
```

适用于同时需要：

```text
AstrBot AI 生态
+
GsCore 游戏插件生态
```

Full Edition 不作为默认推荐安装方式。

---

# 25. Docker 原则

整合包最后阶段再做。

镜像建议：

```text
ghcr.io/<org>/dota2forge-core
ghcr.io/<org>/astrbot-plugin-dota2forge
ghcr.io/<org>/dota2uid
```

Docker Compose 禁止全部使用：

```text
latest
```

应固定兼容版本。

---

# 26. CI/CD

GitHub Actions：

```text
lint
typecheck
test
build
```

PR 必须：

```text
Ruff PASS
Pyright PASS
pytest PASS
```

Release：

```text
tag
↓
build package
↓
publish
```

---

# 27. 版本策略

推荐 Semantic Versioning：

```text
MAJOR.MINOR.PATCH
```

Core 与 Adapter 独立版本。

Adapter 声明：

```text
dota2forge-core >= x.y,<x+1
```

避免 Adapter 与 Core 隐式不兼容。

---

# 28. 第一阶段 MVP 功能范围

第一版不要做太多。

必须完成：

```text
账号绑定
玩家查询
最近战绩
比赛详情
英雄查询
段位查询
图片战报

图片帮助菜单

玩家概况卡

近期战绩卡

历史单局详情卡（按比赛 ID）
```

可延后：

```text
AI分析
复杂攻略
阵容分析
Pick/Ban
比赛直播
职业赛事
Fantasy
```

---

# 29. 最重要的架构约束

Codex 在实现过程中必须遵守：

### Rule 1

`dota2forge_core` 禁止 import：

```text
astrbot
gsuid_core
nonebot
onebot
napcat
```

---

### Rule 2

AstrBot Adapter 和 GsCore Adapter 禁止重复实现 Dota 2 API。

---

### Rule 3

所有外部 Dota 2 数据必须经过 Provider。

---

### Rule 4

所有持久化必须经过 Repository。

---

### Rule 5

Core 不直接发送消息。

---

### Rule 6

Core 不直接注册 Scheduler。

---

### Rule 7

Core 不直接读取宿主 Bot 用户 ID。

---

### Rule 8

框架差异只允许存在于：

```text
adapters/
```

---

# 30. 推荐 Codex 执行顺序

Codex 不应一次性实现整个项目。

Step 1–3 已完成，见 [STRATZ 交付](.agents/tasks/done/2026-09-30-stratz-provider.md)。Step 4 已完成代码、离线测试与本机安装；Step 5 已通过真实宿主加载/受控重载/卸载及恢复冷启动，用户已完成 QQ 单会话帮助、绑定、玩家和战绩命令验收，见 [Dota2UID 任务](.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)。Step 6 Renderer资源/回退边界、Step 8详情/选择文本与卡片代码和 AstrApplication 无宿主消费者已完成离线验证；GsCore 图片压缩/分页/重载与 AstrBot 平台消费未完成。不重做已完成的 Core 和主源；在线证据单列。

```text
Step 1
固定 STRATZ 最小查询、字段及错误映射，编写禁网响应测试

Step 2
实现 STRATZ 玩家与最近比赛 Provider、限流和客户端关闭

Step 3
通过 Core 离线检查，再用本机凭据独立只读联调

Step 4
实现 Dota2UID / GsCore 首个绑定与查询闭环

Step 5
GsCore 加载、重载、卸载与授权命令实机验证

Step 6
定义共享展示模型、图片 Renderer 资源/授权和文本回退规则

Step 7
实现 Dota2UID 图片帮助、玩家卡和近期战绩卡，并实机验证

Step 8
扩展 STRATZ 按比赛 ID 的单场详情契约、Provider、用例和详情卡

Step 9
实现 AstrBot 对相同 Core/Renderer/详情用例的消费并验证生命周期

Step 10
接入 OpenDota 独立补充与交叉核验；Valve 按需

Step 11
单独定义并验证缓存、刷新与有限重试策略

Step 12
扩展 IMP、经济/购买序列和时间序列，逐项核对口径

Step 13
订阅系统

Step 14
AI能力

Step 15
Docker / Integration Pack
```

不要跳过 Core 直接开发 Bot 插件。

---

# 31. Codex 第一阶段执行提示词

以下内容可以直接交给 Codex：

```text
你现在需要创建一个新的开源项目 Dota2Forge。

请严格阅读仓库中的 PROJECT_PLAN.md，并按照其中的架构要求进行开发。

这是一个 Monorepo 项目。

项目核心原则：

1. dota2forge_core 是一个完全与 Bot 框架无关的 Dota 2 Python SDK / Business Core。

2. dota2forge_core 禁止依赖 AstrBot、GsCore、NapCat、OneBot、NoneBot。

3. AstrBot 和 GsCore 都只是 Adapter。

4. 所有 Dota 2 API 访问必须通过 Provider Interface。

5. 所有数据存储必须通过 Repository Interface。

6. Core 不允许直接发送消息，不允许注册 Bot 命令，不允许启动永久 Scheduler。

7. 优先开发：
   Dota2Forge Core
   →
   AstrBot Adapter
   →
   GsCore Adapter
   →
   最后才开发 Integration Pack。

第一阶段暂时不要实现全部业务。

首先完成：

- Monorepo 基础目录
- pyproject.toml
- Ruff
- Pyright
- pytest
- GitHub Actions
- dota2forge_core package
- Domain Model 基础定义
- Provider Protocol
- Repository Protocol
- Config
- Exception Model
- SteamID 转换工具
- 单元测试

完成后停止继续扩展功能。

输出：

1. 创建的目录结构
2. 设计说明
3. 已完成内容
4. 尚未完成内容
5. 测试结果
6. 下一阶段建议

禁止为了快速实现而把 AstrBot 或 GsCore 代码写入 Core。
```

---

# 32. 第一版成功标准

项目第一版发布时，应达到：

### Core

```text
独立安装
独立测试
独立调用
```

### AstrBot

用户：

```text
NapCat + AstrBot + Plugin
```

即可使用。

### GsCore

用户：

```text
NapCat + GsCore + Dota2UID
```

即可使用。

### Code Reuse

AstrBot / GsCore 至少：

```text
80% 以上 Dota 2 业务逻辑共享
```

框架代码仅负责 Adapter。

---

# 33. 项目长期方向

未来 Dota2Forge 可以逐步演化为：

```text
Dota2 Data SDK
      +
Dota2 Bot Core
      +
Multi-Bot Adapter
      +
Dota2 Analytics
      +
AI Coach
```

进一步支持：

```text
比赛复盘
英雄池分析
打法分析
出装分析
阵容分析
版本适应性
队友数据
群内排行榜
自动战报
AI教练
```

但所有后续能力仍保持：

```text
Core First
Framework Agnostic
Adapter Thin
```

这一架构原则。

---

# 34. 最终架构结论

Dota2Forge 不属于 AstrBot。

Dota2Forge 也不属于 GsCore。

正确关系是：

```text
                 Dota2Forge Core
                       │
          ┌────────────┴────────────┐
          │                         │
    AstrBot Adapter           GsCore Adapter
          │                         │
       AstrBot                    GsCore
```

其中：

```text
Dota2Forge Core
```

才是真正长期维护和积累价值的核心资产。

AstrBot 与 GsCore 是两套一等公民级宿主平台。

整合包只负责降低部署门槛，不参与核心业务设计。
