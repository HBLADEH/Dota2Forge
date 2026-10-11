# README 居中导航的 HTML 链接

Category: operations
Related task: [导航任务](../../tasks/done/2026-10-12-readme-navigation-center.md)
Related code: [生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [AstrBot README](../../../adapters/astrbot_plugin_dota2forge/README.md)

## Problem
用户要求 AstrBot README 顶部导航居中。已有生成器只转换Markdown链接，直接改用HTML会使公开分发的安装/日志/主仓链接失效。

## Decision
四项导航使用 p align=center 和 a href，保留文字与原始目标。生成器同时处理Markdown和HTML的安装页、源码文档、许可和Cloud链接；source_ref及平台分发边界不变。

## Alternatives considered
把Markdown包在HTML段落内的渲染结果不可靠。直接硬编码所有远端链接会丢失本地安装页及source_ref，因此保持源码相对链接并由生成器转换。

## Consequences
只改变指定导航排版和分发转换。现有链接检查包含href，保留源码固定引用与公开安装断言，不改截图、业务或版本；未公开发布。

## Verification
现有断言同步HTML形式，本地候选四项导航和固定source_ref逐一通过；统一离线入口退出0，Ruff/mypy、禁网测试和全部覆盖率门槛通过。实际命令及未验证项见关联任务。
