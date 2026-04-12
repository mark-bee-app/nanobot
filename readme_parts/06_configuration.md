## ⚙️ 配置

配置文件：`~/.nanobot/config.json`

> [!NOTE]
> 如果你的配置文件比当前 schema 旧，可以刷新而不覆盖现有值：
> 运行 `nanobot onboard`，然后当询问是否覆盖配置时回答 `N`。
> nanobot 会合并缺失的默认字段并保留你的当前设置。

### 使用环境变量管理密钥

你可以使用 `${VAR_NAME}` 引用在启动时从环境变量解析，而不是将密钥直接存储在 `config.json`：

```json
{
  "channels": {
    "telegram": { "token": "${TELEGRAM_TOKEN}" },
    "email": {
      "imapPassword": "${IMAP_PASSWORD}",
      "smtpPassword": "${SMTP_PASSWORD}"
    }
  },
  "providers": {
    "groq": { "apiKey": "${GROQ_API_KEY}" }
  }
}
```

对于 **systemd** 部署，在服务单元中使用 `EnvironmentFile=` 加载仅部署用户可读的文件：

```ini
# /etc/systemd/system/nanobot.service（摘录）
[Service]
EnvironmentFile=/home/youruser/nanobot_secrets.env
User=nanobot
ExecStart=...
```

```bash
# /home/youruser/nanobot_secrets.env（mode 600，owner youruser）
TELEGRAM_TOKEN=your-token-here
IMAP_PASSWORD=your-password-here
```

### 提供器

> [!TIP]
> - **语音转录**：语音消息（Telegram、WhatsApp）自动使用 Whisper 转录。默认使用 Groq（免费 tier）。在 `channels` 下设置 `"transcriptionProvider": "openai"` 使用 OpenAI Whisper — API 密钥从匹配的提供器配置中获取。
> - **MiniMax Coding Plan**：nanobot 社区专属折扣链接：[海外](https://platform.minimax.io/subscribe/coding-plan?code=9txpdXw04g&source=link) · [中国大陆](https://platform.minimaxi.com/subscribe/token-plan?code=GILTJpMTqZ&source=link)
> - **MiniMax（中国大陆）**：如果你的 API 密钥来自 MiniMax 中国大陆平台（minimaxi.com），在 minimax 提供器配置中设置 `"apiBase": "https://api.minimaxi.com/v1"`。
> - **火山引擎 / BytePlus Coding Plan**：使用专用提供器 `volcengineCodingPlan` 或 `byteplusCodingPlan` 而非按量付费的 `volcengine` / `byteplus` 提供器。
> - **智谱 Coding Plan**：如果你使用智谱 coding plan，在 zhipu 提供器配置中设置 `"apiBase": "https://open.bigmodel.cn/api/coding/paas/v4"`。
> - **阿里云百炼**：如果使用阿里云百炼的 OpenAI 兼容端点，在 dashscope 提供器配置中设置 `"apiBase": "https://dashscope.aliyuncs.com/compatible-mode/v1"`。
> - **Step Fun（中国大陆）**：如果你的 API 密钥来自 Step Fun 中国大陆平台（stepfun.com），在 stepfun 提供器配置中设置 `"apiBase": "https://api.stepfun.com/v1"`。

| 提供器 | 用途 | 获取 API Key |
|----------|---------|-------------|
| `custom` | 任意 OpenAI 兼容端点 | — |
| `openrouter` | LLM（推荐，访问所有模型） | [openrouter.ai](https://openrouter.ai) |
| `volcengine` | LLM（火山引擎，按量付费） | [Coding Plan](https://www.volcengine.com/activity/codingplan?utm_campaign=nanobot&utm_content=nanobot&utm_medium=devrel&utm_source=OWO&utm_term=nanobot) · [volcengine.com](https://www.volcengine.com) |
| `byteplus` | LLM（火山引擎国际版，按量付费） | [Coding Plan](https://www.byteplus.com/en/activity/codingplan?utm_campaign=nanobot&utm_content=nanobot&utm_medium=devrel&utm_source=OWO&utm_term=nanobot) · [byteplus.com](https://www.byteplus.com) |
| `anthropic` | LLM（Claude 直连） | [console.anthropic.com](https://console.anthropic.com) |
| `azure_openai` | LLM（Azure OpenAI） | [portal.azure.com](https://portal.azure.com) |
| `openai` | LLM + 语音转录（Whisper） | [platform.openai.com](https://platform.openai.com) |
| `deepseek` | LLM（DeepSeek 直连） | [platform.deepseek.com](https://platform.deepseek.com) |
| `groq` | LLM + 语音转录（Whisper，默认） | [console.groq.com](https://console.groq.com) |
| `minimax` | LLM（MiniMax 直连） | [platform.minimaxi.com](https://platform.minimaxi.com) |
| `gemini` | LLM（Gemini 直连） | [aistudio.google.com](https://aistudio.google.com) |
| `aihubmix` | LLM（API 网关，访问所有模型） | [aihubmix.com](https://aihubmix.com) |
| `siliconflow` | LLM（SiliconFlow/硅基流动） | [siliconflow.cn](https://siliconflow.cn) |
| `dashscope` | LLM（Qwen） | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |
| `moonshot` | LLM（Moonshot/Kimi） | [platform.moonshot.cn](https://platform.moonshot.cn) |
| `zhipu` | LLM（智谱 GLM） | [open.bigmodel.cn](https://open.bigmodel.cn) |
| `mimo` | LLM（MiMo） | [platform.xiaomimimo.com](https://platform.xiaomimimo.com) |
| `ollama` | LLM（本地，Ollama） | — |
| `mistral` | LLM | [docs.mistral.ai](https://docs.mistral.ai/) |
| `stepfun` | LLM（Step Fun/阶跃星辰） | [platform.stepfun.com](https://platform.stepfun.com) |
| `ovms` | LLM（本地，OpenVINO Model Server） | [docs.openvino.ai](https://docs.openvino.ai/2026/model-server/ovms_docs_llm_quickstart.html) |
| `vllm` | LLM（本地，任意 OpenAI 兼容服务器） | — |
| `openai_codex` | LLM（Codex，OAuth） | `nanobot provider login openai-codex` |
| `github_copilot` | LLM（GitHub Copilot，OAuth） | `nanobot provider login github-copilot` |
| `qianfan` | LLM（百度千帆） | [cloud.baidu.com](https://cloud.baidu.com/doc/qianfan/s/Hmh4suq26) |


<details>
<summary><b>OpenAI Codex（OAuth）</b></summary>

Codex 使用 OAuth 而非 API 密钥。需要 ChatGPT Plus 或 Pro 账户。
`config.json` 中无需 `providers.openaiCodex` 块；`nanobot provider login` 将 OAuth session 存储在配置之外。

**1. 登录：**
```bash
nanobot provider login openai-codex
```

**2. 设置模型**（合并到 `~/.nanobot/config.json`）：
```json
{
  "agents": {
    "defaults": {
      "model": "openai-codex/gpt-5.1-codex"
    }
  }
}
```

**3. 聊天：**
```bash
nanobot agent -m "Hello!"

# 本地针对特定工作区/配置
nanobot agent -c ~/.nanobot-telegram/config.json -m "Hello!"

# 在该配置基础上一次性工作区覆盖
nanobot agent -c ~/.nanobot-telegram/config.json -w /tmp/nanobot-telegram-test -m "Hello!"
```

> Docker 用户：使用 `docker run -it` 进行交互式 OAuth 登录。

</details>


<details>
<summary><b>GitHub Copilot（OAuth）</b></summary>

GitHub Copilot 使用 OAuth 而非 API 密钥。需要配置了 [plan](https://github.com/features/copilot/plans) 的 GitHub 账户。
`config.json` 中无需 `providers.githubCopilot` 块；`nanobot provider login` 将 OAuth session 存储在配置之外。

**1. 登录：**
```bash
nanobot provider login github-copilot
```

**2. 设置模型**（合并到 `~/.nanobot/config.json`）：
```json
{
  "agents": {
    "defaults": {
      "model": "github-copilot/gpt-4.1"
    }
  }
}
```

**3. 聊天：**
```bash
nanobot agent -m "Hello!"

# 本地针对特定工作区/配置
nanobot agent -c ~/.nanobot-telegram/config.json -m "Hello!"

# 在该配置基础上一次性工作区覆盖
nanobot agent -c ~/.nanobot-telegram/config.json -w /tmp/nanobot-telegram-test -m "Hello!"
```

> Docker 用户：使用 `docker run -it` 进行交互式 OAuth 登录。

</details>

<details>
<summary><b>自定义提供器（任意 OpenAI 兼容 API）</b></summary>

直接连接任意 OpenAI 兼容端点 — LM Studio、llama.cpp、Together AI、Fireworks、Azure OpenAI 或任意自托管服务器。模型名称按原样传递。

```json
{
  "providers": {
    "custom": {
      "apiKey": "your-api-key",
      "apiBase": "https://api.your-provider.com/v1"
    }
  },
  "agents": {
    "defaults": {
      "model": "your-model-name"
    }
  }
}
```

> 对于不需要密钥的本地服务器，将 `apiKey` 设为任意非空字符串（如 `"no-key"`）。

</details>

<details>
<summary><b>Ollama（本地）</b></summary>

使用 Ollama 运行本地模型，然后添加到配置：

**1. 启动 Ollama**（示例）：
```bash
ollama run llama3.2
```

**2. 添加到配置**（部分 — 合并到 `~/.nanobot/config.json`）：
```json
{
  "providers": {
    "ollama": {
      "apiBase": "http://localhost:11434"
    }
  },
  "agents": {
    "defaults": {
      "provider": "ollama",
      "model": "llama3.2"
    }
  }
}
```

> 当 `providers.ollama.apiBase` 已配置时，`provider: "auto"` 也有效，但设置 `"provider": "ollama"` 是最清晰的选择。

</details>

<details>
<summary><b>OpenVINO Model Server（本地 / OpenAI 兼容）</b></summary>

使用 [OpenVINO Model Server](https://docs.openvino.ai/2026/model-server/ovms_docs_llm_quickstart.html) 在 Intel GPU 上本地运行 LLM。OVMS 在 `/v3` 暴露 OpenAI 兼容 API。

> 需要 Docker 和带驱动访问（`/dev/dri`）的 Intel GPU。

**1. 拉取模型**（示例）：

```bash
mkdir -p ov/models && cd ov

docker run -d \
  --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd)/models:/models \
  openvino/model_server:latest-gpu \
  --pull \
  --model_name openai/gpt-oss-20b \
  --model_repository_path /models \
  --source_model OpenVINO/gpt-oss-20b-int4-ov \
  --task text_generation \
  --tool_parser gptoss \
  --reasoning_parser gptoss \
  --enable_prefix_caching true \
  --target_device GPU
```

> 这会下载模型权重。等待容器完成后再继续。

**2. 启动服务器**（示例）：

```bash
docker run -d \
  --rm \
  --name ovms \
  --user $(id -u):$(id -g) \
  -p 8000:8000 \
  -v $(pwd)/models:/models \
  --device /dev/dri \
  --group-add=$(stat -c "%g" /dev/dri/render* | head -n 1) \
  openvino/model_server:latest-gpu \
  --rest_port 8000 \
  --model_name openai/gpt-oss-20b \
  --model_repository_path /models \
  --source_model OpenVINO/gpt-oss-20b-int4-ov \
  --task text_generation \
  --tool_parser gptoss \
  --reasoning_parser gptoss \
  --enable_prefix_caching true \
  --target_device GPU
```

**3. 添加到配置**（部分 — 合并到 `~/.nanobot/config.json`）：

```json
{
  "providers": {
    "ovms": {
      "apiBase": "http://localhost:8000/v3"
    }
  },
  "agents": {
    "defaults": {
      "provider": "ovms",
      "model": "openai/gpt-oss-20b"
    }
  }
}
```

> OVMS 是本地服务器 — 无需 API 密钥。支持工具调用（`--tool_parser gptoss`）、推理（`--reasoning_parser gptoss`）和流式。
> 更多详情见[官方 OVMS 文档](https://docs.openvino.ai/2026/model-server/ovms_docs_llm_quickstart.html)。
</details>

<details>
<summary><b>vLLM（本地 / OpenAI 兼容）</b></summary>

使用 vLLM 或任意 OpenAI 兼容服务器运行自己的模型，然后添加到配置：

**1. 启动服务器**（示例）：
```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
```

**2. 添加到配置**（部分 — 合并到 `~/.nanobot/config.json`）：

*提供器（本地服务器密钥可为任意非空字符串）：*
```json
{
  "providers": {
    "vllm": {
      "apiKey": "dummy",
      "apiBase": "http://localhost:8000/v1"
    }
  }
}
```

*模型：*
```json
{
  "agents": {
    "defaults": {
      "model": "meta-llama/Llama-3.1-8B-Instruct"
    }
  }
}
```

</details>

<details>
<summary><b>添加新提供器（开发者指南）</b></summary>

nanobot 使用 **Provider Registry**（`nanobot/providers/registry.py`）作为唯一事实来源。
添加新提供器仅需 **2 步** — 无需修改 if-elif 链。

**步骤 1.** 在 `nanobot/providers/registry.py` 的 `PROVIDERS` 中添加 `ProviderSpec` 条目：

```python
ProviderSpec(
    name="myprovider",                   # 配置字段名
    keywords=("myprovider", "mymodel"),  # 用于自动匹配的模型名关键词
    env_key="MYPROVIDER_API_KEY",        # 环境变量名
    display_name="My Provider",          # 在 `nanobot status` 中显示
    default_api_base="https://api.myprovider.com/v1",  # OpenAI 兼容端点
)
```

**步骤 2.** 在 `nanobot/config/schema.py` 的 `ProvidersConfig` 中添加字段：

```python
class ProvidersConfig(BaseModel):
    ...
    myprovider: ProviderConfig = ProviderConfig()
```

搞定！环境变量、模型路由、配置匹配和 `nanobot status` 显示都将自动工作。

**常用 `ProviderSpec` 选项：**

| 字段 | 描述 | 示例 |
|-------|-------------|---------|
| `default_api_base` | OpenAI 兼容基础 URL | `"https://api.deepseek.com"` |
| `env_extras` | 需设置的额外环境变量 | `(("ZHIPUAI_API_KEY", "{api_key}"),)` |
| `model_overrides` | 每模型参数覆盖 | `(("kimi-k2.5", {"temperature": 1.0}),)` |
| `is_gateway` | 可路由任意模型（如 OpenRouter） | `True` |
| `detect_by_key_prefix` | 通过 API 密钥前缀检测网关 | `"sk-or-"` |
| `detect_by_base_keyword` | 通过 API base URL 检测网关 | `"openrouter"` |
| `strip_model_prefix` | 发送到网关前剥离提供器前缀 | `True`（用于 AiHubMix） |
| `supports_max_completion_tokens` | 使用 `max_completion_tokens` 而非 `max_tokens`；对于拒绝同时设置两者的提供器（如火山引擎）必需 | `True` |

</details>

### 渠道设置

适用于所有渠道的全局设置。在 `~/.nanobot/config.json` 的 `channels` 部分配置：

```json
{
  "channels": {
    "sendProgress": true,
    "sendToolHints": false,
    "sendMaxRetries": 3,
    "transcriptionProvider": "groq",
    "telegram": { ... }
  }
}
```

| 设置 | 默认值 | 描述 |
|---------|---------|-------------|
| `sendProgress` | `true` | 将代理文本进度流式发送到渠道 |
| `sendToolHints` | `false` | 流式发送工具调用提示（如 `read_file("…")`） |
| `sendMaxRetries` | `3` | 每条出站消息最大投递尝试次数，包含初始发送（配置范围 0-10，实际最小 1 次） |
| `transcriptionProvider` | `"groq"` | 语音转录后端：`"groq"`（免费 tier，默认）或 `"openai"`。API 密钥从匹配的提供器配置自动解析。 |

#### 重试行为

重试机制设计简洁。

当渠道 `send()` 抛出异常时，nanobot 在渠道管理器层重试。默认 `channels.sendMaxRetries` 为 `3`，计数包含初始发送。

- **尝试 1**：立即发送
- **尝试 2**：`1s` 后重试
- **尝试 3**：`2s` 后重试
- **更高重试预算**：退避继续为 `1s`、`2s`、`4s`，然后保持上限 `4s`
- **临时故障**：网络抖动和临时 API 限制通常在下一次尝试恢复
- **永久故障**：无效 token、已撤销访问或被封渠道会耗尽重试预算并干净失败

> [!NOTE]
> 此设计是有意为之：渠道实现应在投递失败时抛出异常，渠道管理器拥有共享重试策略。
>
> 有些渠道可能仍在内部应用少量 API 特定重试。例如，Telegram 在向管理器暴露最终失败前单独重试超时和流量控制错误。
>
> 如果渠道完全不可达，nanobot 无法通过同一渠道通知用户。查看日志中的 `Failed to send to {channel} after N attempts` 以发现持续投递失败。

### 网络搜索

> [!TIP]
> 在 `tools.web` 中使用 `proxy` 将所有网络请求（搜索 + 获取）路由通过代理：
> ```json
> { "tools": { "web": { "proxy": "http://127.0.0.1:7890" } } }
> ```

nanobot 支持多种网络搜索提供器。在 `~/.nanobot/config.json` 的 `tools.web.search` 下配置。

默认启用网络工具，网络搜索使用 `duckduckgo`，因此搜索开箱即用无需 API 密钥。

如果要完全禁用所有内置网络工具，将 `tools.web.enable` 设为 `false`。这会从发送给 LLM 的工具列表中移除 `web_search` 和 `web_fetch`。

如果需要允许可信私有地址如 Tailscale / CGNAT 地址，可以显式将它们从 SSRF 阻止中豁免：

```json
{
  "tools": {
    "ssrfWhitelist": ["100.64.0.0/10"]
  }
}
```

| 提供器 | 配置字段 | 环境变量备用 | 免费 |
|----------|--------------|------------------|------|
| `brave` | `apiKey` | `BRAVE_API_KEY` | 否 |
| `tavily` | `apiKey` | `TAVILY_API_KEY` | 否 |
| `jina` | `apiKey` | `JINA_API_KEY` | 免费 tier（10M tokens） |
| `searxng` | `baseUrl` | `SEARXNG_BASE_URL` | 是（自托管） |
| `duckduckgo`（默认） | — | — | 是 |

**禁用所有内置网络工具：**
```json
{
  "tools": {
    "web": {
      "enable": false
    }
  }
}
```

**Brave：**
```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "brave",
        "apiKey": "BSA..."
      }
    }
  }
}
```

**Tavily：**
```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "tavily",
        "apiKey": "tvly-..."
      }
    }
  }
}
```

**Jina**（免费 tier，10M tokens）：
```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "jina",
        "apiKey": "jina_..."
      }
    }
  }
}
```

**SearXNG**（自托管，无需 API 密钥）：
```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "searxng",
        "baseUrl": "https://searx.example"
      }
    }
  }
}
```

**DuckDuckGo**（零配置）：
```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "duckduckgo"
      }
    }
  }
}
```

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `enable` | boolean | `true` | 启用或禁用所有内置网络工具（`web_search` + `web_fetch`） |
| `proxy` | string 或 null | `null` | 所有网络请求的代理，例如 `http://127.0.0.1:7890` |

#### `tools.web.search`

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `provider` | string | `"duckduckgo"` | 搜索后端：`brave`、`tavily`、`jina`、`searxng`、`duckduckgo` |
| `apiKey` | string | `""` | Brave 或 Tavily 的 API 密钥 |
| `baseUrl` | string | `""` | SearXNG 的基础 URL |
| `maxResults` | integer | `5` | 每次搜索结果数（1–10） |

### MCP（Model Context Protocol）

> [!TIP]
> 配置格式与 Claude Desktop / Cursor 兼容。你可以直接从任意 MCP server 的 README 复制 MCP server 配置。

nanobot 支持 [MCP](https://modelcontextprotocol.io/) — 连接外部工具服务器并将其作为原生代理工具使用。

在 `config.json` 中添加 MCP servers：

```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
      },
      "my-remote-mcp": {
        "url": "https://example.com/mcp/",
        "headers": {
          "Authorization": "Bearer xxxxx"
        }
      }
    }
  }
}
```

支持两种传输模式：

| 模式 | 配置 | 示例 |
|------|--------|---------|
| **Stdio** | `command` + `args` | 通过 `npx` / `uvx` 的本地进程 |
| **HTTP** | `url` + `headers`（可选） | 远程端点（`https://mcp.example.com/sse`） |

使用 `toolTimeout` 覆盖慢服务器的默认 30s 每次调用超时：

```json
{
  "tools": {
    "mcpServers": {
      "my-slow-server": {
        "url": "https://example.com/mcp/",
        "toolTimeout": 120
      }
    }
  }
}
```

使用 `enabledTools` 仅注册 MCP server 的部分工具：

```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
        "enabledTools": ["read_file", "mcp_filesystem_write_file"]
      }
    }
  }
}
```

`enabledTools` 接受原始 MCP 工具名（如 `read_file`）或包装后的 nanobot 工具名（如 `mcp_filesystem_write_file`）。

- 省略 `enabledTools` 或设为 `["*"]` 注册所有工具。
- 设 `enabledTools` 为 `[]` 不注册该 server 的任何工具。
- 设 `enabledTools` 为非空名称列表仅注册该子集。

MCP 工具在启动时自动发现和注册。LLM 可与内置工具一起使用 — 无需额外配置。



### 安全

> [!TIP]
> 对于生产部署，在配置中设置 `"restrictToWorkspace": true` 和 `"tools.exec.sandbox": "bwrap"` 以沙箱化代理。
> 在 `v0.1.4.post3` 及更早版本，空 `allowFrom` 允许所有发送者。自 `v0.1.4.post4` 起，空 `allowFrom` 默认拒绝所有访问。要允许所有发送者，设置 `"allowFrom": ["*"]`。

| 选项 | 默认值 | 描述 |
|--------|---------|-------------|
| `tools.restrictToWorkspace` | `false` | 当 `true` 时，限制**所有**代理工具（shell、文件读写编辑、列表）到工作区目录。防止路径穿越和越界访问。 |
| `tools.exec.sandbox` | `""` | Shell 命令的沙箱后端。设为 `"bwrap"` 在 [bubblewrap](https://github.com/containers/bubblewrap) 沙箱中包装 exec 调用 — 进程只能看到工作区（读写）和媒体目录（只读）；配置文件和 API 密钥隐藏。自动为文件工具启用 `restrictToWorkspace`。**仅限 Linux** — 需安装 `bwrap`（`apt install bubblewrap`；Docker 镜像预装）。macOS 或 Windows 不可用（bwrap 依赖 Linux kernel namespaces）。 |
| `tools.exec.enable` | `true` | 当 `false` 时，shell `exec` 工具完全不注册。使用此选项完全禁用 shell 命令执行。 |
| `tools.exec.pathAppend` | `""` | 运行 shell 命令时追加到 `PATH` 的额外目录（如 `/usr/sbin` 用于 `ufw`）。 |
| `channels.*.allowFrom` | `[]`（拒绝所有） | 用户 ID 白名单。空则拒绝所有；使用 `["*"]` 允许所有人。 |

**Docker 安全**：官方 Docker 镜像以非 root 用户运行（`nanobot`，UID 1000）并预装 bubblewrap。使用 `docker-compose.yml` 时，容器丢弃所有 Linux capabilities 除 `SYS_ADMIN`（bwrap namespace 隔离所需）。


### 时区

时间是上下文。上下文应精确。

默认情况下，nanobot 使用 `UTC` 作为运行时时间上下文。如果你想让代理按本地时间思考，将 `agents.defaults.timezone` 设为有效的 [IANA timezone name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)：

```json
{
  "agents": {
    "defaults": {
      "timezone": "Asia/Shanghai"
    }
  }
}
```

这影响向模型显示的运行时时间字符串，如运行时上下文和心跳提示。它也成为 cron 调度的默认时区（当 cron 表达式省略 `tz`），以及一次性 `at` 时间的默认时区（当 ISO datetime 无显式偏移）。

常用示例：`UTC`、`America/New_York`、`America/Los_Angeles`、`Europe/London`、`Europe/Berlin`、`Asia/Tokyo`、`Asia/Shanghai`、`Asia/Singapore`、`Australia/Sydney`。

> 需要其他时区？浏览完整 [IANA Time Zone Database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)。