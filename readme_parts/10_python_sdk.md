## 🐍 Python SDK

将 nanobot 作为库使用 — 无 CLI、无网关，仅需 Python：

```python
from nanobot import Nanobot

bot = Nanobot.from_config()
result = await bot.run("总结 README")
print(result.content)
```

每次调用携带 `session_key` 用于会话隔离 — 不同密钥拥有独立历史：

```python
await bot.run("hi", session_key="user-alice")
await bot.run("hi", session_key="task-42")
```

添加生命周期钩子以观察或自定义代理：

```python
from nanobot.agent import AgentHook, AgentHookContext

class AuditHook(AgentHook):
    async def before_execute_tools(self, ctx: AgentHookContext) -> None:
        for tc in ctx.tool_calls:
            print(f"[工具] {tc.name}")

result = await bot.run("Hello", hooks=[AuditHook()])
```

完整 SDK 参考[docs/PYTHON_SDK.md](docs/PYTHON_SDK.md)。