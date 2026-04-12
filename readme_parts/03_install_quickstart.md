## 📦 安装

> [!IMPORTANT]
> 本 README 可能描述了最新源代码中首先发布的功能。
> 如需最新功能和实验性改动，请从源码安装。
> 如需最稳定的日常体验，请从 PyPI 或使用 `uv` 安装。

**从源码安装**（最新功能，实验性改动可能首先在此发布；推荐用于开发）

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .
```

**使用 [uv](https://github.com/astral-sh/uv) 安装**（稳定版本，快速）

```bash
uv tool install nanobot-ai
```

**从 PyPI 安装**（稳定版本）

```bash
pip install nanobot-ai
```

### 更新到最新版本

**PyPI / pip**

```bash
pip install -U nanobot-ai
nanobot --version
```

**uv**

```bash
uv tool upgrade nanobot-ai
nanobot --version
```

**使用 WhatsApp？** 升级后重建本地桥接：

```bash
rm -rf ~/.nanobot/bridge
nanobot channels login whatsapp
```

## 🚀 快速开始

> [!TIP]
> 在 `~/.nanobot/config.json` 中设置 API 密钥。
> 获取 API 密钥：[OpenRouter](https://openrouter.ai/keys)（全球通用）
>
> 其他 LLM 提供器请参见 [提供器](#providers) 部分。
>
> 网络搜索功能设置请参见 [网络搜索](#web-search)。

**1. 初始化**

```bash
nanobot onboard
```

如需交互式设置向导，使用 `nanobot onboard --wizard`。

**2. 配置** (`~/.nanobot/config.json`)

配置以下**两个部分**（其他选项有默认值）。

*设置 API 密钥*（如 OpenRouter，推荐全球用户）：
```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  }
}
```

*设置模型*（可选固定提供器 — 默认自动检测）：
```json
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5",
      "provider": "openrouter"
    }
  }
}
```

**3. 开始聊天**

```bash
nanobot agent
```

搞定！2 分钟即可拥有一个工作的 AI 代理。