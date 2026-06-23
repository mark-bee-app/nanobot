"""Tests for the /read slash command."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.command.builtin import (
    builtin_command_palette,
    build_help_text,
    cmd_read,
    register_builtin_commands,
)
from nanobot.command.router import CommandContext, CommandRouter
from nanobot.config.schema import ModelPresetConfig


def _provider(default_model: str = "base-model", max_tokens: int = 123) -> MagicMock:
    provider = MagicMock()
    provider.get_default_model.return_value = default_model
    provider.generation = MagicMock(
        max_tokens=max_tokens,
        temperature=0.1,
        reasoning_effort=None,
    )
    return provider


def _make_loop(tmp_path: Path) -> AgentLoop:
    return AgentLoop(
        bus=MessageBus(),
        provider=_provider(),
        workspace=tmp_path,
        model="base-model",
        context_window_tokens=1000,
        model_presets={
            "default": ModelPresetConfig(
                model="base-model",
                max_tokens=123,
                context_window_tokens=1000,
            ),
        },
    )


def _ctx(loop: AgentLoop, raw: str, args: str = "") -> CommandContext:
    msg = InboundMessage(channel="cli", sender_id="user", chat_id="direct", content=raw)
    return CommandContext(msg=msg, session=None, key=msg.session_key, raw=raw, args=args, loop=loop)


async def _init_git_repo(path: Path) -> None:
    import asyncio

    async def _git(args: list[str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=str(path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

    await _git(["init"])
    await _git(["config", "user.email", "test@example.com"])
    await _git(["config", "user.name", "Test User"])


@pytest.mark.asyncio
async def test_read_command_shows_usage_without_args(tmp_path: Path) -> None:
    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read"))
    assert out is not None
    assert "Usage" in out.content
    assert out.metadata == {"render_as": "text"}


@pytest.mark.asyncio
async def test_read_command_requires_git_repository(tmp_path: Path) -> None:
    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read README.md", args="README.md"))
    assert out is not None
    assert "Not inside a Git repository" in out.content


@pytest.mark.asyncio
async def test_read_command_returns_single_match_content(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# Hello\n\nWorld", encoding="utf-8")

    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read README.md", args="README.md"))

    assert out is not None
    assert out.content == "# Hello\n\nWorld"
    assert out.metadata == {"render_as": "text"}


@pytest.mark.asyncio
async def test_read_command_finds_file_without_md_suffix(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)
    (tmp_path / "notes.md").write_text("Some notes", encoding="utf-8")

    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read notes", args="notes"))

    assert out is not None
    assert out.content == "Some notes"


@pytest.mark.asyncio
async def test_read_command_lists_multiple_matches(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("root", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("docs", encoding="utf-8")

    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read README.md", args="README.md"))

    assert out is not None
    assert "Multiple markdown files match" in out.content
    assert "README.md" in out.content
    assert "docs/README.md" in out.content


@pytest.mark.asyncio
async def test_read_command_supports_relative_path(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("Guide content", encoding="utf-8")

    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read docs/guide.md", args="docs/guide.md"))

    assert out is not None
    assert out.content == "Guide content"


@pytest.mark.asyncio
async def test_read_command_rejects_path_outside_workspace(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)
    other = tmp_path.parent / "outside.md"
    other.write_text("outside", encoding="utf-8")

    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read ../outside.md", args="../outside.md"))

    assert out is not None
    assert "Only files within the workspace" in out.content


@pytest.mark.asyncio
async def test_read_command_rejects_non_markdown_path(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read secret.txt", args="secret.txt"))

    assert out is not None
    assert "Only markdown" in out.content


@pytest.mark.asyncio
async def test_read_command_not_found(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)

    loop = _make_loop(tmp_path)
    out = await cmd_read(_ctx(loop, "/read missing.md", args="missing.md"))

    assert out is not None
    assert "No markdown file named" in out.content


def test_read_command_in_help_and_palette() -> None:
    palette = builtin_command_palette()
    assert any(
        item["command"] == "/read" and "file-name-or-relative-path.md" in item["arg_hint"]
        for item in palette
    )
    assert "/read <file-name-or-relative-path.md>" in build_help_text()


@pytest.mark.asyncio
async def test_read_command_registered_on_router(tmp_path: Path) -> None:
    await _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("routed", encoding="utf-8")

    router = CommandRouter()
    register_builtin_commands(router)
    loop = _make_loop(tmp_path)

    out = await router.dispatch(_ctx(loop, "/read README.md", args="README.md"))

    assert out is not None
    assert out.content == "routed"
