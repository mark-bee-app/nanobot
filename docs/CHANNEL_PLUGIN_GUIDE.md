# 渠道插件指南

三个步骤构建自定义 nanobot 渠道：子类化、打包、安装。

> **注意：** 我们建议基于 nanobot 的源码检出（`pip install -e .`）开发渠道插件，而不是 PyPI 发布版本，这样你可以始终访问最新的 base-channel 功能和 API。

## 工作原理

nanobot 通过 Python [入口点](https://packaging.python.org/en/latest/specifications/entry-points/) 发现渠道插件。当 `nanobot gateway` 启动时，它会扫描：

1. `nanobot/channels/` 中的内置渠道
2. 在 `nanobot.channels` 入口点组下注册的外部包

如果匹配的配置节有 `"enabled": true`，渠道就会被实例化并启动。

## 快速开始

我们将构建一个最小的 webhook 渠道，通过 HTTP POST 接收消息并发送回复。

### 项目结构

```
nanobot-channel-webhook/
├── nanobot_channel_webhook/
│   ├── __init__.py          # 重导出 WebhookChannel
│   └── channel.py           # 渠道实现
└── pyproject.toml
```

### 1. 创建你的渠道

```python
# nanobot_channel_webhook/__init__.py
from nanobot_channel_webhook.channel import WebhookChannel

__all__ = ["WebhookChannel"]
```

```python
# nanobot_channel_webhook/channel.py
import asyncio
from typing import Any

from aiohttp import web
from loguru import logger

from nanobot.channels.base import BaseChannel
from nanobot.bus.events import OutboundMessage


class WebhookChannel(BaseChannel):
    name = "webhook"
    display_name = "Webhook"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"enabled": False, "port": 9000, "allowFrom": []}

    async def start(self) -> None:
        """启动一个 HTTP 服务器来监听传入消息。

        重要：start() 必须永远阻塞（或直到调用 stop()）。
        如果它返回，渠道被视为已死亡。
        """
        self._running = True
        port = self.config.get("port", 9000)

        app = web.Application()
        app.router.add_post("/message", self._on_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info("Webhook 监听在 :{}", port)

        # 阻塞直到停止
        while self._running:
            await asyncio.sleep(1)

        await runner.cleanup()

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        """投递出站消息。

        msg.content  — markdown 文本（根据需要转换为平台格式）
        msg.media    — 要附加的本地文件路径列表
        msg.chat_id  — 接收者（与你传给 _handle_message 的 chat_id 相同）
        msg.metadata — 可能包含 "_progress": True 用于流式块
        """
        logger.info("[webhook] -> {}: {}", msg.chat_id, msg.content[:80])
        # 在真实插件中：POST 到回调 URL，通过 SDK 发送等

    async def _on_request(self, request: web.Request) -> web.Response:
        """处理传入的 HTTP POST。"""
        body = await request.json()
        sender = body.get("sender", "unknown")
        chat_id = body.get("chat_id", sender)
        text = body.get("text", "")
        media = body.get("media", [])       # URL 列表

        # 这是关键调用：验证 allowFrom，然后将
        # 消息放到总线上供代理处理。
        await self._handle_message(
            sender_id=sender,
            chat_id=chat_id,
            content=text,
            media=media,
        )

        return web.json_response({"ok": True})
```

### 2. 注册入口点

```toml
# pyproject.toml
[project]
name = "nanobot-channel-webhook"
version = "0.1.0"
dependencies = ["nanobot", "aiohttp"]

[project.entry-points."nanobot.channels"]
webhook = "nanobot_channel_webhook:WebhookChannel"

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends._legacy:_Backend"
```

键（`webhook`）成为配置节名称。值指向你的 `BaseChannel` 子类。

### 3. 安装和配置

```bash
pip install -e .
nanobot plugins list      # 验证 "Webhook" 显示为 "plugin"
nanobot onboard           # 自动为检测到的插件添加默认配置
```

编辑 `~/.nanobot/config.json`：

```json
{
  "channels": {
    "webhook": {
      "enabled": true,
      "port": 9000,
      "allowFrom": ["*"]
    }
  }
}
```

### 4. 运行和测试

```bash
nanobot gateway
```

在另一个终端：

```bash
curl -X POST http://localhost:9000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "user1", "chat_id": "user1", "text": "你好!"}'
```

代理接收消息并处理它。回复到达你的 `send()` 方法。

## BaseChannel API

### 必需（抽象）

| 方法 | 描述 |
|------|------|
| `async start()` | **必须永远阻塞。** 连接到平台，监听消息，对每条消息调用 `_handle_message()`。如果此方法返回，渠道就会死亡。 |
| `async stop()` | 设置 `self._running = False` 并清理。在 gateway 关闭时调用。 |
| `async send(msg: OutboundMessage)` | 将出站消息投递到平台。 |

### 交互式登录

如果你的渠道需要交互式认证（例如扫码登录），重写 `login(force=False)`：

```python
async def login(self, force: bool = False) -> bool:
    """
    执行渠道特定的交互式登录。

    参数:
        force: 如果为 True，忽略现有凭据并重新认证。

    如果已认证或登录成功则返回 True。
    """
    # 对于基于二维码的登录：
    # 1. 如果 force，清除保存的凭据
    # 2. 检查是否已认证（从磁盘/状态加载）
    # 3. 如果没有，显示二维码并轮询确认
    # 4. 成功时保存 token
```

不需要交互式登录的渠道（例如使用 bot token 的 Telegram，使用 bot token 的 Discord）继承默认的 `login()`，它只返回 `True`。

用户通过以下命令触发交互式登录：
```bash
nanobot channels login <channel_name>
nanobot channels login <channel_name> --force  # 重新认证
```

### 基类提供

| 方法 / 属性 | 描述 |
|------------|------|
| `_handle_message(sender_id, chat_id, content, media?, metadata?, session_key?)` | **收到消息时调用此方法。** 检查 `is_allowed()`，然后发布到总线。如果 `supports_streaming` 为 true，自动设置 `_wants_stream`。 |
| `is_allowed(sender_id)` | 检查 `config["allowFrom"]`；`"*"` 允许所有，`[]` 拒绝所有。 |
| `default_config()` (类方法) | 为 `nanobot onboard` 返回默认配置字典。重写以声明你的字段。 |
| `transcribe_audio(file_path)` | 通过 Groq Whisper 转录音频（如果已配置）。 |
| `supports_streaming` (属性) | 当配置有 `"streaming": true` **且** 子类重写了 `send_delta()` 时为 `True`。 |
| `is_running` | 返回 `self._running`。 |
| `login(force=False)` | 执行交互式登录（例如扫码）。如果已认证或登录成功则返回 `True`。在支持交互式登录的子类中重写。 |

### 可选（流式）

| 方法 | 描述 |
|------|------|
| `async send_delta(chat_id, delta, metadata?)` | 重写以接收流式块。详见[流式支持](#流式支持)。 |

### 消息类型

```python
@dataclass
class OutboundMessage:
    channel: str        # 你的渠道名称
    chat_id: str        # 接收者（与你传给 _handle_message 的值相同）
    content: str        # markdown 文本 — 根据需要转换为平台格式
    media: list[str]    # 要附加的本地文件路径（图片、音频、文档）
    metadata: dict      # 可能包含: "_progress" (bool) 用于流式块,
                        #              "message_id" 用于回复线程
```

## 流式支持

渠道可以选择实时流式 — 代理逐 token 发送内容，而不是一条最终消息。这完全是可选的；没有它渠道也能正常工作。

### 工作原理

当**两个**条件都满足时，代理通过你的渠道流式传输内容：

1. 配置有 `"streaming": true`
2. 你的子类重写了 `send_delta()`

如果缺少任一条件，代理会回退到普通的一次性 `send()` 路径。

### 实现 `send_delta`

重写 `send_delta` 来处理两种类型的调用：

```python
async def send_delta(self, chat_id: str, delta: str, metadata: dict[str, Any] | None = None) -> None:
    meta = metadata or {}

    if meta.get("_stream_end"):
        # 流式结束 — 做最终格式化、清理等
        return

    # 常规 delta — 追加文本，更新屏幕上的消息
    # delta 包含一小块文本（几个 token）
```

**元数据标志：**

| 标志 | 含义 |
|------|------|
| `_stream_delta: True` | 内容块（delta 包含新文本） |
| `_stream_end: True` | 流式结束（delta 为空） |
| `_resuming: True` | 更多流式轮次即将到来（例如工具调用后另一个响应） |

### 示例：带流式的 Webhook

```python
class WebhookChannel(BaseChannel):
    name = "webhook"
    display_name = "Webhook"

    def __init__(self, config, bus):
        super().__init__(config, bus)
        self._buffers: dict[str, str] = {}

    async def send_delta(self, chat_id: str, delta: str, metadata: dict[str, Any] | None = None) -> None:
        meta = metadata or {}
        if meta.get("_stream_end"):
            text = self._buffers.pop(chat_id, "")
            # 最终投递 — 格式化并发送完整消息
            await self._deliver(chat_id, text, final=True)
            return

        self._buffers.setdefault(chat_id, "")
        self._buffers[chat_id] += delta
        # 增量更新 — 将部分文本推送给客户端
        await self._deliver(chat_id, self._buffers[chat_id], final=False)

    async def send(self, msg: OutboundMessage) -> None:
        # 非流式路径 — 不变
        await self._deliver(msg.chat_id, msg.content, final=True)
```

### 配置

为每个渠道启用流式：

```json
{
  "channels": {
    "webhook": {
      "enabled": true,
      "streaming": true,
      "allowFrom": ["*"]
    }
  }
}
```

当 `streaming` 为 `false`（默认）或省略时，只调用 `send()` — 没有流式开销。

### BaseChannel 流式 API

| 方法 / 属性 | 描述 |
|------------|------|
| `async send_delta(chat_id, delta, metadata?)` | 重写以处理流式块。默认为空操作。 |
| `supports_streaming` (属性) | 当配置有 `streaming: true` **且** 子类重写 `send_delta` 时返回 `True`。 |

## 配置

你的渠道接收纯 `dict` 作为配置。使用 `.get()` 访问字段：

```python
async def start(self) -> None:
    port = self.config.get("port", 9000)
    token = self.config.get("token", "")
```

`allowFrom` 由 `_handle_message()` 自动处理 — 你不需要自己检查它。

重写 `default_config()` 以便 `nanobot onboard` 自动填充 `config.json`：

```python
@classmethod
def default_config(cls) -> dict[str, Any]:
    return {"enabled": False, "port": 9000, "allowFrom": []}
```

如果不重写，基类返回 `{"enabled": false}`。

## 命名约定

| 内容 | 格式 | 示例 |
|------|------|------|
| PyPI 包 | `nanobot-channel-{name}` | `nanobot-channel-webhook` |
| 入口点键 | `{name}` | `webhook` |
| 配置节 | `channels.{name}` | `channels.webhook` |
| Python 包 | `nanobot_channel_{name}` | `nanobot_channel_webhook` |

## 本地开发

```bash
git clone https://github.com/you/nanobot-channel-webhook
cd nanobot-channel-webhook
pip install -e .
nanobot plugins list    # 应该显示 "Webhook" 为 "plugin"
nanobot gateway         # 端到端测试
```

## 验证

```bash
$ nanobot plugins list

  Name       Source    Enabled
  telegram   builtin  yes
  discord    builtin  no
  webhook    plugin   yes
```