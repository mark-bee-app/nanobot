"""Session management for conversation history."""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.config.paths import get_legacy_sessions_dir
from nanobot.utils.helpers import ensure_dir, find_legal_message_start, safe_filename


@dataclass
class Session:
    """对话会话 (Session) 表示。

    封装了聊天过程中所产生的所有消息，并处理消息对齐、历史截断和元数据存储。
    """

    key: str  # 会话的唯一标识，通常格式为 channel:chat_id
    messages: list[dict[str, Any]] = field(default_factory=list)  # 会话中的所有消息列表
    created_at: datetime = field(default_factory=datetime.now)  # 会话创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 会话最后更新时间
    metadata: dict[str, Any] = field(default_factory=dict)  # 用于存储与会话相关的额外元数据
    last_consolidated: int = 0  # 已经整合（即总结归档）到文件中的消息数量

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """向会话中添加一条新消息。

        Args:
            role: 消息的发送者角色（例如 "user", "assistant" 或 "system"）。
            content: 消息的具体文本内容。
            **kwargs: 附加的消息属性（例如 tool_calls 等）。
        """
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()

    def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """获取尚未归档的消息记录以作为 LLM 的输入，并确保消息截断在合法的工具调用边界处。

        Args:
            max_messages: 返回的最大消息数，默认为 500。

        Returns:
            处理后且符合规范的消息列表。
        """
        unconsolidated = self.messages[self.last_consolidated:]
        sliced = unconsolidated[-max_messages:]

        # 尽量避免从对话中间（即 AI 回复或工具调用的中间）截断，尽量以用户的发言作为起点
        for i, message in enumerate(sliced):
            if message.get("role") == "user":
                sliced = sliced[i:]
                break

        # 清除位于截断开头的孤立工具结果（即缺乏工具调用的直接结果）
        start = find_legal_message_start(sliced)
        if start:
            sliced = sliced[start:]

        out: list[dict[str, Any]] = []
        for message in sliced:
            entry: dict[str, Any] = {"role": message["role"], "content": message.get("content", "")}
            for key in ("tool_calls", "tool_call_id", "name", "reasoning_content"):
                if key in message:
                    entry[key] = message[key]
            out.append(entry)
        return out

    def clear(self) -> None:
        """清除会话中的所有消息，重置会话到初始状态。"""
        self.messages = []
        self.last_consolidated = 0
        self.updated_at = datetime.now()

    def retain_recent_legal_suffix(self, max_messages: int) -> None:
        """只保留最近一定数量的消息后缀，截断规则与 `get_history` 相同以确保合法边界。

        此操作会修改 `self.messages` 以丢弃过旧的消息。

        Args:
            max_messages: 需要保留的最大消息条数。
        """
        if max_messages <= 0:
            self.clear()
            return
        if len(self.messages) <= max_messages:
            return

        start_idx = max(0, len(self.messages) - max_messages)

        # 如果截断点正好落在对话中间，则向前回溯直至找到最近的一条用户消息
        while start_idx > 0 and self.messages[start_idx].get("role") != "user":
            start_idx -= 1

        retained = self.messages[start_idx:]

        # 类似于 get_history()：避免在截断结果开头保留孤立的工具调用结果
        start = find_legal_message_start(retained)
        if start:
            retained = retained[start:]

        dropped = len(self.messages) - len(retained)
        self.messages = retained
        # 更新已归档消息计数，确保不会出现负数
        self.last_consolidated = max(0, self.last_consolidated - dropped)
        self.updated_at = datetime.now()


class SessionManager:
    """会话管理器。

    用于管理对话的加载、保存和列举。会话数据会被存储为 JSONL 格式的文件。
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_dir = ensure_dir(self.workspace / "sessions")
        self.legacy_sessions_dir = get_legacy_sessions_dir()
        self._cache: dict[str, Session] = {}

    def _get_session_path(self, key: str) -> Path:
        """获取当前工作区中会话文件的存储路径。"""
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"

    def _get_legacy_session_path(self, key: str) -> Path:
        """获取旧版全局会话路径 (~/.nanobot/sessions/) 以支持向后兼容。"""
        safe_key = safe_filename(key.replace(":", "_"))
        return self.legacy_sessions_dir / f"{safe_key}.jsonl"

    def get_or_create(self, key: str) -> Session:
        """获取已存在的会话或创建一个新会话。

        Args:
            key: 会话标识符（通常为 channel:chat_id）。

        Returns:
            对应的 Session 实例。
        """
        if key in self._cache:
            return self._cache[key]

        session = self._load(key)
        if session is None:
            session = Session(key=key)

        self._cache[key] = session
        return session

    def _load(self, key: str) -> Session | None:
        """从磁盘读取并加载会话数据。

        如果当前工作区中没有该会话，并且存在旧版路径下的数据，则尝试将其迁移。
        """
        path = self._get_session_path(key)
        if not path.exists():
            legacy_path = self._get_legacy_session_path(key)
            if legacy_path.exists():
                try:
                    shutil.move(str(legacy_path), str(path))
                    logger.info("已从旧版路径迁移会话 {}", key)
                except Exception:
                    logger.exception("无法迁移会话 {}", key)

        if not path.exists():
            return None

        try:
            messages = []
            metadata = {}
            created_at = None
            last_consolidated = 0

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)

                    # 第一行通常包含会话的元数据
                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                        last_consolidated = data.get("last_consolidated", 0)
                    else:
                        messages.append(data)

            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata,
                last_consolidated=last_consolidated
            )
        except Exception as e:
            logger.warning("加载会话 {} 失败: {}", key, e)
            return None

    def save(self, session: Session) -> None:
        """将会话数据保存到磁盘文件中（以 JSONL 格式存储）。"""
        path = self._get_session_path(session.key)

        with open(path, "w", encoding="utf-8") as f:
            metadata_line = {
                "_type": "metadata",
                "key": session.key,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata,
                "last_consolidated": session.last_consolidated
            }
            f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        self._cache[session.key] = session

    def invalidate(self, key: str) -> None:
        """从内存缓存中移除指定的会话。"""
        self._cache.pop(key, None)

    def list_sessions(self) -> list[dict[str, Any]]:
        """列举当前存储目录中的所有会话。

        Returns:
            包含会话基本信息（如键、创建时间和最后更新时间、路径）的字典列表，并按更新时间降序排列。
        """
        sessions = []

        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                # Read just the metadata line
                with open(path, encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            key = data.get("key") or path.stem.replace("_", ":", 1)
                            sessions.append({
                                "key": key,
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                                "path": str(path)
                            })
            except Exception:
                continue

        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)
