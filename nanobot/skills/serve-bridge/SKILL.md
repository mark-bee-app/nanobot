---
name: serve-bridge
description: >
  当用户要求向远程 nanobot、远端 agent、远程 serve 实例发送消息、查询或任务时，使用该 skill。
  适用于 gateway 模式部署的 nanobot 需要主动调用另一台机器上 serve 模式部署的 nanobot 的场景。
  通过 exec 工具运行预置脚本 `call-remote.py`，向远程 serve 的 /v1/chat/completions 端点发送 POST 请求。
  触发关键词：远程 agent、remote nanobot、serve 实例、转发给、问问远程、调用远程。
metadata:
  nanobot:
    emoji: "🌉"
---

# Serve Bridge — 远程 Nanobot 调用指南

## 概述

本 skill 用于 gateway 部署的 nanobot **主动**向另一台机器上 serve 模式部署的 nanobot 发送请求，实现单向通信（gateway → serve）。

## 获取远程 Serve 地址

在发起调用前，先确认远程 serve 的地址。按以下优先级：

1. **环境变量**：通过 `exec` 工具执行 `echo $NANOBOT_SERVE_URL`，如果输出非空则使用该地址。
2. **用户指定**：如果用户对话中明确提到了地址（如 `http://192.168.1.100:8000`），直接使用。
3. **默认地址**：如果以上都未获取到，使用 `http://localhost:8000`，但应告知用户正在使用默认地址。

## 调用方式

使用 `exec` 工具运行预置脚本 `nanobot/skills/serve-bridge/scripts/call-remote.py`。

如果脚本不存在，再回退到 curl 命令。

### 脚本调用（推荐）

```bash
python nanobot/skills/serve-bridge/scripts/call-remote.py \
  --url <REMOTE_URL> \
  --message "<要发送的消息>" \
  --session-id "<可选会话ID>"
```

参数说明：

| 参数 | 说明 |
|------|------|
| `--url` | 远程 serve 地址，不传则读取环境变量 `NANOBOT_SERVE_URL`，否则默认 `localhost:8000` |
| `--message` / `-m` | **必需**。要发送给远程 agent 的消息内容 |
| `--session-id` / `-s` | 可选。如需维持多轮对话上下文，使用固定的 session_id |

脚本会自动解析响应，只返回远程 agent 的回复内容（纯文本），无需额外处理 JSON。

### 完整示例

发送消息"总结一下今天的天气"到远程 serve：

```bash
python nanobot/skills/serve-bridge/scripts/call-remote.py \
  --url http://192.168.1.50:8000 \
  --message "总结一下今天的天气"
```

### 回退方案：curl 命令

如果预置脚本不可用，使用 curl 直接调用：

```bash
curl -s -X POST "http://<REMOTE_HOST>:<PORT>/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nanobot",
    "messages": [{"role": "user", "content": "<消息>"}],
    "session_id": "<可选>"
  }'
```

响应为 OpenAI-compatible JSON，需提取 `choices[0].message.content`。

## 多轮对话

如需与远程 agent 维持多轮对话上下文：

1. 在首次调用时指定 `--session-id`（如 `"bridge-session-001"`）
2. 后续调用使用相同的 `session_id`
3. 远程 serve 会为该 session_id 维护独立的对话历史

## 错误处理

| 情况 | 处理方式 |
|------|---------|
| HTTP 非 200 | 检查远程 serve 是否正常运行，地址和端口是否正确 |
| 脚本返回空 | 检查 `--message` 是否正确传入 |
| 连接失败 | 检查网络连通性，防火墙是否放行对应端口 |
| 超时 | 远程 serve 的默认超时为 120 秒，如任务复杂可能超时 |

## 健康检查

如需确认远程 serve 是否可用：

```bash
curl -s http://<REMOTE_HOST>:<PORT>/health
```

正常应返回 `{"status": "ok"}`。
