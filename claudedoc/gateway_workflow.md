# gateway 方法主要业务流程

`gateway` 方法是 `nanobot` 系统的核心后台进程，负责协调和管理所有的后台任务和通道通信。以下是它的主要业务流程梳理：

## 1. 配置与环境初始化
*   **加载配置**: 通过 `_load_runtime_config` 加载运行时的配置，包括端口、工作区路径等参数。
*   **环境准备**: 调用 `sync_workspace_templates` 确保工作区环境（如模板文件等）已经同步并准备就绪。
*   **实例化基础组件**:
    *   实例化消息总线（`MessageBus`），作为模块间异步通信的核心。
    *   初始化 LLM 提供者（`provider`）和会话管理器（`SessionManager`）。

## 2. 定时任务（Cron）服务配置
*   **迁移旧数据**: 检查并调用 `_migrate_cron_store` 迁移旧版本的全局定时任务存储。
*   **初始化 Cron 服务**: 为工作区设置独立的定时任务存储路径（`jobs.json`），并初始化 `CronService`，将其与 `AgentLoop` 绑定。

## 3. 代理循环（AgentLoop）初始化
*   **创建 AgentLoop 实例**: 负责处理 LLM 交互和工具调用。
*   **加载各项配置**: 代理循环结合了模型设置、上下文窗口、重试策略、工具配置（如 web、exec、MCP）等各项系统配置。

## 4. Cron 任务的回调处理（`on_cron_job`）
*   **系统任务拦截**: 拦截名为 "dream" 的内部系统任务，并直接执行 `agent.dream.run()`。
*   **用户定义任务处理**: 对于用户定义的 cron 任务，构造系统提示（`reminder_note`），通过代理处理（`agent.process_direct`）。
*   **结果下发评估**: 利用 `evaluate_response` 评估响应结果是否需要下发。如果需要，则通过 `MessageBus` 发布出站消息。

## 5. 渠道管理器（ChannelManager）初始化
*   **实例化 ChannelManager**: 用于管理和启动所有已启用的消息渠道（如 CLI、Telegram、Discord、飞书等）。

## 6. 心跳（Heartbeat）服务配置
*   心跳服务用于定期激活代理，以保持其活跃或执行后台监控任务。
*   **`on_heartbeat_execute`**: 选择一个合适的目标渠道/会话，通过代理循环执行心跳任务，并保留有限的对话历史。
*   **`on_heartbeat_notify`**: 将心跳执行的输出结果发布到对应的消息渠道。
*   **启动 HeartbeatService**。

## 7. 内部系统任务注册
*   读取配置，将 "dream" 模块作为常驻的系统级 cron 任务注册到 `CronService` 中，以确保后台知识整合和长期记忆功能的定期运行。

## 8. 异步并发启动
*   **启动核心服务**: 使用 `asyncio.gather` 并发启动核心服务：Cron、Heartbeat、AgentLoop 和所有渠道（ChannelManager）。
*   **优雅停机处理**: 捕获 `KeyboardInterrupt` 或异常时，依次安全地关闭 MCP、Heartbeat、Cron、AgentLoop 和各类渠道。