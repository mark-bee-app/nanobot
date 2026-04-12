## 💬 聊天应用

将 nanobot 连接到你喜欢的聊天平台。想构建自己的？参见[渠道插件指南](./docs/CHANNEL_PLUGIN_GUIDE.md)。

| 渠道 | 所需配置 |
|---------|---------------|
| **Telegram** | @BotFather 的 Bot token |
| **Discord** | Bot token + Message Content intent |
| **WhatsApp** | QR 码扫描 (`nanobot channels login whatsapp`) |
| **微信 (Weixin)** | QR 码扫描 (`nanobot channels login weixin`) |
| **飞书** | App ID + App Secret |
| **钉钉** | App Key + App Secret |
| **Slack** | Bot token + App-Level token |
| **Matrix** | Homeserver URL + Access token |
| **Email** | IMAP/SMTP 凭证 |
| **QQ** | App ID + App Secret |
| **企业微信** | Bot ID + Bot Secret |
| **Mochat** | Claw token（可自动设置） |

<details>
<summary><b>Telegram</b>（推荐）</summary>

**1. 创建 bot**
- 打开 Telegram，搜索 `@BotFather`
- 发送 `/newbot`，按提示操作
- 复制 token

**2. 配置**

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

> 你可以在 Telegram 设置中找到你的 **User ID**。显示为 `@yourUserId`。
> 复制此值**不含 `@` 符号**并粘贴到配置文件。


**3. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>Mochat (Claw IM)</b></summary>

默认使用 **Socket.IO WebSocket**，HTTP 轮询作为备用。

**1. 让 nanobot 为你设置 Mochat**

只需向 nanobot 发送此消息（将 `xxx@xxx` 替换为你的真实邮箱）：

```
Read https://raw.githubusercontent.com/HKUDS/MoChat/refs/heads/main/skills/nanobot/skill.md and register on MoChat. My Email account is xxx@xxx Bind me as your owner and DM me on MoChat.
```

nanobot 会自动注册、配置 `~/.nanobot/config.json` 并连接到 Mochat。

**2. 重启网关**

```bash
nanobot gateway
```

搞定 — nanobot 自动完成其余工作！

<br>

<details>
<summary>手动配置（高级）</summary>

如果你倾向于手动配置，在 `~/.nanobot/config.json` 中添加：

> 保持 `claw_token` 私密。只应在 `X-Claw-Token` 请求头中发送到你的 Mochat API 端点。

```json
{
  "channels": {
    "mochat": {
      "enabled": true,
      "base_url": "https://mochat.io",
      "socket_url": "https://mochat.io",
      "socket_path": "/socket.io",
      "claw_token": "claw_xxx",
      "agent_user_id": "6982abcdef",
      "sessions": ["*"],
      "panels": ["*"],
      "reply_delay_mode": "non-mention",
      "reply_delay_ms": 120000
    }
  }
}
```



</details>

</details>

<details>
<summary><b>Discord</b></summary>

**1. 创建 bot**
- 访问 https://discord.com/developers/applications
- 创建应用 → Bot → Add Bot
- 复制 bot token

**2. 启用 intents**
- 在 Bot 设置中，启用 **MESSAGE CONTENT INTENT**
- （可选）如果计划使用基于成员数据的白名单，启用 **SERVER MEMBERS INTENT**

**3. 获取你的 User ID**
- Discord 设置 → 高级 → 启用 **Developer Mode**
- 右键点击你的头像 → **Copy User ID**

**4. 配置**

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"],
      "groupPolicy": "mention"
    }
  }
}
```

> `groupPolicy` 控制 bot 在群组渠道中的响应方式：
> - `"mention"`（默认）— 仅在被 @提及 时响应
> - `"open"` — 响应所有消息
> DM 在发送者位于 `allowFrom` 时始终响应。
> - 如果将群组策略设为 open，创建新线程作为私有线程然后在其中 @ bot。否则线程本身和生成它的渠道会生成 bot 会话。

**5. 邀请 bot**
- OAuth2 → URL Generator
- Scopes: `bot`
- Bot Permissions: `Send Messages`, `Read Message History`
- 打开生成的邀请 URL 并将 bot 添加到你的服务器

**6. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>Matrix (Element)</b></summary>

先安装 Matrix 依赖：

```bash
pip install nanobot-ai[matrix]
```

**1. 创建/选择 Matrix 账户**

- 在你的 homeserver 上创建或复用 Matrix 贴户（例如 `matrix.org`）。
- 确认你可以用 Element 登录。

**2. 获取凭证**

- 你需要：
  - `userId`（示例：`@nanobot:matrix.org`）
  - `password`

（注意：`accessToken` 和 `deviceId` 仍因遗留原因支持，但为了可靠的加密，推荐使用密码登录。如果提供了 `password`，`accessToken` 和 `deviceId` 会被忽略。）

**3. 配置**

```json
{
  "channels": {
    "matrix": {
      "enabled": true,
      "homeserver": "https://matrix.org",
      "userId": "@nanobot:matrix.org",
      "password": "mypasswordhere",
      "e2eeEnabled": true,
      "allowFrom": ["@your_user:matrix.org"],
      "groupPolicy": "open",
      "groupAllowFrom": [],
      "allowRoomMentions": false,
      "maxMediaBytes": 20971520
    }
  }
}
```

> 保持持久的 `matrix-store` — 如果这些在重启间变更，加密会话状态会丢失。

| 选项 | 描述 |
|--------|-------------|
| `allowFrom` | 允许交互的用户 ID。空则拒绝所有；使用 `["*"]` 允许所有人。 |
| `groupPolicy` | `open`（默认）、`mention` 或 `allowlist`。 |
| `groupAllowFrom` | 房间白名单（当策略为 `allowlist` 时使用）。 |
| `allowRoomMentions` | 在 mention 模式下接受 `@room` 提及。 |
| `e2eeEnabled` | E2EE 支持（默认 `true`）。设为 `false` 仅使用明文。 |
| `maxMediaBytes` | 最大附件大小（默认 `20MB`）。设为 `0` 阻止所有媒体。 |




**4. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>WhatsApp</b></summary>

需要 **Node.js ≥18**。

**1. 链接设备**

```bash
nanobot channels login whatsapp
# 用 WhatsApp → 设置 → 已链接设备 扫描 QR
```

**2. 配置**

```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1234567890"]
    }
  }
}
```

**3. 运行**（两个终端）

```bash
# 终端 1
nanobot channels login whatsapp

# 终端 2
nanobot gateway
```

> WhatsApp 桥接更新不会自动应用到现有安装。
> 升级 nanobot 后，重建本地桥接：
> `rm -rf ~/.nanobot/bridge && nanobot channels login whatsapp`

</details>

<details>
<summary><b>飞书</b></summary>

使用 **WebSocket** 长连接 — 无需公网 IP。

**1. 创建飞书 bot**
- 访问[飞书开放平台](https://open.feishu.cn/app)
- 创建新应用 → 启用 **机器人** 能力
- **权限**：
  - `im:message`（发送消息）和 `im:message.p2p_msg:readonly`（接收消息）
  - **流式回复**（nanobot 默认）：添加 **`cardkit:card:write`**（在飞书开发者控制台常标注为"创建和更新卡片"。CardKit 实体和流式助手文本必需。旧应用可能尚未拥有 — 打开"权限管理"，启用该 scope，如果控制台要求则**发布**新版应用）。
  - 如果**无法**添加 `cardkit:card:write`，在 `channels.feishu` 下设置 `"streaming": false`（见下文）。Bot 仍可工作；回复使用普通交互卡片而非逐 token 流式。
- **事件**：添加 `im.message.receive_v1`（接收消息）
  - 选择 **长连接** 模式（需要先运行 nanobot 以建立连接）
- 从"凭证与基础信息"获取 **App ID** 和 **App Secret**
- 发布应用

**2. 配置**

```json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "appId": "cli_xxx",
      "appSecret": "xxx",
      "encryptKey": "",
      "verificationToken": "",
      "allowFrom": ["ou_YOUR_OPEN_ID"],
      "groupPolicy": "mention",
      "streaming": true
    }
  }
}
```

> `streaming` 默认为 `true`。如果你的应用没有 **`cardkit:card:write`**（见上文权限），使用 `false`。
> `encryptKey` 和 `verificationToken` 在长连接模式下可选。
> `allowFrom`：添加你的 open_id（在给 bot 发消息时可在 nanobot 日志中找到）。使用 `["*"]` 允许所有用户。
> `groupPolicy`：`"mention"`（默认 — 仅在被 @时响应）、`"open"`（响应所有群消息）。私聊始终响应。

**3. 运行**

```bash
nanobot gateway
```

> [!TIP]
> 飞书使用 WebSocket 接收消息 — 无需 webhook 或公网 IP！

</details>

<details>
<summary><b>QQ（QQ单聊）</b></summary>

使用 **botpy SDK** 和 WebSocket — 无需公网 IP。当前仅支持**私聊消息**。

**1. 注册并创建 bot**
- 访问 [QQ 开放平台](https://q.qq.com) → 注册开发者（个人或企业）
- 创建新 bot 应用
- 进入 **开发设置** → 复制 **AppID** 和 **AppSecret**

**2. 设置沙箱用于测试**
- 在 bot 管理控制台，找到 **沙箱配置**
- 在 **在消息列表配置** 下，点击 **添加成员** 并添加你的 QQ 号
- 添加后，用手机 QQ 扫描 bot 的 QR 码 → 打开 bot 资料 → 点击"发消息"开始聊天

**3. 配置**

> - `allowFrom`：添加你的 openid（在给 bot 发消息时可在 nanobot 日志中找到）。使用 `["*"]` 公开访问。
> - `msgFormat`：可选。使用 `"plain"`（默认，与旧版 QQ 客户端最大兼容）或 `"markdown"`（新版客户端更丰富的格式）。
> - 生产环境：在 bot 控制台提交审核并发布。完整发布流程参见 [QQ Bot 文档](https://bot.q.qq.com/wiki/)。

```json
{
  "channels": {
    "qq": {
      "enabled": true,
      "appId": "YOUR_APP_ID",
      "secret": "YOUR_APP_SECRET",
      "allowFrom": ["YOUR_OPENID"],
      "msgFormat": "plain"
    }
  }
}
```

**4. 运行**

```bash
nanobot gateway
```

从 QQ 发消息给 bot — 它应该会响应！

</details>

<details>
<summary><b>钉钉</b></summary>

使用 **Stream Mode** — 无需公网 IP。

**1. 创建钉钉 bot**
- 访问[钉钉开放平台](https://open-dev.dingtalk.com/)
- 创建新应用 → 添加 **机器人** 能力
- **配置**：
  - 开启 **Stream Mode**
- **权限**：添加发送消息所需权限
- 从"凭证"获取 **AppKey** (Client ID) 和 **AppSecret** (Client Secret)
- 发布应用

**2. 配置**

```json
{
  "channels": {
    "dingtalk": {
      "enabled": true,
      "clientId": "YOUR_APP_KEY",
      "clientSecret": "YOUR_APP_SECRET",
      "allowFrom": ["YOUR_STAFF_ID"]
    }
  }
}
```

> `allowFrom`：添加你的员工 ID。使用 `["*"]` 允许所有用户。

**3. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>Slack</b></summary>

使用 **Socket Mode** — 无需公网 URL。

**1. 创建 Slack app**
- 访问 [Slack API](https://api.slack.com/apps) → **Create New App** → "From scratch"
- 选择名称和工作区

**2. 配置 app**
- **Socket Mode**：开启 → 生成带 `connections:write` scope 的 **App-Level Token** → 复制（`xapp-...`）
- **OAuth & Permissions**：添加 bot scopes：`chat:write`、`reactions:write`、`app_mentions:read`
- **Event Subscriptions**：开启 → 订阅 bot 事件：`message.im`、`message.channels`、`app_mention` → Save Changes
- **App Home**：滚动到 **Show Tabs** → 启用 **Messages Tab** → 检查 **"Allow users to send Slash commands and messages from the messages tab"**
- **Install App**：点击 **Install to Workspace** → 授权 → 复制 **Bot Token**（`xoxb-...`）

**3. 配置 nanobot**

```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "botToken": "xoxb-...",
      "appToken": "xapp-...",
      "allowFrom": ["YOUR_SLACK_USER_ID"],
      "groupPolicy": "mention"
    }
  }
}
```

**4. 运行**

```bash
nanobot gateway
```

直接 DM bot 或在渠道中 @mention 它 — 它应该会响应！

> [!TIP]
> - `groupPolicy`：`"mention"`（默认 — 仅在被 @mention 时响应）、`"open"`（响应所有渠道消息）或 `"allowlist"`（限制到特定渠道）。
> - DM 策略默认开放。设置 `"dm": {"enabled": false}` 禁用 DM。

</details>

<details>
<summary><b>Email</b></summary>

为 nanobot 提供独立邮箱账户。它通过 **IMAP** 轮询接收邮件并通过 **SMTP** 回复 — 就像个人邮件助手。

**1. 获取凭证（Gmail 示例）**
- 为你的 bot 创建专用 Gmail 账户（如 `my-nanobot@gmail.com`)
- 启用 2-Step Verification → 创建 [App Password](https://myaccount.google.com/apppasswords)
- 此 app password 用于 IMAP 和 SMTP

**2. 配置**

> - `consentGranted` 必须为 `true` 才允许邮箱访问。这是安全门 — 设为 `false` 完全禁用。
> - `allowFrom`：添加你的邮箱地址。使用 `["*"]` 接收任何人邮件。
> - `smtpUseTls` 和 `smtpUseSsl` 默认为 `true` / `false`，适用于 Gmail（端口 587 + STARTTLS）。无需显式设置。
> - 如果只想读取/分析邮件而不自动回复，设置 `"autoReplyEnabled": false`。
> - `allowedAttachmentTypes`：保存匹配这些 MIME 类型的入站附件 — `["*"]` 全部，例如 `["application/pdf", "image/*"]`（默认 `[]` = 禁用）。
> - `maxAttachmentSize`：每个附件最大字节数（默认 `2000000` / 2MB）。
> - `maxAttachmentsPerEmail`：每邮件最大保存附件数（默认 `5`）。

```json
{
  "channels": {
    "email": {
      "enabled": true,
      "consentGranted": true,
      "imapHost": "imap.gmail.com",
      "imapPort": 993,
      "imapUsername": "my-nanobot@gmail.com",
      "imapPassword": "your-app-password",
      "smtpHost": "smtp.gmail.com",
      "smtpPort": 587,
      "smtpUsername": "my-nanobot@gmail.com",
      "smtpPassword": "your-app-password",
      "fromAddress": "my-nanobot@gmail.com",
      "allowFrom": ["your-real-email@gmail.com"],
      "allowedAttachmentTypes": ["application/pdf", "image/*"]
    }
  }
}
```


**3. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>微信 (Weixin)</b></summary>

通过 ilinkai 个人微信 API 使用 **HTTP 长轮询** 和 QR 码登录。无需本地微信桌面客户端。

**1. 安装微信支持**

```bash
pip install "nanobot-ai[weixin]"
```

**2. 配置**

```json
{
  "channels": {
    "weixin": {
      "enabled": true,
      "allowFrom": ["YOUR_WECHAT_USER_ID"]
    }
  }
}
```

> - `allowFrom`：添加你在 nanobot 日志中看到的微信账户 sender ID。使用 `["*"]` 允许所有用户。
> - `token`：可选。如省略，交互式登录后 nanobot 会为你保存 token。
> - `routeTag`：可选。当上游微信部署需要请求路由时，nanobot 会将其作为 `SKRouteTag` 请求头发送。
> - `stateDir`：可选。默认为 nanobot 的微信状态运行时目录。
> - `pollTimeout`：可选的长轮询超时秒数。

**3. 登录**

```bash
nanobot channels login weixin
```

使用 `--force` 重新认证并忽略已保存 token：

```bash
nanobot channels login weixin --force
```

**4. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>企业微信</b></summary>

> 这里使用 [wecom-aibot-sdk-python](https://github.com/chengyongru/wecom_aibot_sdk)（官方 [@wecom/aibot-node-sdk](https://www.npmjs.com/package/@wecom/aibot-node-sdk) 的社区 Python 版本）。
>
> 使用 **WebSocket** 长连接 — 无需公网 IP。

**1. 安装可选依赖**

```bash
pip install nanobot-ai[wecom]
```

**2. 创建企业微信 AI Bot**

进入企业微信管理控制台 → 智能机器人 → 创建机器人 → 选择带 **长连接** 的 **API 模式**。复制 Bot ID 和 Secret。

**3. 配置**

```json
{
  "channels": {
    "wecom": {
      "enabled": true,
      "botId": "your_bot_id",
      "secret": "your_bot_secret",
      "allowFrom": ["your_id"]
    }
  }
}
```

**4. 运行**

```bash
nanobot gateway
```

</details>