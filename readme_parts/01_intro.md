<div align="center">
  <img src="nanobot_logo.png" alt="nanobot" width="500">
  <h1>nanobot：超轻量级个人 AI 代理</h1>
  <p>
    <a href="https://pypi.org/project/nanobot-ai/"><img src="https://img.shields.io/pypi/v/nanobot-ai" alt="PyPI"></a>
    <a href="https://pepy.tech/project/nanobot-ai"><img src="https://static.pepy.tech/badge/nanobot-ai" alt="Downloads"></a>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat&logo=feishu&logoColor=white" alt="Feishu"></a>
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat&logo=wechat&logoColor=white" alt="WeChat"></a>
    <a href="https://discord.gg/MnCvHqpUGB"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

🐈 **nanobot** 是一个**超轻量级**个人 AI 代理，灵感来自 [OpenClaw](https://github.com/openclaw/openclaw)。

⚡️ 以**99%更少的代码行数**实现核心代理功能。

📏 实时代码行数：随时运行 `bash core_agent_lines.sh` 验证。

## 📢 新闻

- **2026-04-04** 🚀 Jinja2 响应模板、Dream 内存强化、更智能的重试处理。
- **2026-04-03** 🧠 小米 MiMo 提供器、可见的思维链推理、Telegram UX 优化。
- **2026-04-02** 🧱 **长时间运行任务**更可靠 — 核心运行时强化。
- **2026-04-01** 🔑 GitHub Copilot 认证恢复；更严格的工作区路径；OpenRouter Claude 缓存修复。
- **2026-03-31** 🛰️ 微信多模态对齐、Discord/Matrix 优化、Python SDK 门面、MCP 和工具修复。
- **2026-03-30** 🧩 OpenAI 兼容 API 收紧；可组合代理生命周期钩子。
- **2026-03-29** 💬 微信语音、输入状态、QR/媒体恢复；固定会话的 OpenAI 兼容 API。
- **2026-03-28** 📚 提供器文档刷新；技能模板措辞修复。
- **2026-03-27** 🚀 发布 **v0.1.4.post6** — 架构解耦、移除 litellm、端到端流式、微信渠道和安全修复。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.4.post6)。
- **2026-03-26** 🏗️ 提取代理运行器并统一生命周期钩子；边界处的流式增量合并。
- **2026-03-25** 🌏 StepFun 提供器、可配置时区、Gemini 思考签名。
- **2026-03-24** 🔧 微信兼容性、飞书 CardKit 流式、测试套件重构。

<details>
<summary>早期新闻</summary>

- **2026-03-23** 🔧 命令路由重构支持插件、WhatsApp/微信媒体、统一渠道登录 CLI。
- **2026-03-22** ⚡ 端到端流式、微信渠道、Anthropic 缓存优化、`/status` 命令。
- **2026-03-21** 🔒 用原生 `openai` + `anthropic` SDK 替换 `litellm`。详见[提交](https://github.com/HKUDS/nanobot/commit/3dfdab7)。
- **2026-03-20** 🧙 交互式设置向导 — 选择提供器、模型自动补全，即刻开始。
- **2026-03-19** 💬 Telegram 在高负载下更稳定；飞书现在正确渲染代码块。
- **2026-03-18** 📷 Telegram 现可通过 URL 发送媒体。Cron 调度显示人类可读详情。
- **2026-03-17** ✨ 飞书格式美化、Slack 完成时反应、自定义端点支持额外请求头、图像处理更可靠。
- **2026-03-16** 🚀 发布 **v0.1.4.post5** — 专注于优化的版本，更强的可靠性和渠道支持，更稳定的日常体验。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.4.post5)。
- **2026-03-15** 🧩 钉钉富媒体、更智能的内置技能、更整洁的模型兼容性。
- **2026-03-14** 💬 渠道插件、飞书回复、更稳定的 MCP、QQ 和媒体处理。
- **2026-03-13** 🌐 多提供器网络搜索、LangSmith、更广泛的可靠性改进。
- **2026-03-12** 🚀 火山引擎支持、Telegram 回复上下文、`/restart`、更稳固的内存。
- **2026-03-11** 🔌 企业微信、Ollama、更简洁的发现机制、更安全的工具行为。
- **2026-03-10** 🧠 基于 token 的内存、共享重试、更整洁的 gateway 和 Telegram 行为。
- **2026-03-09** 💬 Slack 线程优化、更好的飞书音频兼容性。
- **2026-03-08** 🚀 发布 **v0.1.4.post4** — 可靠性满满的版本，更安全的默认设置、更好的多实例支持、更稳固的 MCP、主要的渠道和提供器改进。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.4.post4)。
- **2026-03-07** 🚀 Azure OpenAI 提供器、WhatsApp 媒体、QQ 群聊、更多 Telegram/飞书优化。
- **2026-03-06** 🪄 更轻量的提供器、更智能的媒体处理、更稳固的内存和 CLI 兼容性。
- **2026-03-05** ⚡️ Telegram 草稿流式、MCP SSE 支持、更广泛的渠道可靠性修复。
- **2026-03-04** 🛠️ 依赖清理、更安全的文件读取、又一轮测试和 Cron 修复。
- **2026-03-03** 🧠 更整洁的用户消息合并、更安全的多模态保存、更强的 Cron 保护。
- **2026-03-02** 🛡️ 更安全的默认访问控制、更稳固的 Cron 重载、更整洁的 Matrix 媒体处理。
- **2026-03-01** 🌐 Web 代理支持、更智能的 Cron 提醒、飞书富文本解析改进。
- **2026-02-28** 🚀 发布 **v0.1.4.post3** — 更整洁的上下文、强化的会话历史、更智能的代理。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.4.post3)。
- **2026-02-27** 🧠 实验性思考模式支持、钉钉媒体消息、飞书和 QQ 渠道修复。
- **2026-02-26** 🛡️ 会话污染修复、WhatsApp 去重、Windows 路径保护、Mistral 兼容性。
- **2026-02-25** 🧹 新 Matrix 渠道、更整洁的会话上下文、自动工作区模板同步。
- **2026-02-24** 🚀 发布 **v0.1.4.post2** — 专注于可靠性的版本，重新设计的心跳、提示缓存优化、强化的提供器和渠道稳定性。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.4.post2)。
- **2026-02-23** 🔧 虚拟工具调用心跳、提示缓存优化、Slack mrkdwn 修复。
- **2026-02-22** 🛡️ Slack 线程隔离、Discord 输入状态修复、代理可靠性改进。
- **2026-02-21** 🎉 发布 **v0.1.4.post1** — 新提供器、跨渠道媒体支持、主要稳定性改进。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.4.post1)。
- **2026-02-20** 🐦 飞书现在接收用户多模态文件。底层内存更可靠。
- **2026-02-19** ✨ Slack 现发送文件、Discord 分割长消息、子代理在 CLI 模式下工作。
- **2026-02-18** ⚡️ nanobot 现支持火山引擎、MCP 自定义认证请求头、Anthropic 提示缓存。
- **2026-02-17** 🎉 发布 **v0.1.4** — MCP 支持、进度流式、新提供器、多渠道改进。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.4)。
- **2026-02-16** 🦞 nanobot 集成 [ClawHub](https://clawhub.ai) 技能 — 搜索和安装公共代理技能。
- **2026-02-15** 🔑 nanobot 现支持 OpenAI Codex 提供器，带 OAuth 登录支持。
- **2026-02-14** 🔌 nanobot 现支持 MCP！详见 [MCP 部分](#mcp-model-context-protocol)。
- **2026-02-13** 🎉 发布 **v0.1.3.post7** — 包含安全强化和多项改进。**请升级到最新版本以解决安全问题**。详见[发布说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.3.post7)。
- **2026-02-12** 🧠 重新设计内存系统 — 更少代码，更可靠。加入[讨论](https://github.com/HKUDS/nanobot/discussions/566)！
- **2026-02-11** ✨ 增强 CLI 体验，添加 MiniMax 支持！
- **2026-02-10** 🎉 发布 **v0.1.3.post6**，多项改进！查看[更新说明](https://github.com/HKUDS/nanobot/releases/tag/v0.1.3.post6)和我们的[路线图](https://github.com/HKUDS/nanobot/discussions/431)。
- **2026-02-09** 💬 添加 Slack、Email 和 QQ 支持 — nanobot 现支持多聊天平台！
- **2026-02-08** 🔧 重构提供器 — 添加新 LLM 提供器仅需 2 步！查看[这里](#providers)。
- **2026-02-07** 🚀 发布 **v0.1.3.post5**，支持 Qwen 和多项关键改进！详见[这里](https://github.com/HKUDS/nanobot/releases/tag/v0.1.3.post5)。
- **2026-02-06** ✨ 添加 Moonshot/Kimi 提供器、Discord 集成，增强安全强化！
- **2026-02-05** ✨ 添加飞书渠道、DeepSeek 提供器，增强定时任务支持！
- **2026-02-04** 🚀 发布 **v0.1.3.post4**，多提供器和 Docker 支持！详见[这里](https://github.com/HKUDS/nanobot/releases/tag/v0.1.3.post4)。
- **2026-02-03** ⚡ 集成 vLLM 支持本地 LLM，改进自然语言任务调度！
- **2026-02-02** 🎉 nanobot 正式发布！欢迎试用 🐈 nanobot！

</details>

> 🐈 nanobot 仅用于教育、研究和技术交流目的。它与加密货币无关，不涉及任何官方代币或硬币。

## nanobot 核心特性：

🪶 **超轻量级**：为稳定、长时间运行的 AI 代理构建的轻量级实现。

🔬 **研究就绪**：代码整洁易读，便于理解、修改和扩展研究。

⚡️ **闪电快速**：最小占用意味着更快启动、更低资源消耗、更短迭代周期。

💎 **易于使用**：一键部署，即刻上手。

## 🏗️ 架构

<p align="center">
  <img src="nanobot_arch.png" alt="nanobot architecture" width="800">
</p>