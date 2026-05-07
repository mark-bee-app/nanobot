# Nanobot 心跳机制业务执行流程

Nanobot 的心跳机制（Heartbeat）主要用于让 Agent 能够在后台定期“苏醒”，检查是否有计划任务或需要主动触发的操作，并在必要时执行并通知用户。

整体的业务执行流程分为四个主要阶段：

## 1. 初始化与调度启动

在系统启动时（主要是 Gateway 模式），会读取配置文件并创建 `HeartbeatService` 实例，启动后台轮询协程。

* **主要文件**：`nanobot/cli/commands.py`
* **核心逻辑**：
  * `gateway` 命令入口处实例化了 `HeartbeatService`。
  * `on_heartbeat_execute` 和 `on_heartbeat_notify` 两个回调函数被传入 Service 中，用于打通后台服务与 Agent 主引擎、消息总线（Bus）的连接。

## 2. Phase 1：决策阶段（检查是否有任务）

心跳定时触发（默认为 `_tick()` 方法）。它不会直接无脑唤醒 Agent，而是通过一次轻量级的 LLM 调用判断是否真的有事做。

* **主要文件**：`nanobot/heartbeat/service.py`
* **核心逻辑**：
  * `_run_loop` 与 `_tick` 方法：控制唤醒频率。
  * `_read_heartbeat_file`：读取工作目录下的 `HEARTBEAT.md` 文件（Agent 会把需要定期跟进的任务写在这个文件里）。
  * `_decide` 方法：将时间信息和 `HEARTBEAT.md` 内容发给 LLM，强制要求 LLM 调用虚拟工具 `heartbeat`。LLM 必须输出 `action`（`skip` 或 `run`）以及 `tasks`（如果有任务的话，用自然语言概括需要做什么）。

## 3. Phase 2：执行阶段（运行主 Agent 流程）

如果决策阶段判定 `action == "run"`，就会进入真实的任务执行阶段。

* **主要文件**：`nanobot/cli/commands.py` (回调) 和 `nanobot/heartbeat/service.py`
* **核心逻辑**：
  * `HeartbeatService._tick` 中会调用 `self.on_execute(tasks)`。
  * 对应到 `cli/commands.py` 里的 `on_heartbeat_execute` 回调：它会调用 `agent.process_direct(tasks, session_key="heartbeat", ...)`，将刚刚 LLM 总结的 `tasks` 当作一条来自用户的指令，送进主 Agent 的思考与工具调用循环中执行。

## 4. Phase 3 & 4：后置评估与通知（防打扰判断与消息投递）

Agent 执行完任务后会产生回复（Response）。为了避免闲聊或无意义的打扰（比如回复了“检查完毕，无新动态”），系统会做一个智能拦截。

* **主要文件**：`nanobot/utils/evaluator.py` 和 `nanobot/cli/commands.py` (回调)
* **核心逻辑**：
  * `utils/evaluator.py` 中的 `evaluate_response` 函数：使用 LLM（调用 `evaluate_notification` 虚拟工具），传入任务上下文和 Agent 刚生成的回复，让 LLM 决策是否需要真的通知用户（返回布尔值 `should_notify`）。
  * 如果 `should_notify` 为 True，`HeartbeatService` 将触发 `self.on_notify(response)`。
  * `cli/commands.py` 中的 `on_heartbeat_notify` 回调：通过 `_pick_heartbeat_target` 找出用户活跃的 IM 渠道（如微信/企微等），并把消息打包成 `OutboundMessage` 发送到消息总线（`bus.publish_outbound`），最终推给用户。

---

**源码阅读建议顺序：**
1. `nanobot/heartbeat/service.py`：了解核心机制和两阶段设计的本体。
2. `nanobot/cli/commands.py`：搜索 `HeartbeatService`，看如何串联 Agent 和消息发布。
3. `nanobot/utils/evaluator.py`：看如何做防打扰拦截判断。