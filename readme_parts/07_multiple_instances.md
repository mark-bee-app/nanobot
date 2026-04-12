## 🧩 多实例运行

使用独立配置和运行时数据同时运行多个 nanobot 实例。使用 `--config` 作为主入口点。在 `onboard` 时可选传递 `--workspace` 来初始化或更新特定实例的已保存工作区。

### 快速开始

如果你希望每个实例从一开始就拥有独立工作区，在初始化时同时传递 `--config` 和 `--workspace`。

**初始化实例：**

```bash
# 创建独立的实例配置和工作区
nanobot onboard --config ~/.nanobot-telegram/config.json --workspace ~/.nanobot-telegram/workspace
nanobot onboard --config ~/.nanobot-discord/config.json --workspace ~/.nanobot-discord/workspace
nanobot onboard --config ~/.nanobot-feishu/config.json --workspace ~/.nanobot-feishu/workspace
```

**配置每个实例：**

编辑 `~/.nanobot-telegram/config.json`、`~/.nanobot-discord/config.json` 等，配置不同的渠道设置。你在 `onboard` 时传递的工作区会保存到每个配置中作为该实例的默认工作区。

**运行实例：**

```bash
# 实例 A - Telegram bot
nanobot gateway --config ~/.nanobot-telegram/config.json

# 实例 B - Discord bot  
nanobot gateway --config ~/.nanobot-discord/config.json

# 实例 C - 飞书 bot，自定义端口
nanobot gateway --config ~/.nanobot-feishu/config.json --port 18792
```

### 路径解析

使用 `--config` 时，nanobot 从配置文件位置派生运行时数据目录。工作区仍来自 `agents.defaults.workspace`，除非你用 `--workspace` 覆盖。

要针对某个实例在本地打开 CLI 会话：

```bash
nanobot agent -c ~/.nanobot-telegram/config.json -m "Hello from Telegram instance"
nanobot agent -c ~/.nanobot-discord/config.json -m "Hello from Discord instance"

# 可选的一次性工作区覆盖
nanobot agent -c ~/.nanobot-telegram/config.json -w /tmp/nanobot-telegram-test
```

> `nanobot agent` 使用所选工作区/配置启动本地 CLI 代理。它不会附加到或代理已运行的 `nanobot gateway` 进程。

| 组件 | 解析来源 | 示例 |
|-----------|---------------|---------|
| **配置** | `--config` 路径 | `~/.nanobot-A/config.json` |
| **工作区** | `--workspace` 或配置 | `~/.nanobot-A/workspace/` |
| **定时任务** | 配置目录 | `~/.nanobot-A/cron/` |
| **媒体/运行时状态** | 配置目录 | `~/.nanobot-A/media/` |

### 工作原理

- `--config` 选择加载哪个配置文件
- 默认情况下，工作区来自该配置中的 `agents.defaults.workspace`
- 如果你传递 `--workspace`，它会覆盖配置文件中的工作区

### 最简设置

1. 将基础配置复制到新实例目录。
2. 为该实例设置不同的 `agents.defaults.workspace`。
3. 使用 `--config` 启动实例。

示例配置：

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot-telegram/workspace",
      "model": "anthropic/claude-sonnet-4-6"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_TELEGRAM_BOT_TOKEN"
    }
  },
  "gateway": {
    "port": 18790
  }
}
```

启动独立实例：

```bash
nanobot gateway --config ~/.nanobot-telegram/config.json
nanobot gateway --config ~/.nanobot-discord/config.json
```

需要时可覆盖工作区进行一次性运行：

```bash
nanobot gateway --config ~/.nanobot-telegram/config.json --workspace /tmp/nanobot-telegram-test
```

### 常见用途

- 为 Telegram、Discord、飞书等平台运行独立 bot
- 保持测试和生产实例隔离
- 为不同团队使用不同模型或提供器
- 为多租户提供独立配置和运行时数据

### 注意事项

- 各实例同时运行时必须使用不同端口
- 如需隔离的内存、会话和技能，每个实例使用不同工作区
- `--workspace` 覆盖配置文件中定义的工作区
- 定时任务和运行时媒体/状态从配置目录派生