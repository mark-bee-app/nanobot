## 💻 CLI 命令参考

| 命令 | 描述 |
|---------|-------------|
| `nanobot onboard` | 在 `~/.nanobot/` 初始化配置和工作区 |
| `nanobot onboard --wizard` | 启动交互式初始化向导 |
| `nanobot onboard -c <config> -w <workspace>` | 初始化或刷新特定实例的配置和工作区 |
| `nanobot agent -m "..."` | 与代理聊天 |
| `nanobot agent -w <workspace>` | 针对特定工作区聊天 |
| `nanobot agent -w <workspace> -c <config>` | 针对特定工作区/配置聊天 |
| `nanobot agent` | 交互式聊天模式 |
| `nanobot agent --no-markdown` | 显示纯文本回复 |
| `nanobot agent --logs` | 聊天时显示运行日志 |
| `nanobot serve` | 启动 OpenAI 兼容 API |
| `nanobot gateway` | 启动网关 |
| `nanobot status` | 显示状态 |
| `nanobot provider login openai-codex` | 提供器 OAuth 登录 |
| `nanobot channels login <channel>` | 交互式渠道认证 |
| `nanobot channels status` | 显示渠道状态 |

交互模式退出方式：`exit`、`quit`、`/exit`、`/quit`、`:q` 或 `Ctrl+D`。

## 💬 聊天内命令

这些命令在聊天渠道和交互式代理会话中有效：

| 命令 | 描述 |
|---------|-------------|
| `/new` | 开始新对话 |
| `/stop` | 停止当前任务 |
| `/restart` | 重启 bot |
| `/status` | 显示 bot 状态 |
| `/dream` | 立即运行 Dream 内存整合 |
| `/dream-log` | 显示最新的 Dream 内存变更 |
| `/dream-log <sha>` | 显示特定 Dream 内存变更 |
| `/dream-restore` | 列出最近的 Dream 内存版本 |
| `/dream-restore <sha>` | 将内存恢复到特定变更前的状态 |
| `/help` | 显示可用的聊天内命令 |

<details>
<summary><b>心跳（定时任务）</b></summary>

网关每 30 分钟唤醒一次，检查工作区中的 `HEARTBEAT.md`（`~/.nanobot/workspace/HEARTBEAT.md`）。如果文件包含任务，代理会执行并将结果发送到你最近活跃的聊天渠道。

**设置：**编辑 `~/.nanobot/workspace/HEARTBEAT.md`（由 `nanobot onboard` 自动创建）：

```markdown
## 定时任务

- [ ] 查看天气预报并发送摘要
- [ ] 扫描邮箱中的紧急邮件
```

代理也可以自行管理此文件 — 让它"添加一个定时任务"，它会为你更新 `HEARTBEAT.md`。

> **注意：**网关必须运行（`nanobot gateway`），且你必须至少与 bot 聊过一次，这样它才知道发送到哪个渠道。

</details>