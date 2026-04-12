## 🔌 OpenAI 兼容 API

nanobot 可为本地集成提供最小化的 OpenAI 兼容端点：

```bash
pip install "nanobot-ai[api]"
nanobot serve
```

默认情况下，API 绑定到 `127.0.0.1:8900`。可在 `config.json` 中修改。

### 行为

- 会话隔离：在请求体中传递 `"session_id"` 以隔离对话；省略则使用共享默认会话（`api:default`）
- 单消息输入：每个请求必须包含恰好一条 `user` 消息
- 固定模型：省略 `model`，或传递 `/v1/models` 显示的相同模型
- 不支持流式：`stream=true` 不支持

### 端点

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

### curl

```bash
curl http://127.0.0.1:8900/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "hi"}],
    "session_id": "my-session"
  }'
```

### Python (`requests`)

```python
import requests

resp = requests.post(
    "http://127.0.0.1:8900/v1/chat/completions",
    json={
        "messages": [{"role": "user", "content": "hi"}],
        "session_id": "my-session",  # 可选：隔离对话
    },
    timeout=120,
)
resp.raise_for_status()
print(resp.json()["choices"][0]["message"]["content"])
```

### Python (`openai`)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8900/v1",
    api_key="dummy",
)

resp = client.chat.completions.create(
    model="MiniMax-M2.7",
    messages=[{"role": "user", "content": "hi"}],
    extra_body={"session_id": "my-session"},  # 可选：隔离对话
)
print(resp.choices[0].message.content)
```