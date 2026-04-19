# Nanobot Serve 部署与使用指南

> 基于对话整理，日期：2026/04/19

---

## 一、Serve 与 Gateway 的关系

**不冲突，可以一起使用，但不建议。**

| 命令 | 作用 | 端口配置 |
|------|------|----------|
| `serve` | 启动 OpenAI-compatible HTTP API (`/v1/chat/completions`) | `api.port` (默认 8900) |
| `gateway` | 启动后台消息网关（含 AgentLoop、Cron、Heartbeat、渠道） | `gateway.port` (默认 18790) |

**注意**：两个命令各创建一套 `AgentLoop`、`MessageBus`、`SessionManager`。若指向**同一个 workspace**，会同时读写 `history.jsonl`、`SOUL.md` 等文件，导致数据竞争。建议为不同模式使用独立 workspace，或只运行其中一个。

---

## 二、Linux 部署 Serve

### 1. 安装

```bash
# 基础安装 + API 依赖 (aiohttp)
pip install "nanobot-ai[api]"

# 或从源码
pip install -e ".[dev,api]"
```

### 2. 配置 `~/.nanobot/config.json`

```json
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6",
      "workspace": "~/.nanobot/workspace"
    }
  },
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    }
  },
  "api": {
    "host": "0.0.0.0",
    "port": 8900,
    "timeout": 120
  }
}
```

- `api.host`：默认 `127.0.0.1`（仅本地），服务器部署需改为 `0.0.0.0`
- `api.port`：默认 `8900`
- `api.timeout`：单次请求超时秒数

### 3. 直接启动

```bash
nanobot serve
# 或覆盖参数
nanobot serve --host 0.0.0.0 --port 8900 --timeout 120
```

启动日志示例：

```
Starting OpenAI-compatible API server
  Endpoint : http://0.0.0.0:8900/v1/chat/completions
  Model    : anthropic/claude-sonnet-4-6
  Session  : api:default
  Timeout  : 120s
```

### 4. 生产部署：systemd 服务

创建 `/etc/systemd/system/nanobot-serve.service`：

```ini
[Unit]
Description=Nanobot OpenAI-Compatible API Server
After=network.target

[Service]
Type=simple
User=nanobot
Group=nanobot
WorkingDirectory=/home/nanobot
Environment="HOME=/home/nanobot"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/nanobot/.local/bin/nanobot serve --config /home/nanobot/.nanobot/config.json
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nanobot-serve
sudo systemctl status nanobot-serve
```

### 5. 可选：Nginx 反向代理

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8900;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 130s;  # > serve timeout
    }
}
```

---

## 三、API 测试

```bash
# 聊天补全
curl http://localhost:8900/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nanobot",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 健康检查
curl http://localhost:8900/health

# 查看可用模型
curl http://localhost:8900/v1/models
```

---

## 四、注意事项

1. **不支持流式输出**：`stream=true` 会返回 400 错误
2. **单条消息限制**：`messages` 数组目前只支持一个 `user` 消息
3. **会话隔离**：可通过请求体传 `session_id` 隔离不同用户上下文，不传则共用 `api:default`
4. **Workspace 竞争**：不要与 `gateway` 共用同一个 workspace，建议 `--workspace` 分开
5. **超时配置**：Nginx 的 `proxy_read_timeout` 需大于 `serve` 的 `timeout`