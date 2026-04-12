# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 在此代码仓库工作提供指导。
所有回复使用中文。
新建的文档使用中文命名。

## 快速开始

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行单个测试
pytest tests/path/to/test_file.py::test_name

# 代码检查
ruff check nanobot/

# 代码格式化
ruff format nanobot/
```

## 高层架构

nanobot 是一个超轻量级个人 AI 代理框架，核心组件如下：

### 核心组件

**代理循环** (`nanobot/agent/loop.py`)
- nanobot 的核心：接收消息、运行 LLM 迭代、执行工具
- 使用 `AgentRunner` 进行 LLM 交互，支持流式输出
- 管理会话上下文、内存合并和工具执行

**LLM 提供器** (`nanobot/providers/`)
- 通过 `LLMProvider` 基类抽象 LLM 集成
- 基于注册表的系统 (`nanobot/providers/registry.py`) — 添加提供器只需 2 步
- 支持：Anthropic、OpenAI、OpenRouter、Groq、DeepSeek、Ollama、vLLM 等

**消息渠道** (`nanobot/channels/`)
- 聊天平台适配器 (Telegram、Discord、Slack、飞书、WhatsApp、微信等)
- 每个渠道实现统一的发送/接收接口
- 渠道管理器处理消息合并和投递重试

**工具** (`nanobot/agent/tools/`)
- 代理能力：`web_search`、`web_fetch`、`read_file`、`edit_file`、`exec`、`spawn`、`mcp` 等
- 通过 `ToolRegistry` 注册，自动生成 schema
- 强制执行安全边界 (如 SSRF 防护、沙盒执行)

**技能** (`nanobot/skills/`)
- Markdown 定义的技能包，包含指令和元数据
- 代理启动时加载，提供领域特定能力
- 格式：`SKILL.md` 含 YAML frontmatter + markdown 指令

**内存系统** (`nanobot/agent/memory.py`)
- 两阶段设计：`Consolidator` (总结旧对话) + `Dream` (策划长期知识)
- 文件：`SOUL.md` (代理身份)、`USER.md` (用户知识)、`memory/MEMORY.md` (项目事实)
- 历史记录在 `memory/history.jsonl` (仅追加、基于游标)

**会话管理器** (`nanobot/session/manager.py`)
- 维护每个会话的对话状态 (`Session` 对象)
- 处理历史持久化、token 计数和上下文构建

**命令路由** (`nanobot/command/`)
- 聊天命令如 `/status`、`/dream`、`/restart`、`/memory`
- 通过 `register_builtin_commands()` 注册，支持可扩展插件

**定时任务服务** (`nanobot/cron/`)
- 支持 cron 表达式或基于间隔的调度
- 驱动 Dream 的定期运行和用户定义的循环任务

### 关键设计模式

**提供器注册表**
- 单一事实来源在 `nanobot/providers/registry.py`
- `ProviderSpec` 条目定义名称、环境变量键、基础 URL、检测规则
- 无 if-elif 链 — 新提供器自动接入配置匹配和路由

**钩子系统**
- `AgentHook` 基类用于生命周期拦截
- 方法：`before_iteration`、`on_stream`、`on_stream_end`、`before_execute_tools`、`after_iteration`、`finalize_content`
- `CompositeHook` 支持错误隔离的扇出；`finalize_content` 以管道方式运行

**工具注册表**
- 基础工具：`BaseTool` 含 `name`、`description`、`parameters` (Pydantic schema)
- 自动注册和发现
- 工具可生成子代理、访问 MCP 服务器、在沙盒中运行 shell 命令

**配置 Schema**
- Pydantic 模型在 `nanobot/config/schema.py`
- 通过 `${VAR_NAME}` 语法进行环境变量插值
- 向后兼容由 `nanobot/config/loader.py` 中的迁移逻辑处理

### 目录结构 (nanobot/)

```
nanobot/
├── agent/           # 核心代理循环、内存、runner、子代理、钩子
├── tools/           # 内置工具实现
├── providers/       # LLM 提供器实现 + 注册表
├── channels/        # 聊天平台适配器
├── command/         # 聊天命令路由
├── cron/            # 定时任务服务
├── session/         # 会话状态管理
├── config/          # 配置 schema、加载、路径
├── security/        # 网络安全、SSRF 防护
├── bus/             # 消息路由事件总线
├── utils/           # 共享工具 (helpers、gitstore、restart、evaluator)
└── templates/       # 代理上下文的 Markdown 模板 (SOUL、USER、MEMORY 等)
```

### 测试

测试位于 `tests/`，使用 pytest：
- `asyncio_mode = "auto"` 在 pyproject.toml 中 — async 测试开箱即用
- 按组件组织：`tests/agent/`、`tests/channels/`、`tests/providers/`、`tests/tools/` 等
- 使用 `pytest -v tests/` 运行完整套件，或指定具体文件/类

### 分支策略

- `main`: 稳定版本
- `nightly`: 实验性功能 (功能稳定后 cherry-pick 到 `main`)
- 新功能/重构目标 `nightly`；bug 修复/文档目标 `main`
