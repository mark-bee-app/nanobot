"""Tests for the /git slash command."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.command.builtin import (
    build_help_text,
    builtin_command_palette,
    cmd_git,
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


async def _git(path: Path, args: list[str]) -> tuple[int, str, str]:
    import asyncio

    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return (
        proc.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


async def _init_git_repo(path: Path) -> None:
    await _git(path, ["init"])
    await _git(path, ["config", "user.email", "test@example.com"])
    await _git(path, ["config", "user.name", "Test User"])


async def _init_git_repo_with_remote(path: Path, tmp_path: Path) -> Path:
    """Init a repo with a local bare remote set as upstream."""

    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, ["init", "--bare"])

    await _git(path, ["init"])
    await _git(path, ["config", "user.email", "test@example.com"])
    await _git(path, ["config", "user.name", "Test User"])
    await _git(path, ["remote", "add", "origin", str(bare)])
    return bare


@pytest.mark.asyncio
async def test_git_command_requires_git_repository(tmp_path: Path) -> None:
    loop = _make_loop(tmp_path)
    out = await cmd_git(_ctx(loop, "/git"))
    assert out is not None
    assert "Not inside a Git repository" in out.content


@pytest.mark.asyncio
async def test_git_command_no_changes_pulls_and_pushes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    await _init_git_repo_with_remote(repo, tmp_path)
    (repo / "README.md").write_text("# repo", encoding="utf-8")
    await _git(repo, ["add", "-A"])
    await _git(repo, ["commit", "-m", "initial"])
    await _git(repo, ["push", "-u", "origin", "HEAD"])

    loop = _make_loop(repo)
    out = await cmd_git(_ctx(loop, "/git"))

    assert out is not None
    assert "No local changes to commit" in out.content
    assert "Pulled latest changes" in out.content
    assert "Pushed local commits" in out.content


@pytest.mark.asyncio
async def test_git_command_commits_local_changes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    await _init_git_repo_with_remote(repo, tmp_path)
    (repo / "README.md").write_text("# repo", encoding="utf-8")
    await _git(repo, ["add", "-A"])
    await _git(repo, ["commit", "-m", "initial"])
    await _git(repo, ["push", "-u", "origin", "HEAD"])

    (repo / "new.md").write_text("new content", encoding="utf-8")

    loop = _make_loop(repo)
    out = await cmd_git(_ctx(loop, "/git"))

    assert out is not None
    assert "Committed local changes" in out.content
    assert "chore: sync workspace at" in out.content
    assert "Pulled latest changes" in out.content
    assert "Pushed local commits" in out.content

    rc, stdout, _ = await _git(repo, ["status", "--porcelain"])
    assert rc == 0
    assert stdout.strip() == ""


@pytest.mark.asyncio
async def test_git_command_pulls_and_pushes_to_remote(tmp_path: Path) -> None:
    import asyncio

    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, ["init", "--bare"])

    clone = tmp_path / "clone"
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", str(bare), str(clone),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()

    await _git(clone, ["config", "user.email", "test@example.com"])
    await _git(clone, ["config", "user.name", "Test User"])
    (clone / "README.md").write_text("# repo", encoding="utf-8")
    await _git(clone, ["add", "-A"])
    await _git(clone, ["commit", "-m", "initial"])
    await _git(clone, ["push", "-u", "origin", "HEAD"])

    (clone / "local.md").write_text("local", encoding="utf-8")

    loop = _make_loop(clone)
    out = await cmd_git(_ctx(loop, "/git"))

    assert out is not None
    assert "Committed local changes" in out.content
    assert "Pulled latest changes" in out.content
    assert "Pushed local commits" in out.content

    rc, stdout, _ = await _git(bare, ["log", "--pretty=format:%s"])
    assert rc == 0
    assert "chore: sync workspace at" in stdout


def test_git_command_in_help_and_palette() -> None:
    palette = builtin_command_palette()
    assert any(item["command"] == "/git" for item in palette)
    assert "/git" in build_help_text()


@pytest.mark.asyncio
async def test_git_command_registered_on_router(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    await _init_git_repo_with_remote(repo, tmp_path)
    (repo / "README.md").write_text("# repo", encoding="utf-8")
    await _git(repo, ["add", "-A"])
    await _git(repo, ["commit", "-m", "initial"])
    await _git(repo, ["push", "-u", "origin", "HEAD"])

    router = CommandRouter()
    register_builtin_commands(router)
    loop = _make_loop(repo)

    out = await router.dispatch(_ctx(loop, "/git"))
    assert out is not None
    assert "No local changes to commit" in out.content
    assert "Pushed local commits" in out.content
