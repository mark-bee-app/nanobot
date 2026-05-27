"""智能体循环：核心处理引擎。

负责消息接收、上下文构建、LLM 调用、工具执行、结果回发等全流程。
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import time
from contextlib import AsyncExitStack, nullcontext, suppress
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from loguru import logger

from nanobot.agent import model_presets as preset_helpers
from nanobot.agent.autocompact import AutoCompact
from nanobot.agent.context import ContextBuilder
from nanobot.agent.hook import AgentHook, CompositeHook
from nanobot.agent.memory import Consolidator, Dream
from nanobot.agent.progress_hook import AgentProgressHook
from nanobot.agent.runner import _MAX_INJECTIONS_PER_TURN, AgentRunner, AgentRunSpec
from nanobot.agent.subagent import SubagentManager
from nanobot.agent.tools.file_state import FileStateStore, bind_file_states, reset_file_states
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.self import MyTool
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.command import CommandContext, CommandRouter, register_builtin_commands
from nanobot.config.schema import AgentDefaults, ModelPresetConfig
from nanobot.providers.base import LLMProvider
from nanobot.providers.factory import ProviderSnapshot
from nanobot.session.goal_state import (
    goal_state_ws_blob,
    runner_wall_llm_timeout_s,
)
from nanobot.session.manager import Session, SessionManager
from nanobot.utils.artifacts import generated_image_paths_from_messages
from nanobot.utils.document import extract_documents
from nanobot.utils.helpers import image_placeholder_text
from nanobot.utils.helpers import truncate_text as truncate_text_fn
from nanobot.utils.image_generation_intent import image_generation_prompt
from nanobot.utils.runtime import EMPTY_FINAL_RESPONSE_MESSAGE
from nanobot.utils.session_attachments import merge_turn_media_into_last_assistant
from nanobot.utils.webui_titles import mark_webui_session, maybe_generate_webui_title_after_turn
from nanobot.utils.webui_turn_helpers import publish_turn_run_status

if TYPE_CHECKING:
    from nanobot.config.schema import (
        ChannelsConfig,
        ProviderConfig,
        ToolsConfig,
    )
    from nanobot.cron.service import CronService


UNIFIED_SESSION_KEY = "unified:default"


class TurnState(Enum):
    """一次对话回合（turn）的各阶段状态机定义。"""
    RESTORE = auto()   # 恢复：从 checkpoint / pending 中恢复中断的会话
    COMPACT = auto()   # 压缩：自动压缩过长的会话历史
    COMMAND = auto()   # 命令：识别并执行用户输入的斜杠命令
    BUILD = auto()     # 构建：组装 prompt、工具定义、历史记录
    RUN = auto()       # 运行：调用 LLM，执行工具调用循环
    SAVE = auto()      # 保存：将本轮新生成的消息持久化到会话
    RESPOND = auto()   # 响应：组装并发送最终回复消息
    DONE = auto()      # 完成：回合结束


@dataclass
class StateTraceEntry:
    """用于追踪一次回合中各状态切换的时间与事件。"""
    state: TurnState       # 当前状态
    started_at: float      # 该状态开始时间（perf_counter）
    duration_ms: float     # 该状态持续时长（毫秒）
    event: str             # 状态处理完成后产生的事件名
    error: str | None = None  # 若发生异常，记录异常类型


@dataclass
class TurnContext:
    """单个回合在状态机中运行时的可变上下文。

    保存了本轮处理所需的所有中间状态、回调函数和最终产物。
    """
    msg: InboundMessage          # 触发本轮的用户/系统消息
    session_key: str             # 当前会话标识
    state: TurnState             # 当前所处状态
    turn_id: str                 # 唯一回合 ID（用于追踪日志）
    session: Session | None = None  # 当前会话对象（在 RESTORE 阶段填充）

    history: list[dict[str, Any]] = field(default_factory=list)          # 从会话中读出的历史消息
    initial_messages: list[dict[str, Any]] = field(default_factory=list)  # 组装后送给 LLM 的初始消息列表

    final_content: str | None = None          # LLM 最终返回的文本内容
    tools_used: list[str] = field(default_factory=list)            # 本轮使用过的工具名列表
    all_messages: list[dict[str, Any]] = field(default_factory=list)     # 本轮 LLM 对话产生的全部消息
    stop_reason: str = ""                     # 停止原因：max_iterations / error / tool_error / stop 等
    had_injections: bool = False              # 本轮是否插入了用户 follow-up 消息

    user_persisted_early: bool = False        # 是否在 BUILD 阶段就提前持久化了用户消息
    save_skip: int = 0                        # 保存时需要跳过的历史消息数（避免重复存旧消息）

    outbound: OutboundMessage | None = None   # 最终要发回给用户的消息
    generated_media: list[str] = field(default_factory=list)       # 本轮生成的图片等媒体文件路径

    on_progress: Callable[..., Awaitable[None]] | None = None      # 进度回调（工具提示、推理过程等）
    on_stream: Callable[[str], Awaitable[None]] | None = None      # 流式输出回调（收到文本增量时触发）
    on_stream_end: Callable[..., Awaitable[None]] | None = None    # 流式结束回调
    on_retry_wait: Callable[[str], Awaitable[None]] | None = None  # 等待重试时的回调

    pending_queue: asyncio.Queue | None = None  # 同一会话的后续消息注入队列（实现 mid-turn injection）
    pending_summary: str | None = None          # 自动压缩后产生的会话摘要

    turn_wall_started_at: float = field(default_factory=time.time)  # 回合开始时的墙上时间
    turn_latency_ms: int | None = None         # 本轮总耗时（毫秒）

    trace: list[StateTraceEntry] = field(default_factory=list)      # 状态机各阶段耗时追踪


class AgentLoop:
    """
    智能体循环（AgentLoop）是整个 nanobot 的核心处理引擎。

    主要职责：
    1. 从消息总线（MessageBus）接收外部消息
    2. 构建 LLM 上下文：历史记录、记忆、技能等
    3. 调用大语言模型（LLM）生成回复或工具调用
    4. 执行工具调用，收集结果，再送回 LLM
    5. 将最终响应通过消息总线发回对应渠道

    内部采用事件驱动的状态机（RESTORE → COMPACT → COMMAND → BUILD → RUN → SAVE → RESPOND → DONE）
    管理一次完整的对话回合（turn）。
    """

    @property
    def current_iteration(self) -> int:
        """当前 LLM 对话轮次（tool-call 迭代次数）。"""
        return self._current_iteration

    @property
    def tool_names(self) -> list[str]:
        """当前已注册的所有工具名称列表。"""
        return self.tools.tool_names

    _RUNTIME_CHECKPOINT_KEY = "runtime_checkpoint"
    _PENDING_USER_TURN_KEY = "pending_user_turn"

    # 事件驱动的状态转换表。
    # 每个状态处理器返回一个事件字符串，驱动器在此表中查找下一个状态。
    _TRANSITIONS: dict[tuple[TurnState, str], TurnState] = {
        (TurnState.RESTORE, "ok"): TurnState.COMPACT,
        (TurnState.COMPACT, "ok"): TurnState.COMMAND,
        (TurnState.COMMAND, "dispatch"): TurnState.BUILD,
        (TurnState.COMMAND, "shortcut"): TurnState.DONE,
        (TurnState.BUILD, "ok"): TurnState.RUN,
        (TurnState.RUN, "ok"): TurnState.SAVE,
        (TurnState.SAVE, "ok"): TurnState.RESPOND,
        (TurnState.RESPOND, "ok"): TurnState.DONE,
    }

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int | None = None,
        context_window_tokens: int | None = None,
        context_block_limit: int | None = None,
        max_tool_result_chars: int | None = None,
        provider_retry_mode: str = "standard",
        tool_hint_max_length: int | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
        channels_config: ChannelsConfig | None = None,
        timezone: str | None = None,
        session_ttl_minutes: int = 0,
        consolidation_ratio: float = 0.5,
        max_messages: int = 120,
        hooks: list[AgentHook] | None = None,
        unified_session: bool = False,
        disabled_skills: list[str] | None = None,
        tools_config: ToolsConfig | None = None,
        image_generation_provider_config: ProviderConfig | None = None,
        image_generation_provider_configs: dict[str, ProviderConfig] | None = None,
        provider_snapshot_loader: Callable[..., ProviderSnapshot] | None = None,
        provider_signature: tuple[object, ...] | None = None,
        model_presets: dict[str, ModelPresetConfig] | None = None,
        model_preset: str | None = None,
        preset_snapshot_loader: preset_helpers.PresetSnapshotLoader | None = None,
        runtime_model_publisher: Callable[[str, str | None], None] | None = None,
    ):
        from nanobot.config.schema import ToolsConfig

        _tc = tools_config or ToolsConfig()
        defaults = AgentDefaults()
        self.bus = bus
        self.channels_config = channels_config
        self.provider = provider
        self._provider_snapshot_loader = provider_snapshot_loader
        self._preset_snapshot_loader = preset_snapshot_loader
        self._runtime_model_publisher = runtime_model_publisher
        self._provider_signature = provider_signature
        self._default_selection_signature = preset_helpers.default_selection_signature(provider_signature)
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = (
            max_iterations if max_iterations is not None else defaults.max_tool_iterations
        )
        self.context_window_tokens = (
            context_window_tokens
            if context_window_tokens is not None
            else defaults.context_window_tokens
        )
        self.context_block_limit = context_block_limit
        self.max_tool_result_chars = (
            max_tool_result_chars
            if max_tool_result_chars is not None
            else defaults.max_tool_result_chars
        )
        self.provider_retry_mode = provider_retry_mode
        self.tool_hint_max_length = (
            tool_hint_max_length if tool_hint_max_length is not None
            else defaults.tool_hint_max_length
        )
        self.tools_config = _tc
        self.web_config = _tc.web
        self.exec_config = _tc.exec
        self._image_generation_provider_configs = dict(image_generation_provider_configs or {})
        if (
            image_generation_provider_config is not None
            and "openrouter" not in self._image_generation_provider_configs
        ):
            self._image_generation_provider_configs["openrouter"] = image_generation_provider_config
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        self._start_time = time.time()
        self._last_usage: dict[str, int] = {}
        self._pending_turn_latency_ms: dict[str, int] = {}
        self._extra_hooks: list[AgentHook] = hooks or []

        self.context = ContextBuilder(workspace, timezone=timezone, disabled_skills=disabled_skills)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        # 每个逻辑会话一个文件读/写追踪器。工具注册表被整个循环共享，
        # 因此工具通过 contextvars 解析当前激活的状态。
        self._file_state_store = FileStateStore()
        self.runner = AgentRunner(provider)
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            tools_config=_tc,
            max_tool_result_chars=self.max_tool_result_chars,
            restrict_to_workspace=restrict_to_workspace,
            disabled_skills=disabled_skills,
            max_iterations=self.max_iterations,
            llm_wall_timeout_for_session=lambda sk: runner_wall_llm_timeout_s(self.sessions, sk),
        )
        self._unified_session = unified_session
        self._max_messages = max_messages if max_messages > 0 else 120
        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stacks: dict[str, AsyncExitStack] = {}
        self._mcp_connected = False
        self._mcp_connecting = False
        self._active_tasks: dict[str, list[asyncio.Task]] = {}  # session_key -> tasks
        self._background_tasks: list[asyncio.Task] = []
        self._session_locks: dict[str, asyncio.Lock] = {}
        # 每个会话的待处理队列，用于 mid-turn 消息注入。
        # 当某个会话已有活跃任务时，该会话的新消息会被路由到这里，
        # 而不是创建一个新任务（保证单会话串行处理）。
        self._pending_queues: dict[str, asyncio.Queue] = {}
        # 追踪被路由到待处理队列的 follow-up 消息的 message_id，
        # 以便在流结束时清理对应渠道的反应（例如飞书的点赞）。
        # 以 session_key 为索引。
        self._pending_message_ids: dict[str, list[str]] = {}
        # NANOBOT_MAX_CONCURRENT_REQUESTS: <=0 表示无限制；默认 3。
        _max = int(os.environ.get("NANOBOT_MAX_CONCURRENT_REQUESTS", "3"))
        self._concurrency_gate: asyncio.Semaphore | None = (
            asyncio.Semaphore(_max) if _max > 0 else None
        )
        self.consolidator = Consolidator(
            store=self.context.memory,
            provider=provider,
            model=self.model,
            sessions=self.sessions,
            context_window_tokens=self.context_window_tokens,
            build_messages=self.context.build_messages,
            get_tool_definitions=self.tools.get_definitions,
            max_completion_tokens=provider.generation.max_tokens,
            consolidation_ratio=consolidation_ratio,
        )
        self.auto_compact = AutoCompact(
            sessions=self.sessions,
            consolidator=self.consolidator,
            session_ttl_minutes=session_ttl_minutes,
        )
        self.dream = Dream(
            store=self.context.memory,
            provider=provider,
            model=self.model,
        )
        self.model_presets: dict[str, ModelPresetConfig] = model_presets or {}
        self._active_preset: str | None = None
        if model_preset:
            self.set_model_preset(model_preset, publish_update=False)
        self._register_default_tools()
        self._runtime_vars: dict[str, Any] = {}
        self._current_iteration: int = 0
        self.commands = CommandRouter()
        register_builtin_commands(self.commands)

    @classmethod
    def from_config(
        cls,
        config: Any,
        bus: MessageBus | None = None,
        **extra: Any,
    ) -> AgentLoop:
        """从配置对象创建 AgentLoop 实例。

        额外关键字参数会被转发给 ``AgentLoop.__init__``，
        允许调用者覆盖或扩展标准配置派生的参数（例如 ``cron_service``、``session_manager``）。
        """
        from nanobot.providers.factory import make_provider

        if bus is None:
            bus = MessageBus()
        defaults = config.agents.defaults
        provider = extra.pop("provider", None) or make_provider(config)
        resolved = config.resolve_preset()
        model = extra.pop("model", None) or resolved.model
        context_window_tokens = extra.pop("context_window_tokens", None) or resolved.context_window_tokens
        provider_snapshot_loader = extra.pop("provider_snapshot_loader", None)
        preset_snapshot_loader = extra.pop("preset_snapshot_loader", None) or preset_helpers.make_preset_snapshot_loader(
            config,
            provider_snapshot_loader,
        )
        return cls(
            bus=bus,
            provider=provider,
            workspace=config.workspace_path,
            model=model,
            max_iterations=defaults.max_tool_iterations,
            context_window_tokens=context_window_tokens,
            context_block_limit=defaults.context_block_limit,
            max_tool_result_chars=defaults.max_tool_result_chars,
            provider_retry_mode=defaults.provider_retry_mode,
            tool_hint_max_length=defaults.tool_hint_max_length,
            restrict_to_workspace=config.tools.restrict_to_workspace,
            mcp_servers=config.tools.mcp_servers,
            channels_config=config.channels,
            timezone=defaults.timezone,
            unified_session=defaults.unified_session,
            disabled_skills=defaults.disabled_skills,
            session_ttl_minutes=defaults.session_ttl_minutes,
            consolidation_ratio=defaults.consolidation_ratio,
            max_messages=defaults.max_messages,
            tools_config=config.tools,
            model_presets=preset_helpers.configured_model_presets(config),
            model_preset=defaults.model_preset,
            provider_snapshot_loader=provider_snapshot_loader,
            preset_snapshot_loader=preset_snapshot_loader,
            **extra,
        )

    def _sync_subagent_runtime_limits(self) -> None:
        """保持子智能体的运行时限制与主循环的可变设置同步。"""
        self.subagents.max_iterations = self.max_iterations

    def _apply_provider_snapshot(
        self,
        snapshot: ProviderSnapshot,
        *,
        publish_update: bool = True,
        model_preset: str | None = None,
    ) -> None:
        """为后续回合切换模型/提供商，不干扰当前正在进行的回合。

        会同步更新 runner、subagents、consolidator、dream 等所有依赖 provider 和 model 的子系统。
        """
        provider = snapshot.provider
        model = snapshot.model
        context_window_tokens = snapshot.context_window_tokens
        old_model = self.model
        self.provider = provider
        self.model = model
        self.context_window_tokens = context_window_tokens
        self.runner.provider = provider
        self.subagents.set_provider(provider, model)
        self.consolidator.set_provider(provider, model, context_window_tokens)
        self.dream.set_provider(provider, model)
        self._provider_signature = snapshot.signature
        if publish_update and self._runtime_model_publisher is not None:
            self._runtime_model_publisher(
                self.model,
                model_preset if model_preset is not None else self.model_preset,
            )
        logger.info("Runtime model switched for next turn: {} -> {}", old_model, model)

    def _refresh_provider_snapshot(self) -> None:
        """刷新提供商配置快照。若签名变化则自动应用新配置。"""
        if self._provider_snapshot_loader is None:
            return
        try:
            snapshot = self._provider_snapshot_loader()
        except Exception:
            logger.exception("Failed to refresh provider config")
            return
        default_selection = preset_helpers.default_selection_signature(snapshot.signature)
        if self._active_preset and self._default_selection_signature in (None, default_selection):
            self._default_selection_signature = default_selection
            try:
                snapshot = self._build_model_preset_snapshot(self._active_preset)
            except Exception:
                logger.exception("Failed to refresh active model preset")
                return
        else:
            self._active_preset = None
            self._default_selection_signature = default_selection
        if snapshot.signature == self._provider_signature:
            return
        self._default_selection_signature = preset_helpers.default_selection_signature(snapshot.signature)
        self._apply_provider_snapshot(snapshot)

    @property
    def model_preset(self) -> str | None:
        """当前激活的模型预设名称。"""
        return self._active_preset

    @model_preset.setter
    def model_preset(self, name: str | None) -> None:
        self.set_model_preset(name)

    def _build_model_preset_snapshot(self, name: str) -> ProviderSnapshot:
        """根据预设名称构建 ProviderSnapshot（包含 provider、model、context_window_tokens）。"""
        return preset_helpers.build_runtime_preset_snapshot(
            name=name,
            presets=self.model_presets,
            provider=self.provider,
            loader=self._preset_snapshot_loader,
        )

    def set_model_preset(self, name: str | None, *, publish_update: bool = True) -> None:
        """按名称解析模型预设并应用到所有运行时模型依赖项。"""
        name = preset_helpers.normalize_preset_name(name, self.model_presets)
        snapshot = self._build_model_preset_snapshot(name)
        self._apply_provider_snapshot(snapshot, publish_update=publish_update, model_preset=name)
        self._active_preset = name

    def _register_default_tools(self) -> None:
        """通过插件加载器注册默认工具集。"""
        from nanobot.agent.tools.context import ToolContext
        from nanobot.agent.tools.loader import ToolLoader

        ctx = ToolContext(
            config=self.tools_config,
            workspace=str(self.workspace),
            bus=self.bus,
            subagent_manager=self.subagents,
            cron_service=self.cron_service,
            sessions=self.sessions,
            provider_snapshot_loader=self._provider_snapshot_loader,
            image_generation_provider_configs=self._image_generation_provider_configs,
            timezone=self.context.timezone or "UTC",
        )
        loader = ToolLoader()
        registered = loader.load(ctx, self.tools)

        # MyTool 需要运行时状态引用，因此手动注册
        if self.tools_config.my.enable:
            self.tools.register(
                MyTool(runtime_state=self, modify_allowed=self.tools_config.my.allow_set)
            )
            registered.append("my")

        logger.info("Registered {} tools: {}", len(registered), registered)

    async def _connect_mcp(self) -> None:
        """连接到配置的 MCP 服务器（一次性、惰性连接）。"""
        if self._mcp_connected or self._mcp_connecting or not self._mcp_servers:
            return
        self._mcp_connecting = True
        from nanobot.agent.tools.mcp import connect_mcp_servers

        try:
            self._mcp_stacks = await connect_mcp_servers(self._mcp_servers, self.tools)
            if self._mcp_stacks:
                self._mcp_connected = True
            else:
                logger.warning("No MCP servers connected successfully (will retry next message)")
        except asyncio.CancelledError:
            logger.warning("MCP connection cancelled (will retry next message)")
            self._mcp_stacks.clear()
        except BaseException as e:
            logger.warning("Failed to connect MCP servers (will retry next message): {}", e)
            self._mcp_stacks.clear()
        finally:
            self._mcp_connecting = False

    def _set_tool_context(
        self, channel: str, chat_id: str,
        message_id: str | None = None, metadata: dict | None = None,
        session_key: str | None = None,
    ) -> None:
        """为所有需要路由信息的工具更新上下文。

        将 channel、chat_id、session_key 等信息封装为 RequestContext，
        设置到所有实现了 ContextAware 接口的工具实例上。
        """
        from nanobot.agent.tools.context import ContextAware, RequestContext

        if session_key is not None:
            effective_key = session_key
        elif self._unified_session:
            effective_key = UNIFIED_SESSION_KEY
        else:
            effective_key = f"{channel}:{chat_id}"

        request_ctx = RequestContext(
            channel=channel,
            chat_id=chat_id,
            message_id=message_id,
            session_key=effective_key,
            metadata=dict(metadata or {}),
        )

        for name in self.tools.tool_names:
            tool = self.tools.get(name)
            if tool and isinstance(tool, ContextAware):
                tool.set_context(request_ctx)

    @staticmethod
    def _runtime_chat_id(msg: InboundMessage) -> str:
        """返回模型运行时元数据中显示的 chat id。

        优先使用 msg.metadata 中的 context_chat_id（某些渠道如 Slack thread 会覆盖），
        否则回退到 msg.chat_id。
        """
        return str(msg.metadata.get("context_chat_id") or msg.chat_id)

    async def _build_bus_progress_callback(
        self, msg: InboundMessage
    ) -> Callable[..., Awaitable[None]]:
        """构建一个进度回调，将进度信息发布到消息总线。"""

        async def _bus_progress(
            content: str,
            *,
            tool_hint: bool = False,
            tool_events: list[dict[str, Any]] | None = None,
            reasoning: bool = False,
            reasoning_end: bool = False,
        ) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            meta["_tool_hint"] = tool_hint
            if reasoning:
                meta["_reasoning_delta"] = True
            if reasoning_end:
                meta["_reasoning_end"] = True
            if tool_events:
                meta["_tool_events"] = tool_events
            await self.bus.publish_outbound(
                OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=content,
                    metadata=meta,
                )
            )

        return _bus_progress

    async def _build_retry_wait_callback(
        self, msg: InboundMessage
    ) -> Callable[[str], Awaitable[None]]:
        """构建一个重试等待回调，将等待信息发布到消息总线。"""

        async def _on_retry_wait(content: str) -> None:
            meta = dict(msg.metadata or {})
            meta["_retry_wait"] = True
            await self.bus.publish_outbound(
                OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=content,
                    metadata=meta,
                )
            )

        return _on_retry_wait

    def _persist_user_message_early(
        self,
        msg: InboundMessage,
        session: Session,
        **kwargs: Any,
    ) -> bool:
        """在回合开始前提前持久化触发消息。

        目的：防止 BUILD 后程序崩溃导致用户消息丢失。
        返回 True 表示消息已被持久化。
        """
        media_paths = [p for p in (msg.media or []) if isinstance(p, str) and p]
        has_text = isinstance(msg.content, str) and msg.content.strip()
        if has_text or media_paths:
            extra: dict[str, Any] = {"media": list(media_paths)} if media_paths else {}
            extra.update(kwargs)
            text = msg.content if isinstance(msg.content, str) else ""
            session.add_message("user", text, **extra)
            self._mark_pending_user_turn(session)
            self.sessions.save(session)
            return True
        return False

    def _build_initial_messages(
        self,
        msg: InboundMessage,
        session: Session,
        history: list[dict[str, Any]],
        pending_summary: str | None,
    ) -> list[dict[str, Any]]:
        """构建本轮 LLM 的初始消息列表（包含历史、当前消息、技能提示等）。"""
        return self.context.build_messages(
            history=history,
            current_message=image_generation_prompt(msg.content, msg.metadata),
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=self._runtime_chat_id(msg),
            sender_id=msg.sender_id,
            session_summary=pending_summary,
            session_metadata=session.metadata,
        )

    async def _dispatch_command_inline(
        self,
        msg: InboundMessage,
        key: str,
        raw: str,
        dispatch_fn: Callable[[CommandContext], Awaitable[OutboundMessage | None]],
    ) -> None:
        """直接从 run() 循环中分发命令并发布结果（用于优先级命令和注入队列中的命令）。"""
        ctx = CommandContext(msg=msg, session=None, key=key, raw=raw, loop=self)
        result = await dispatch_fn(ctx)
        if result:
            await self.bus.publish_outbound(result)
        else:
            logger.warning("Command '{}' matched but dispatch returned None", raw)

    async def _cancel_active_tasks(self, key: str) -> int:
        """取消并等待 *key* 对应的所有活跃任务和子智能体。

        返回被取消的任务数 + 子智能体总数。
        """
        tasks = self._active_tasks.pop(key, [])
        cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
        for t in tasks:
            with suppress(asyncio.CancelledError, Exception):
                await t
        sub_cancelled = await self.subagents.cancel_by_session(key)
        return cancelled + sub_cancelled

    def _effective_session_key(self, msg: InboundMessage) -> str:
        """返回用于任务路由和 mid-turn 注入的有效会话键。

        当启用 unified_session 且消息没有显式覆盖 session_key 时，
        返回统一的默认会话键 UNIFIED_SESSION_KEY。
        """
        if self._unified_session and not msg.session_key_override:
            return UNIFIED_SESSION_KEY
        return msg.session_key

    def _replay_token_budget(self) -> int:
        """根据上下文窗口大小推导用于回放会话历史的 token 预算。

        预留了 LLM 最大输出 token + 1024 的安全余量，防止历史消息过长。
        """
        if self.context_window_tokens <= 0:
            return 0
        max_output = getattr(getattr(self.provider, "generation", None), "max_tokens", 4096)
        try:
            reserved_output = int(max_output)
        except (TypeError, ValueError):
            reserved_output = 4096
        budget = self.context_window_tokens - max(1, reserved_output) - 1024
        return budget if budget > 0 else max(128, self.context_window_tokens // 2)

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[..., Awaitable[None]] | None = None,
        on_stream: Callable[[str], Awaitable[None]] | None = None,
        on_stream_end: Callable[..., Awaitable[None]] | None = None,
        on_retry_wait: Callable[[str], Awaitable[None]] | None = None,
        *,
        session: Session | None = None,
        channel: str = "cli",
        chat_id: str = "direct",
        message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        session_key: str | None = None,
        pending_queue: asyncio.Queue | None = None,
    ) -> tuple[str | None, list[str], list[dict], str, bool]:
        """运行智能体迭代循环（LLM 多轮对话 + 工具执行）。

        参数:
            on_stream: 流式输出时每次收到文本增量调用的回调。
            on_stream_end(resuming): 流式会话结束时调用。
                resuming=True 表示后续还有工具调用（UI 应重新显示 spinner）；
                resuming=False 表示这是最终回复。

        返回: (final_content, tools_used, messages, stop_reason, had_injections)
        """
        self._sync_subagent_runtime_limits()

        loop_hook = AgentProgressHook(
            on_progress=on_progress,
            on_stream=on_stream,
            on_stream_end=on_stream_end,
            channel=channel,
            chat_id=chat_id,
            message_id=message_id,
            metadata=metadata,
            session_key=session_key,
            tool_hint_max_length=self.tool_hint_max_length,
            set_tool_context=self._set_tool_context,
            on_iteration=lambda iteration: setattr(self, "_current_iteration", iteration),
        )
        hook: AgentHook = (
            CompositeHook([loop_hook] + self._extra_hooks) if self._extra_hooks else loop_hook
        )

        async def _checkpoint(payload: dict[str, Any]) -> None:
            """工具执行过程中定期保存运行时 checkpoint。"""
            if session is None:
                return
            self._set_runtime_checkpoint(session, payload)

        async def _drain_pending(*, limit: int = _MAX_INJECTIONS_PER_TURN) -> list[dict[str, Any]]:
            """从 pending queue 中排空 follow-up 消息并注入到 LLM 对话。

            当队列中暂时没有消息但本轮派生的子智能体仍在运行时，会阻塞等待
            至少一个结果到达（或超时 300 秒）。这让 runner 循环保持活跃，
            确保后续子智能体完成结果按顺序注入，而不是被单独调度。
            """
            if pending_queue is None:
                return []

            def _to_user_message(pending_msg: InboundMessage) -> dict[str, Any]:
                content = pending_msg.content
                media = pending_msg.media if pending_msg.media else None
                if media:
                    content, media = extract_documents(content, media)
                    media = media or None
                user_content = self.context._build_user_content(content, media)
                return {"role": "user", "content": user_content}

            items: list[dict[str, Any]] = []
            while len(items) < limit:
                try:
                    items.append(_to_user_message(pending_queue.get_nowait()))
                except asyncio.QueueEmpty:
                    break

            # 若队列中暂时没有消息但本轮派生的子智能体仍在运行，则阻塞等待。
            # 这让 runner 循环保持活跃，确保后续子智能体完成结果按顺序注入，
            # 而不是被单独调度为新的任务。
            if (not items
                    and session is not None
                    and self.subagents.get_running_count_by_session(session.key) > 0):
                try:
                    msg = await asyncio.wait_for(pending_queue.get(), timeout=300)
                except asyncio.TimeoutError:
                    logger.warning(
                        "Timeout waiting for sub-agent completion in session {}",
                        session.key,
                    )
                    return items
                items.append(_to_user_message(msg))
                while len(items) < limit:
                    try:
                        items.append(_to_user_message(pending_queue.get_nowait()))
                    except asyncio.QueueEmpty:
                        break

            return items

        active_session_key = session.key if session else session_key
        file_state_token = bind_file_states(self._file_state_store.for_session(active_session_key))
        try:
            result = await self.runner.run(AgentRunSpec(
                initial_messages=initial_messages,
                tools=self.tools,
                model=self.model,
                max_iterations=self.max_iterations,
                max_tool_result_chars=self.max_tool_result_chars,
                hook=hook,
                error_message="Sorry, I encountered an error calling the AI model.",
                concurrent_tools=True,
                workspace=self.workspace,
                session_key=session.key if session else None,
                context_window_tokens=self.context_window_tokens,
                context_block_limit=self.context_block_limit,
                provider_retry_mode=self.provider_retry_mode,
                progress_callback=on_progress,
                stream_progress_deltas=on_stream is not None,
                retry_wait_callback=on_retry_wait,
                checkpoint_callback=_checkpoint,
                injection_callback=_drain_pending,
                # 持续性目标（sustained goals）的运行时间可能合法地超过 NANOBOT_LLM_TIMEOUT_S；
                # 空闲停滞仍由流式 provider 中的 NANOBOT_STREAM_IDLE_TIMEOUT_S 限制。
                llm_timeout_s=runner_wall_llm_timeout_s(
                    self.sessions,
                    session.key if session is not None else session_key,
                    metadata=(session.metadata if session is not None else None),
                ),
            ))
        finally:
            reset_file_states(file_state_token)
        self._last_usage = result.usage
        if result.stop_reason == "max_iterations":
            logger.warning("Max iterations ({}) reached", self.max_iterations)
            # 将最终内容推送到流中，让流式渠道（如飞书）更新卡片，避免留空。
            if on_stream and on_stream_end:
                await on_stream(result.final_content or "")
                await on_stream_end(resuming=False)
        elif result.stop_reason == "error":
            logger.error("LLM returned error: {}", (result.final_content or "")[:200])
        return result.final_content, result.tools_used, result.messages, result.stop_reason, result.had_injections

    async def run(self) -> None:
        """启动智能体循环主循环，将每条消息作为独立任务派发，以支持 /stop 等命令及时响应。

        主循环逻辑：
        1. 从消息总线消费入站消息（带 1 秒超时，以便定期检查过期会话）。
        2. 优先级命令立即内联处理，不进入正常流程。
        3. 若该会话已有活跃任务，将 follow-up 消息注入到 pending_queue（mid-turn injection）。
        4. 否则创建新任务调用 _dispatch() 处理消息。
        """
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                # 超时后检查是否有会话因 TTL 过期需要自动压缩
                self.auto_compact.check_expired(
                    self._schedule_background,
                    active_session_keys=self._pending_queues.keys(),
                )
                continue
            except asyncio.CancelledError:
                # 保留真正的任务取消信号，以便 shutdown 能干净完成。
                # 仅忽略可能从集成代码泄漏出来的非任务 CancelledError。
                if not self._running or asyncio.current_task().cancelling():
                    raise
                continue
            except Exception as e:
                logger.warning("Error consuming inbound message: {}, continuing...", e)
                continue

            raw = msg.content.strip()
            if self.commands.is_priority(raw):
                # 优先级命令（如 /stop）不排队，直接处理
                await self._dispatch_command_inline(
                    msg, msg.session_key, raw,
                    self.commands.dispatch_priority,
                )
                continue
            effective_key = self._effective_session_key(msg)
            # 如果该会话已经有活跃的 pending queue（即正在处理中），
            # 将消息路由到该队列进行 mid-turn 注入，避免创建竞争任务。
            if effective_key in self._pending_queues:
                # 非优先级命令不允许排队注入，直接分发（与优先级命令相同处理）。
                if self.commands.is_dispatchable_command(raw):
                    await self._dispatch_command_inline(
                        msg, effective_key, raw,
                        self.commands.dispatch,
                    )
                    continue
                pending_msg = msg
                if effective_key != msg.session_key:
                    pending_msg = dataclasses.replace(
                        msg,
                        session_key_override=effective_key,
                    )
                try:
                    self._pending_queues[effective_key].put_nowait(pending_msg)
                except asyncio.QueueFull:
                    logger.warning(
                        "Pending queue full for session {}, falling back to queued task",
                        effective_key,
                    )
                else:
                    logger.info(
                        "Routed follow-up message to pending queue for session {}",
                        effective_key,
                    )
                    # 记录被注入消息的 message_id，以便流结束时清理渠道反应。
                    _msg_id = msg.metadata.get("message_id") if msg.metadata else None
                    if _msg_id:
                        self._pending_message_ids.setdefault(effective_key, []).append(str(_msg_id))
                    continue
            # 在派发前计算有效的 session key，
            # 确保开启 unified session 时 /stop 命令能正确找到对应任务。
            task = asyncio.create_task(self._dispatch(msg))
            self._active_tasks.setdefault(effective_key, []).append(task)
            task.add_done_callback(
                lambda t, k=effective_key: self._active_tasks.get(k, [])
                and self._active_tasks[k].remove(t)
                if t in self._active_tasks.get(k, [])
                else None
            )

    async def _dispatch(self, msg: InboundMessage) -> None:
        """处理单条消息：同一会话串行，跨会话并发。

        处理流程：
        1. 获取该会话的锁和并发门控，保证同一 session_key 一次只处理一个回合。
        2. 注册 pending queue，使本轮处理期间到达的 follow-up 消息可以被注入。
        3. 若用户请求流式输出，构建 on_stream / on_stream_end 回调。
        4. 调用状态机 (_process_message) 完成整个回合。
        5. 发送最终响应、turn_end 信号、可能的 title 生成通知。
        6. 若任务被取消（如 /stop），尝试从 checkpoint 恢复部分上下文。
        7. 清理 pending queue，将剩余消息重新发布到总线以免丢失。
        """
        session_key = self._effective_session_key(msg)
        if session_key != msg.session_key:
            msg = dataclasses.replace(msg, session_key_override=session_key)
        lock = self._session_locks.setdefault(session_key, asyncio.Lock())
        gate = self._concurrency_gate or nullcontext()

        # 注册 pending queue，让本轮处理期间到达的 follow-up 消息
        # 被注入当前回合，而不是 spawn 出新任务。
        pending = asyncio.Queue(maxsize=20)
        self._pending_queues[session_key] = pending

        try:
            async with lock, gate:
                try:
                    on_stream = on_stream_end = None
                    if msg.metadata.get("_wants_stream"):
                        # 将一次回答拆分为多个流式片段（segment），
                        # 每个 segment 对应一段工具调用后的回复或最终回复。
                        stream_base_id = f"{msg.session_key}:{time.time_ns()}"
                        stream_segment = 0

                        def _current_stream_id() -> str:
                            return f"{stream_base_id}:{stream_segment}"

                        async def on_stream(delta: str) -> None:
                            meta = dict(msg.metadata or {})
                            meta["_stream_delta"] = True
                            meta["_stream_id"] = _current_stream_id()
                            await self.bus.publish_outbound(OutboundMessage(
                                channel=msg.channel, chat_id=msg.chat_id,
                                content=delta,
                                metadata=meta,
                            ))

                        async def on_stream_end(*, resuming: bool = False) -> None:
                            nonlocal stream_segment
                            meta = dict(msg.metadata or {})
                            meta["_stream_end"] = True
                            meta["_resuming"] = resuming
                            meta["_stream_id"] = _current_stream_id()
                            # 附加上任何被注入的 follow-up 消息的 message_id，
                            # 让渠道在流结束时一并清理这些消息的反应。
                            if not resuming:
                                injected = self._pending_message_ids.pop(session_key, [])
                                if injected:
                                    meta["_injected_message_ids"] = injected
                            await self.bus.publish_outbound(OutboundMessage(
                                channel=msg.channel, chat_id=msg.chat_id,
                                content="",
                                metadata=meta,
                            ))
                            stream_segment += 1

                    response = await self._process_message(
                        msg, on_stream=on_stream, on_stream_end=on_stream_end,
                        pending_queue=pending,
                    )
                    if response is not None:
                        await self.bus.publish_outbound(response)
                    elif msg.channel == "cli":
                        # CLI 通道即使无内容也需要发送一个空消息，以保持交互一致性
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id,
                            content="", metadata=msg.metadata or {},
                        ))
                    if msg.channel == "websocket":
                        # 发送 turn_end 信号，表示本轮已完全结束（所有工具执行完毕、最终文本已流式输出）。
                        # 这让 WebSocket 客户端知道何时可以停止 loading 动画。
                        turn_lat = self._pending_turn_latency_ms.pop(session_key, None)
                        turn_metadata: dict[str, Any] = {**msg.metadata, "_turn_end": True}
                        if turn_lat is not None:
                            turn_metadata["latency_ms"] = int(turn_lat)
                        sess_turn = self.sessions.get_or_create(session_key)
                        turn_metadata["goal_state"] = goal_state_ws_blob(sess_turn.metadata)
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id,
                            content="", metadata=turn_metadata,
                        ))
                        if msg.metadata.get("webui") is True:
                            # 异步生成会话标题并通知前端刷新
                            async def _generate_title_and_notify() -> None:
                                generated = await maybe_generate_webui_title_after_turn(
                                    channel=msg.channel,
                                    metadata=msg.metadata,
                                    sessions=self.sessions,
                                    session_key=session_key,
                                    provider=self.provider,
                                    model=self.model,
                                )
                                if generated:
                                    await self.bus.publish_outbound(OutboundMessage(
                                        channel=msg.channel,
                                        chat_id=msg.chat_id,
                                        content="",
                                        metadata={**msg.metadata, "_session_updated": True},
                                    ))

                            self._schedule_background(_generate_title_and_notify())
                except asyncio.CancelledError:
                    logger.info("Task cancelled for session {}", session_key)
                    # 保留中断回合的部分上下文，让用户不会丢失 /stop 之前
                    # 已经产生的工具结果和助手消息。checkpoint 在工具执行期间
                    # 已被 _emit_checkpoint 写入会话元数据；现在将其物化到会话历史中，
                    # 使它在下一轮对话中可见。
                    try:
                        key = self._effective_session_key(msg)
                        session = self.sessions.get_or_create(key)
                        if self._restore_runtime_checkpoint(session):
                            self._clear_pending_user_turn(session)
                            self.sessions.save(session)
                            logger.info(
                                "Restored partial context for cancelled session {}",
                                key,
                            )
                    except Exception:
                        logger.debug(
                            "Could not restore checkpoint for cancelled session {}",
                            session_key,
                            exc_info=True,
                        )
                    raise
                except Exception:
                    logger.exception("Error processing message for session {}", session_key)
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel, chat_id=msg.chat_id,
                        content="Sorry, I encountered an error.",
                    ))
        finally:
            # 排空 pending queue 中剩余的消息并重新发布到总线，
            # 使它们作为新的入站消息被处理，而不是静默丢失。
            queue = self._pending_queues.pop(session_key, None)
            if queue is not None:
                leftover = 0
                while True:
                    try:
                        item = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    await self.bus.publish_inbound(item)
                    leftover += 1
                if leftover:
                    logger.info(
                        "Re-published {} leftover message(s) to bus for session {}",
                        leftover, session_key,
                    )
            # 清理该会话未被追踪的注入消息 ID。
            self._pending_message_ids.pop(session_key, None)
            await publish_turn_run_status(self.bus, msg, "idle")
            self._pending_turn_latency_ms.pop(session_key, None)

    async def close_mcp(self) -> None:
        """排空挂起的后台归档任务，然后关闭 MCP 连接。"""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()
        for name, stack in self._mcp_stacks.items():
            try:
                await stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                logger.debug("MCP server '{}' cleanup error (can be ignored)", name)
        self._mcp_stacks.clear()

    def _schedule_background(self, coro) -> None:
        """将协程调度为受跟踪的后台任务（shutdown 时会等待其完成）。"""
        task = asyncio.create_task(coro)
        self._background_tasks.append(task)
        task.add_done_callback(self._background_tasks.remove)

    def stop(self) -> None:
        """停止智能体主循环。"""
        self._running = False
        logger.info("Agent loop stopping")

    async def _process_system_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[..., Awaitable[None]] | None = None,
        on_stream: Callable[[str], Awaitable[None]] | None = None,
        on_stream_end: Callable[..., Awaitable[None]] | None = None,
        pending_queue: asyncio.Queue | None = None,
    ) -> OutboundMessage | None:
        """处理系统入站消息（例如子智能体结果通知、后台任务完成等）。

        与普通用户消息流程类似，但 sender_id 为 "subagent" 时当前角色视为 assistant。
        """
        channel, chat_id = (
            msg.chat_id.split(":", 1) if ":" in msg.chat_id else ("cli", msg.chat_id)
        )
        logger.info("Processing system message from {}", msg.sender_id)
        key = msg.session_key_override or f"{channel}:{chat_id}"
        session = self.sessions.get_or_create(key)
        if self._restore_runtime_checkpoint(session):
            self.sessions.save(session)
        if self._restore_pending_user_turn(session):
            self.sessions.save(session)

        session, pending = self.auto_compact.prepare_session(session, key)
        if pending:
            logger.info("Memory compact triggered for session {}", key)

        await self.consolidator.maybe_consolidate_by_tokens(
            session,
            replay_max_messages=self._max_messages,
        )
        is_subagent = msg.sender_id == "subagent"
        if is_subagent and self._persist_subagent_followup(session, msg):
            logger.debug("Subagent result persisted for session {}", key)
            self.sessions.save(session)
        self._set_tool_context(
            channel, chat_id, msg.metadata.get("message_id"),
            msg.metadata, session_key=key,
        )
        _hist_kwargs: dict[str, Any] = {
            "max_messages": self._max_messages,
            "max_tokens": self._replay_token_budget(),
            "include_timestamps": True,
        }
        history = session.get_history(**_hist_kwargs)
        current_role = "assistant" if is_subagent else "user"

        messages = self.context.build_messages(
            history=history,
            current_message="" if is_subagent else msg.content,
            channel=channel,
            chat_id=chat_id,
            current_role=current_role,
            sender_id=msg.sender_id,
            session_summary=pending,
            session_metadata=session.metadata,
        )
        t_wall = time.time()
        final_content, _, all_msgs, stop_reason, _ = await self._run_agent_loop(
            messages, session=session, channel=channel, chat_id=chat_id,
            message_id=msg.metadata.get("message_id"),
            metadata=msg.metadata,
            session_key=key,
            pending_queue=pending_queue,
        )
        wall_done = time.time()
        latency_ms = max(0, int((wall_done - t_wall) * 1000))
        self._save_turn(session, all_msgs, 1 + len(history), turn_latency_ms=latency_ms)
        if channel == "websocket":
            self._pending_turn_latency_ms[key] = latency_ms
        session.enforce_file_cap(on_archive=self.context.memory.raw_archive)
        self._clear_runtime_checkpoint(session)
        self.sessions.save(session)
        self._schedule_background(
            self.consolidator.maybe_consolidate_by_tokens(
                session,
                replay_max_messages=self._max_messages,
            )
        )
        content = final_content or "Background task completed."
        outbound_metadata: dict[str, Any] = {}
        if channel == "slack" and key.startswith("slack:") and key.count(":") >= 2:
            outbound_metadata["slack"] = {"thread_ts": key.split(":", 2)[2]}
        if origin_message_id := msg.metadata.get("origin_message_id"):
            outbound_metadata["origin_message_id"] = origin_message_id
        return OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=content,
            metadata=outbound_metadata,
        )

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[..., Awaitable[None]] | None = None,
        on_stream: Callable[[str], Awaitable[None]] | None = None,
        on_stream_end: Callable[..., Awaitable[None]] | None = None,
        pending_queue: asyncio.Queue | None = None,
    ) -> OutboundMessage | None:
        """处理单条入站消息并通过状态机返回响应。

        状态机流程：RESTORE → COMPACT → COMMAND → BUILD → RUN → SAVE → RESPOND → DONE
        每个阶段对应 _state_{name} 方法，阶段之间通过 _TRANSITIONS 表驱动。
        """
        self._refresh_provider_snapshot()

        if msg.channel == "system":
            return await self._process_system_message(
                msg,
                session_key=session_key,
                on_progress=on_progress,
                on_stream=on_stream,
                on_stream_end=on_stream_end,
                pending_queue=pending_queue,
            )

        key = session_key or msg.session_key
        ctx = TurnContext(
            msg=msg,
            session=None,
            session_key=key,
            state=TurnState.RESTORE,
            turn_id=f"{key}:{time.time_ns()}",
            on_progress=on_progress,
            on_stream=on_stream,
            on_stream_end=on_stream_end,
            pending_queue=pending_queue,
        )

        while ctx.state is not TurnState.DONE:
            handler_name = f"_state_{ctx.state.name.lower()}"
            handler = getattr(self, handler_name, None)
            if handler is None:
                raise RuntimeError(f"Missing state handler for {ctx.state}")

            t0 = time.perf_counter()
            try:
                event = await handler(ctx)
            except Exception:
                duration = (time.perf_counter() - t0) * 1000
                ctx.trace.append(
                    StateTraceEntry(
                        state=ctx.state,
                        started_at=t0,
                        duration_ms=duration,
                        event="",
                        error="exception",
                    )
                )
                raise

            duration = (time.perf_counter() - t0) * 1000
            ctx.trace.append(
                StateTraceEntry(
                    state=ctx.state,
                    started_at=t0,
                    duration_ms=duration,
                    event=event,
                )
            )
            logger.debug(
                "[turn {}] State {} took {:.1f}ms -> event {}",
                ctx.turn_id,
                ctx.state.name,
                duration,
                event,
            )

            next_state = self._TRANSITIONS.get((ctx.state, event))
            if next_state is None:
                raise RuntimeError(
                    f"[turn {ctx.turn_id}] No transition from {ctx.state} "
                    f"on event {event!r}"
                )
            ctx.state = next_state

        logger.debug(
            "[turn {}] Turn completed after {} states",
            ctx.turn_id,
            len(ctx.trace),
        )
        return ctx.outbound

    def _assemble_outbound(
        self,
        msg: InboundMessage,
        final_content: str,
        all_msgs: list[dict[str, Any]],
        stop_reason: str,
        had_injections: bool,
        generated_media: list[str],
        on_stream: Callable[[str], Awaitable[None]] | None,
        *,
        turn_latency_ms: int | None = None,
    ) -> OutboundMessage | None:
        """根据回合结果组装最终 outbound 消息。

        特殊处理：若 message 工具在本轮已主动发送过消息，且没有用户注入或空回复，
        则抑制默认的 outbound 消息（避免重复通知）。
        """
        # MessageTool 抑制：若 message 工具已在本轮主动发送过消息
        if (mt := self.tools.get("message")) and isinstance(mt, MessageTool) and mt._sent_in_turn:
            if not had_injections or stop_reason == "empty_final_response":
                return None

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}:{}: {}", msg.channel, msg.sender_id, preview)

        meta = dict(msg.metadata or {})
        if on_stream is not None and stop_reason not in {"error", "tool_error"}:
            meta["_streamed"] = True
        if turn_latency_ms is not None:
            meta["latency_ms"] = int(turn_latency_ms)

        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            media=generated_media,
            metadata=meta,
        )

    async def _state_restore(self, ctx: TurnContext) -> TurnState:
        """RESTORE 阶段：从 checkpoint / pending user turn 恢复；提取文档附件。

        1. 若消息携带媒体文件，提取文档（如图片转 OCR 文本）。
        2. 确保会话对象存在。
        3. 恢复之前中断的运行时 checkpoint 和待处理的用户消息。
        """
        msg = ctx.msg

        if msg.media:
            new_content, image_only = extract_documents(msg.content, msg.media)
            ctx.msg = dataclasses.replace(msg, content=new_content, media=image_only)
            msg = ctx.msg

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        # 会话通常已由调用者（_process_message）获取，但在此独立调用时也要确保存在。
        if ctx.session is None:
            ctx.session = self.sessions.get_or_create(ctx.session_key)
        mark_webui_session(ctx.session, msg.metadata)

        if self._restore_runtime_checkpoint(ctx.session):
            self.sessions.save(ctx.session)
        if self._restore_pending_user_turn(ctx.session):
            self.sessions.save(ctx.session)

        return "ok"

    async def _state_compact(self, ctx: TurnContext) -> str:
        """COMPACT 阶段：自动压缩过期或超长的会话历史。"""
        ctx.session, pending = self.auto_compact.prepare_session(ctx.session, ctx.session_key)
        ctx.pending_summary = pending
        return "ok"

    async def _state_command(self, ctx: TurnContext) -> str:
        """COMMAND 阶段：识别并执行用户输入的斜杠命令。

        若命令匹配并返回了 OutboundMessage（shortcut），则跳过 BUILD/SAVE 直接结束回合。
        此时需要提前将用户消息和助手回复持久化，以便 WebUI 历史记录能看到该命令交互。
        标记 _command=True 使 get_history 在构建 LLM 上下文时可过滤掉这些命令消息。
        /new 命令被排除，因为它会主动清空会话。
        """
        raw = ctx.msg.content.strip()
        cmd_ctx = CommandContext(
            msg=ctx.msg, session=ctx.session, key=ctx.session_key, raw=raw, loop=self
        )
        result = await self.commands.dispatch(cmd_ctx)
        if result is not None:
            ctx.outbound = result
            # Shortcut 命令跳过了 BUILD 和 SAVE，所以必须在这里手动持久化回合，
            # 否则 WebUI 在 _turn_end 后 hydrating 历史记录时看不到该消息。
            # 用 _command 标记，让 get_history 在构造 LLM 上下文时过滤掉它们。
            # /new 被排除，因为它会故意清空会话。
            if raw.lower() != "/new":
                ctx.user_persisted_early = self._persist_user_message_early(
                    ctx.msg, ctx.session, _command=True
                )
                ctx.session.add_message(
                    "assistant", result.content, _command=True
                )
                self.sessions.save(ctx.session)
                self._clear_pending_user_turn(ctx.session)
            return "shortcut"
        return "dispatch"

    async def _state_build(self, ctx: TurnContext) -> str:
        """BUILD 阶段：组装 LLM 所需的完整消息上下文。

        1. 按需触发记忆压缩（consolidation）。
        2. 设置工具的会话上下文（channel、chat_id 等路由信息）。
        3. 若启用了 message 工具，开始新的一轮追踪。
        4. 从会话中读取带预算控制的历史记录。
        5. 构建包含当前消息、技能、系统提示的 initial_messages。
        6. 提前持久化用户消息（防止 BUILD 后崩溃导致消息丢失）。
        7. 构建进度和重试等待回调。
        """
        await self.consolidator.maybe_consolidate_by_tokens(
            ctx.session,
            replay_max_messages=self._max_messages,
        )
        self._set_tool_context(
            ctx.msg.channel,
            ctx.msg.chat_id,
            ctx.msg.metadata.get("message_id"),
            ctx.msg.metadata,
            session_key=ctx.session_key,
        )
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.start_turn()

        _hist_kwargs: dict[str, Any] = {
            "max_messages": self._max_messages,
            "max_tokens": self._replay_token_budget(),
            "include_timestamps": True,
        }
        ctx.history = ctx.session.get_history(**_hist_kwargs)

        ctx.initial_messages = self._build_initial_messages(
            ctx.msg, ctx.session, ctx.history, ctx.pending_summary
        )
        ctx.user_persisted_early = self._persist_user_message_early(
            ctx.msg, ctx.session
        )

        if ctx.on_progress is None:
            ctx.on_progress = await self._build_bus_progress_callback(ctx.msg)
        if ctx.on_retry_wait is None:
            ctx.on_retry_wait = await self._build_retry_wait_callback(ctx.msg)

        return "ok"

    async def _state_run(self, ctx: TurnContext) -> str:
        """RUN 阶段：调用 AgentRunner 运行 LLM 多轮迭代（工具调用循环）。"""
        await publish_turn_run_status(self.bus, ctx.msg, "running")
        result = await self._run_agent_loop(
            ctx.initial_messages,
            on_progress=ctx.on_progress,
            on_stream=ctx.on_stream,
            on_stream_end=ctx.on_stream_end,
            on_retry_wait=ctx.on_retry_wait,
            session=ctx.session,
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            message_id=ctx.msg.metadata.get("message_id"),
            metadata=ctx.msg.metadata,
            session_key=ctx.session_key,
            pending_queue=ctx.pending_queue,
        )
        final_content, tools_used, all_msgs, stop_reason, had_injections = result
        ctx.final_content = final_content
        ctx.tools_used = tools_used
        ctx.all_messages = all_msgs
        ctx.stop_reason = stop_reason
        ctx.had_injections = had_injections
        return "ok"

    async def _state_save(self, ctx: TurnContext) -> str:
        """SAVE 阶段：将本轮 LLM 产生的新消息持久化到会话存储。

        1. 若 LLM 最终无内容，使用 EMPTY_FINAL_RESPONSE_MESSAGE 兜底。
        2. 计算需要跳过的历史消息数（避免重复保存旧消息）。
        3. 提取本轮生成的媒体文件并合并到最后的 assistant 消息。
        4. 计算回合耗时并保存所有新消息。
        5. 清理 checkpoint 和 pending user turn 标记。
        6. 触发后台的记忆压缩任务。
        """
        if ctx.final_content is None or not ctx.final_content.strip():
            ctx.final_content = EMPTY_FINAL_RESPONSE_MESSAGE

        ctx.save_skip = 1 + len(ctx.history) + (1 if ctx.user_persisted_early else 0)
        skip_msgs = ctx.all_messages[ctx.save_skip:]
        ctx.generated_media = generated_image_paths_from_messages(skip_msgs)
        mt = self.tools.get("message")
        extra = getattr(mt, "turn_delivered_media_paths", lambda: [])() if mt else []
        merge_turn_media_into_last_assistant(ctx.all_messages, ctx.generated_media, extra)

        ctx.turn_latency_ms = max(0, int((time.time() - ctx.turn_wall_started_at) * 1000))
        self._save_turn(
            ctx.session, ctx.all_messages, ctx.save_skip,
            turn_latency_ms=ctx.turn_latency_ms,
        )
        if ctx.msg.channel == "websocket":
            self._pending_turn_latency_ms[ctx.session_key] = ctx.turn_latency_ms
        ctx.session.enforce_file_cap(on_archive=self.context.memory.raw_archive)
        self._clear_pending_user_turn(ctx.session)
        self._clear_runtime_checkpoint(ctx.session)
        self.sessions.save(ctx.session)
        self._schedule_background(
            self.consolidator.maybe_consolidate_by_tokens(
                ctx.session,
                replay_max_messages=self._max_messages,
            )
        )
        return "ok"

    async def _state_respond(self, ctx: TurnContext) -> str:
        """RESPOND 阶段：根据回合结果组装最终 outbound 消息。"""
        ctx.outbound = self._assemble_outbound(
            ctx.msg,
            ctx.final_content,
            ctx.all_messages,
            ctx.stop_reason,
            ctx.had_injections,
            ctx.generated_media,
            ctx.on_stream,
            turn_latency_ms=ctx.turn_latency_ms,
        )
        return "ok"

    def _sanitize_persisted_blocks(
        self,
        content: list[dict[str, Any]],
        *,
        should_truncate_text: bool = False,
        drop_runtime: bool = False,
    ) -> list[dict[str, Any]]:
        """在写入会话历史前，清理易变的多模态载荷。

        处理规则：
        - 若 drop_runtime=True，丢弃运行时上下文文本块。
        - 将 base64 编码的图片 URL 替换为占位文本。
        - 若 should_truncate_text=True，截断超长文本块。
        """
        filtered: list[dict[str, Any]] = []
        for block in content:
            if not isinstance(block, dict):
                filtered.append(block)
                continue

            if (
                drop_runtime
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
                and block["text"].startswith(ContextBuilder._RUNTIME_CONTEXT_TAG)
            ):
                continue

            if block.get("type") == "image_url" and block.get("image_url", {}).get(
                "url", ""
            ).startswith("data:image/"):
                path = (block.get("_meta") or {}).get("path", "")
                filtered.append({"type": "text", "text": image_placeholder_text(path)})
                continue

            if block.get("type") == "text" and isinstance(block.get("text"), str):
                text = block["text"]
                if should_truncate_text and len(text) > self.max_tool_result_chars:
                    text = truncate_text_fn(text, self.max_tool_result_chars)
                filtered.append({**block, "text": text})
                continue

            filtered.append(block)

        return filtered

    def _save_turn(
        self,
        session: Session,
        messages: list[dict],
        skip: int,
        *,
        turn_latency_ms: int | None = None,
    ) -> None:
        """将本轮新生成的消息保存到会话中，并截断过大的工具结果。

        保存策略：
        - 跳过空的助手消息（无内容且无 tool_calls），避免污染会话上下文。
        - 工具结果若超长则截断文本；列表内容块也经过 _sanitize_persisted_blocks 处理。
        - 用户消息中若包含运行时上下文标签，则剥离该标签及其后的内容。
        - 为每条消息自动添加时间戳；为最后一条助手消息记录本轮耗时。
        """
        from datetime import datetime

        last_assistant_idx: int | None = None
        for m in messages[skip:]:
            entry = dict(m)
            role, content = entry.get("role"), entry.get("content")
            if role == "assistant" and not content and not entry.get("tool_calls"):
                continue  # 跳过空的助手消息——它们会污染会话上下文
            if role == "tool":
                if isinstance(content, str) and len(content) > self.max_tool_result_chars:
                    entry["content"] = truncate_text_fn(content, self.max_tool_result_chars)
                elif isinstance(content, list):
                    filtered = self._sanitize_persisted_blocks(content, should_truncate_text=True)
                    if not filtered:
                        continue
                    entry["content"] = filtered
            elif role == "user":
                if isinstance(content, str) and ContextBuilder._RUNTIME_CONTEXT_TAG in content:
                    # 剥离末尾追加的运行时上下文块
                    tag_pos = content.find(ContextBuilder._RUNTIME_CONTEXT_TAG)
                    before = content[:tag_pos].rstrip("\n ")
                    if before:
                        entry["content"] = before
                    else:
                        continue
                if isinstance(content, list):
                    filtered = self._sanitize_persisted_blocks(content, drop_runtime=True)
                    if not filtered:
                        continue
                    entry["content"] = filtered
            entry.setdefault("timestamp", datetime.now().isoformat())
            session.messages.append(entry)
            if role == "assistant":
                last_assistant_idx = len(session.messages) - 1
        if turn_latency_ms is not None and last_assistant_idx is not None:
            session.messages[last_assistant_idx]["latency_ms"] = int(turn_latency_ms)
        session.updated_at = datetime.now()

    def _persist_subagent_followup(self, session: Session, msg: InboundMessage) -> bool:
        """在 prompt 组装前持久化子智能体 follow-up，使历史记录保持持久。

        返回 True 表示追加了新条目；False 表示去重（session 中已有相同
        subagent_task_id）或内容为空无需保存。
        """
        if not msg.content:
            return False
        task_id = msg.metadata.get("subagent_task_id") if isinstance(msg.metadata, dict) else None
        if task_id and any(
            m.get("injected_event") == "subagent_result" and m.get("subagent_task_id") == task_id
            for m in session.messages
        ):
            return False
        session.add_message(
            "assistant",
            msg.content,
            sender_id=msg.sender_id,
            injected_event="subagent_result",
            subagent_task_id=task_id,
        )
        return True

    def _set_runtime_checkpoint(self, session: Session, payload: dict[str, Any]) -> None:
        """将最新的飞行中（in-flight）回合状态持久化到会话元数据。

        在工具执行期间定期调用，以便 /stop 或崩溃后能恢复部分上下文。
        """
        session.metadata[self._RUNTIME_CHECKPOINT_KEY] = payload
        self.sessions.save(session)

    def _mark_pending_user_turn(self, session: Session) -> None:
        """标记该会话存在一个已持久化但尚未获得回复的用户消息。"""
        session.metadata[self._PENDING_USER_TURN_KEY] = True

    def _clear_pending_user_turn(self, session: Session) -> None:
        """清除 pending user turn 标记。"""
        session.metadata.pop(self._PENDING_USER_TURN_KEY, None)

    def _clear_runtime_checkpoint(self, session: Session) -> None:
        """清除运行时 checkpoint。回合正常结束时调用。"""
        if self._RUNTIME_CHECKPOINT_KEY in session.metadata:
            session.metadata.pop(self._RUNTIME_CHECKPOINT_KEY, None)

    @staticmethod
    def _checkpoint_message_key(message: dict[str, Any]) -> tuple[Any, ...]:
        """生成消息的摘要键，用于判断 session 中已存在哪些消息（避免恢复时重复）。"""
        return (
            message.get("role"),
            message.get("content"),
            message.get("tool_call_id"),
            message.get("name"),
            message.get("tool_calls"),
            message.get("reasoning_content"),
            message.get("thinking_blocks"),
        )

    def _restore_runtime_checkpoint(self, session: Session) -> bool:
        """将未完成的回合物化到会话历史中，供下一轮请求使用。

        恢复来源是 session.metadata 中保存的 runtime checkpoint，包含：
        - assistant_message: 助手发出的带 tool_calls 的消息
        - completed_tool_results: 已完成的工具结果
        - pending_tool_calls: 尚未完成的工具调用（标记为错误）

        为避免重复追加，会先检测 session.messages 末尾与 restored_messages
        前缀的重叠部分（通过 _checkpoint_message_key 比较）。
        """
        from datetime import datetime

        checkpoint = session.metadata.get(self._RUNTIME_CHECKPOINT_KEY)
        if not isinstance(checkpoint, dict):
            return False

        assistant_message = checkpoint.get("assistant_message")
        completed_tool_results = checkpoint.get("completed_tool_results") or []
        pending_tool_calls = checkpoint.get("pending_tool_calls") or []

        restored_messages: list[dict[str, Any]] = []
        if isinstance(assistant_message, dict):
            restored = dict(assistant_message)
            restored.setdefault("timestamp", datetime.now().isoformat())
            restored_messages.append(restored)
        for message in completed_tool_results:
            if isinstance(message, dict):
                restored = dict(message)
                restored.setdefault("timestamp", datetime.now().isoformat())
                restored_messages.append(restored)
        for tool_call in pending_tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_id = tool_call.get("id")
            name = ((tool_call.get("function") or {}).get("name")) or "tool"
            restored_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": name,
                    "content": "Error: Task interrupted before this tool finished.",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 检测重叠：session 末尾可能已有部分恢复过的消息
        overlap = 0
        max_overlap = min(len(session.messages), len(restored_messages))
        for size in range(max_overlap, 0, -1):
            existing = session.messages[-size:]
            restored = restored_messages[:size]
            if all(
                self._checkpoint_message_key(left) == self._checkpoint_message_key(right)
                for left, right in zip(existing, restored)
            ):
                overlap = size
                break
        session.messages.extend(restored_messages[overlap:])

        self._clear_pending_user_turn(session)
        self._clear_runtime_checkpoint(session)
        return True

    def _restore_pending_user_turn(self, session: Session) -> bool:
        """处理崩溃前仅持久化了用户消息、未生成回复的回合。

        若 session 最后一条消息是用户消息，则追加一条错误提示的助手消息，
        让用户知道上一轮因中断而未完成。
        """
        from datetime import datetime

        if not session.metadata.get(self._PENDING_USER_TURN_KEY):
            return False

        if session.messages and session.messages[-1].get("role") == "user":
            session.messages.append(
                {
                    "role": "assistant",
                    "content": "Error: Task interrupted before a response was generated.",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            session.updated_at = datetime.now()

        self._clear_pending_user_turn(session)
        return True

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        media: list[str] | None = None,
        on_progress: Callable[..., Awaitable[None]] | None = None,
        on_stream: Callable[[str], Awaitable[None]] | None = None,
        on_stream_end: Callable[..., Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """直接处理一条消息并返回 outbound 载荷（用于 CLI/SDK 直接调用）。"""
        await self._connect_mcp()
        msg = InboundMessage(
            channel=channel, sender_id="user", chat_id=chat_id,
            content=content, media=media or [],
        )
        return await self._process_message(
            msg,
            session_key=session_key,
            on_progress=on_progress,
            on_stream=on_stream,
            on_stream_end=on_stream_end,
        )
