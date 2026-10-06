# CC Switch 背景生成配置

2026-10-05已通过内置image_gen生成并接入标题背景，见[生成记录](../../.agents/artifacts/dota-style-v2/header-generation-v2.json)。本指南保留API/CLI备用配置与历史失败证据；本轮未调用该中转，未验证其权限是否改变。

此前用户已授权imagegen API/CLI生成装饰背景。本机CC Switch为3.20.4，[路由源码](https://github.com/farion1231/cc-switch/blob/v3.20.4/src-tauri/src/proxy/server.rs)注册/v1/images/generations，[处理器](https://github.com/farion1231/cc-switch/blob/v3.20.4/src-tauri/src/proxy/handlers.rs)使用Codex当前供应商转发。用户开启代理后health=healthy；CLI请求gpt-image-2到达供应商，但返回HTTP403：Image generation is not enabled for this group。该次请求未生成位图，分组图片权限不足。

## 启用路由

CC Switch3.20.4打开「设置 → 高级 → 代理服务」（或主界面顶部代理开关）启动本地代理；在路由服务的应用路由区域启用Codex，部分界面称应用接管，保持监听127.0.0.1:15721；菜单名称以安装版本为准。在Codex供应商页面选用支持OpenAI Images API的中转商。供应商需支持POST /v1/images/generations和实际图像模型；文本模型/Responses能用不等于图像可用。

本机已准备被Git忽略的 .env.imagegen，仅含本地路由与占位Key：

```dotenv
OPENAI_BASE_URL=http://127.0.0.1:15721/v1
OPENAI_API_KEY=PROXY_MANAGED
```

占位Key只用于CC Switch本地路由，真实Key由路由按供应商配置注入。CLI使用OpenAI SDK，不自动读取Codex的config.toml或CC Switch配置。若端口不同，更新此文件的地址；不覆盖已有STRATZ .env。

确认供应商支持脚本默认gpt-image-2；实际模型名以供应商控制台为准。若只提供其他gpt-image-*模型，需要显式选择对应 --model，不能把Codex文本模型名称当图像模型。CLI不支持任意非GPT Image模型；中转也需返回data[].b64_json。

## 验证与生成

在仓库根目录使用PowerShell，先只读确认路由可达：

```powershell
Invoke-RestMethod http://127.0.0.1:15721/health
$imageGenCli = 'C:/Users/BLADE/.codex/skills/.system/imagegen/scripts/image_gen.py'
uv run --env-file .env.imagegen --locked python $imageGenCli generate --model gpt-image-2 --prompt-file .agents/artifacts/dota-style-v2/header-prompt.txt --size 1536x1024 --quality medium --no-augment --out output/imagegen/dota-forge-header-v1.png --dry-run
```

dry-run只检查参数/输出路径，无API请求。确认路由和供应商图像模型后，实际生成：

```powershell
uv run --env-file .env.imagegen --no-project --with openai --with pillow python $imageGenCli generate --model gpt-image-2 --prompt-file .agents/artifacts/dota-style-v2/header-prompt.txt --size 1536x1024 --quality medium --no-augment --out output/imagegen/dota-forge-header-v1.png
```

--with依赖安装在隔离环境，不改workspace依赖/锁文件；首次可能联网下载。实际生成使用供应商API额度/计费。已授权CLI，无需重新询问授权；路由可达且模型确认后可继续生成和QA。

如不使用CC Switch本地路由，在本地.env.imagegen填中转商Images API实际基础地址与真实Key；基础地址通常以/v1结尾，不填完整/images/generations。PROXY_MANAGED不能用来直接连接供应商。不要在聊天中粘贴Key，不把文件提交Git。

连接失败先检查路由服务；404检查路径/Images API支持，401/403检查供应商认证/权限，model_not_found检查图像模型。历史请求的403明确要求开通分组图片权限，或在CC Switch切换到已开通Images的供应商；更换尺寸/提示词不能解决分组权限。权限未变时不反复请求；该CLI请求没有成功生成，费用是否扣除以供应商账单为准。

生成后检查无文字/英雄/装备并裁切标题区，保存decor/header.png，更新本地manifest的模型、提示词、时间、SHA256及尺寸，复现390px卡片。接入格式见[本地插图](illustrations.md)。官方英雄/装备仍保持独立下载，后续可规划周期校验，不在本轮创建调度。

来源：[OpenAI Images API](https://developers.openai.com/api/docs/guides/image-generation)、[OpenAI SDK配置](https://github.com/openai/openai-python)、[CC Switch路由说明](https://github.com/farion1231/cc-switch/blob/v3.20.4/docs/user-manual/zh/4-proxy/4.1-service.md)。
