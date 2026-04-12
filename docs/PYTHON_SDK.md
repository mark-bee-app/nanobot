# Python SDK

> **注意：** 此接口目前是最新源代码版本中的实验性功能，计划在 `v0.1.5` 正式发布。

以编程方式使用 nanobot — 加载配置、运行代理、获取结果。

## 快速开始

```python
import asyncio
from nanobot import Nanobot

async def main():
    bot = Nanobot.from_config()
    result = await bot.run("东京现在几点？")
    print(result.content)

asyncio.run(main())
```

## API

### `Nanobot.from_config(config_path?, *, workspace?)`

从配置文件创建 `Nanobot` 实例。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `config_path` | `str \| Path \| None` | `None` | `config.json` 的路径。默认为 `~/.nanobot/config.json`。 |
| `workspace` | `str \| Path \| None` | `None` | 覆盖配置中的工作目录。 |

如果指定的路径不存在，会抛出 `FileNotFoundError`。

### `await bot.run(message, *, session_key?, hooks?)`

运行一次代理。返回 `RunResult`。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `message` | `str` | *(必填)* | 要处理的用户消息。 |
| `session_key` | `str` | `"sdk:default"` | 会话标识符，用于会话隔离。不同的键拥有独立的对话历史。 |
| `hooks` | `list[AgentHook] \| None` | `None` | 仅本次运行使用的生命周期钩子。 |

```python
# 隔离会话 — 每个用户拥有独立的对话历史
await bot.run("你好", session_key="user-alice")
await bot.run("你好", session_key="user-bob")
```

### `RunResult`

| 字段 | 类型 | 描述 |
|------|------|------|
| `content` | `str` | 代理的最终文本回复。 |
| `tools_used` | `list[str]` | 本次运行中调用的工具名称列表。 |
| `messages` | `list[dict]` | 原始消息历史（用于调试）。 |

## 钩子

钩子让你可以在不修改内部代码的情况下观察或修改代理循环。

继承 `AgentHook` 类并重写任意方法：

| 方法 | 触发时机 |
|------|----------|
| `before_iteration(ctx)` | 每次 LLM 调用之前 |
| `on_stream(ctx, delta)` | 每个流式 token |
| `on_stream_end(ctx)` | 流式输出结束时 |
| `before_execute_tools(ctx)` | 工具执行之前（可检查 `ctx.tool_calls`） |
| `after_iteration(ctx, response)` | 每次 LLM 响应之后 |
| `finalize_content(ctx, content)` | 转换最终输出文本 |

### 示例：审计钩子

```python
from nanobot.agent import AgentHook, AgentHookContext

class AuditHook(AgentHook):
    def __init__(self):
        self.calls = []

    async def before_execute_tools(self, ctx: AgentHookContext) -> None:
        for tc in ctx.tool_calls:
            self.calls.append(tc.name)
            print(f"[audit] {tc.name}({tc.arguments})")

hook = AuditHook()
result = await bot.run("列出 /tmp 目录下的文件", hooks=[hook])
print(f"使用的工具: {hook.calls}")
```

### 组合钩子

传入多个钩子 — 它们按顺序执行，其中一个的错误不会阻塞其他钩子：

```python
result = await bot.run("你好", hooks=[AuditHook(), MetricsHook()])
```

底层使用 `CompositeHook` 实现带错误隔离的扇出。

### `finalize_content` 管道

与异步方法（扇出）不同，`finalize_content` 是一个管道 — 每个钩子的输出作为下一个钩子的输入：

```python
class Censor(AgentHook):
    def finalize_content(self, ctx, content):
        return content.replace("secret", "***") if content else content
```

## 完整示例

```python
import asyncio
from nanobot import Nanobot
from nanobot.agent import AgentHook, AgentHookContext

class TimingHook(AgentHook):
    async def before_iteration(self, ctx: AgentHookContext) -> None:
        import time
        ctx.metadata["_t0"] = time.time()

    async def after_iteration(self, ctx, response) -> None:
        import time
        elapsed = time.time() - ctx.metadata.get("_t0", 0)
        print(f"[timing] 迭代耗时 {elapsed:.2f}s")

async def main():
    bot = Nanobot.from_config(workspace="/my/project")
    result = await bot.run(
        "解释主函数的功能",
        hooks=[TimingHook()],
    )
    print(result.content)

asyncio.run(main())
```