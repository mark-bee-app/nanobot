# nanobot 架构概览

本文档提供了 `nanobot` 架构的高层概览，旨在帮助 AI 代理和开发者快速理解代码库结构，从而更高效地进行开发、重构、测试和调试。

## 1. 项目概览

`nanobot` 是一个基于 Python (3.11+) 编写的超轻量级个人 AI 助手框架。

### 核心组件
- **代理循环 (Agent Loop)** (`nanobot/agent/loop.py`)：nanobot 的核心。负责接收消息、运行大语言模型 (LLM) 迭代以及执行工具。它使用 `AgentRunner` 与 LLM 交互，并管理会话上下文、内存和工具执行。
- **LLM 提供者 (LLM Providers)** (`nanobot/providers/`)：通过 `LLMProvider` 基类抽象出 LLM 的集成。采用注册表系统 (`nanobot/providers/registry.py`) 方便地添加新的提供者（如 Anthropic、OpenAI、DeepSeek、Ollama、vLLM 等），无需使用 `if-elif` 语句链。
- **消息渠道 (Message Channels)** (`nanobot/channels/`)：各种聊天平台（如 Telegram、Discord、Slack、飞书、WhatsApp、微信等）的适配器，提供统一的发送/接收接口。包含一个渠道管理器用于处理消息合并和重试。
- **工具 (Tools)** (`nanobot/agent/tools/`)：代理的功能扩展（如 `web_search`、`read_file`、`exec`、`mcp` 等）。工具通过 `ToolRegistry` 进行注册，并能自动生成 Pydantic 结构。内置强制安全边界（如防范 SSRF、沙盒执行）。
- **技能 (Skills)** (`nanobot/skills/`)：采用 Markdown 编写 (`SKILL.md`) 并包含 YAML Frontmatter 元数据的特定领域能力定义，在代理启动时加载。
- **内存系统 (Memory System)** (`nanobot/agent/memory.py`)：采用两阶段设计：`Consolidator` 负责总结旧对话，`Dream` 负责筛选并生成长期知识。使用模板（如 `SOUL.md` 表示代理身份，`USER.md` 和 `MEMORY.md` 表示项目事实）。
- **会话管理器 (Session Manager)** (`nanobot/session/manager.py`)：管理每个会话的对话状态（`Session` 对象），处理历史记录持久化（仅限追加）、Token 计数和上下文构建。
- **命令路由 (Command Routing)** (`nanobot/command/`)：注册并路由聊天命令（如 `/status`、`/dream`、`/restart`、`/memory`）。
- **定时任务服务 (Cron Service)** (`nanobot/cron/`)：支持 cron 表达式或基于间隔的调度，驱动 Dream 模块定期运行及其他用户定义的循环任务。

### 关键设计模式
- **提供者与工具注册表**：支持自动发现与注册功能。
- **钩子系统 (Hook System)**：通过 `AgentHook` 基类进行生命周期拦截（例如：`before_iteration`、`on_stream`、`finalize_content`）。
- **配置 Schema**：`nanobot/config/schema.py` 中的 Pydantic 模型，支持使用 `${VAR_NAME}` 语法进行环境变量插值，同时包含向下兼容迁移逻辑。

## 2. 构建与命令

**开发环境设置：**
```bash
# 安装开发依赖
pip install -e ".[dev]"
```

**测试与代码检查：**
```bash
# 运行所有测试
pytest

# 运行单个测试
pytest tests/path/to/test_file.py::test_name

# 代码检查 (Lint)
ruff check nanobot/

# 代码格式化
ruff format nanobot/
```

**分支策略：**
- `main`：稳定版本（Bug 修复和文档更新的首选目标）。
- `nightly`：用于实验性功能和重构。当功能稳定后，通过 cherry-pick 合并到 `main`。

## 3. 代码风格

该项目强调简单、清晰、解耦和高可维护性。

- **格式化和代码检查工具**：`ruff`
- **行长限制**：100 个字符
- **目标 Python 版本**：3.11+
- **Lint 规则**：启用 `E`、`F`、`I`、`N`、`W`，忽略 `E501`（行过长）。
- **异步编程**：整个代码库广泛使用 `asyncio`。
- **原则**：更看重代码的可读性而不是“黑魔法”；优先考虑小步聚焦的补丁，而不是大范围的重写；只有在明显能降低复杂度时才引入新的抽象。

## 4. 测试

- **测试框架**：`pytest` 与 `pytest-asyncio`。
- **配置**：在 `pyproject.toml` 中配置 `asyncio_mode = "auto"` 以实现无缝异步测试。
- **结构组织**：测试文件位于 `tests/` 目录，按组件分类（例如：`tests/agent/`、`tests/channels/`）。
- **代码覆盖率**：通过 `pytest-cov` 管理，明确排除 `tests/` 目录。过滤了标准的代码覆盖率忽略模式（如 `pragma: no cover`、`raise NotImplementedError`、`if TYPE_CHECKING:` 等）。

## 5. 安全性

安全性至关重要，该框架内置了以下安全控制机制：

- **API 密钥**：必须安全地存储在配置文件中（`~/.nanobot/config.json`，权限为 `0600`）或通过环境变量配置，严禁将密钥提交至版本控制系统。
- **访问控制**：生产环境中必须为各个渠道配置 `allowFrom` 列表。自 `v0.1.4.post4` 版本起，空的 `allowFrom` 列表将默认拒绝所有访问（显式允许所有请配置为 `["*"]`）。
- **Shell 命令执行（`exec` 工具）**：
  - 在 Linux 系统下，强烈推荐启用 `bwrap` 沙盒 (`"tools.exec.sandbox": "bwrap"`) 实现内核级隔离。
  - 启用沙盒将自动激活对于文件工具的 `restrictToWorkspace`。
  - 会阻止危险的 Shell 命令（如 `rm -rf /`，叉炸弹 fork bombs）。
  - 切勿以 `root` 用户运行 nanobot。
- **网络与桥接**：
  - 所有外部 API 调用均强制使用 HTTPS。
  - WhatsApp 桥接器仅绑定在 `127.0.0.1:3001` 上，并支持基于令牌的认证。
- **数据隐私**：本地聊天历史、配置信息及日志等均存放在 `~/.nanobot/` 目录下，应当设置相应的文件系统权限加以保护。

## 6. 配置

- **存储位置**：默认情况下，`nanobot` 的配置、鉴权数据、历史记录和日志都存放在 `~/.nanobot/` 目录下。
- **结构定义与验证**：配置项基于 Pydantic Settings 实现强类型与严格验证。
- **配置迁移**：向后兼容逻辑与配置文件迁移功能统一在 `nanobot/config/loader.py` 中进行管理。
