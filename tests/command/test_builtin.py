"""Tests for built-in slash commands."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nanobot.command.builtin import cmd_read


def _make_context(tmp_path: Path, args: str = ""):
    """Build a minimal CommandContext for cmd_read tests."""
    msg = MagicMock()
    msg.channel = "test"
    msg.chat_id = "123"
    msg.metadata = {}

    loop = MagicMock()
    loop.workspace = tmp_path

    ctx = MagicMock()
    ctx.msg = msg
    ctx.loop = loop
    ctx.args = args
    ctx.raw = f"/read {args}".strip()
    return ctx


@pytest.mark.asyncio
async def test_read_empty_arg(tmp_path):
    ctx = _make_context(tmp_path, args="")
    result = await cmd_read(ctx)
    assert result.content.startswith("Usage:")
    assert result.channel == "test"


@pytest.mark.asyncio
async def test_read_no_match(tmp_path):
    ctx = _make_context(tmp_path, args="missing")
    result = await cmd_read(ctx)
    assert "No matching .md file found" in result.content


@pytest.mark.asyncio
async def test_read_single_match(tmp_path):
    file_path = tmp_path / "note.md"
    file_path.write_text("Hello, world!")
    ctx = _make_context(tmp_path, args="note")
    result = await cmd_read(ctx)
    assert "Hello, world!" in result.content
    assert str(file_path.resolve()) in result.content


@pytest.mark.asyncio
async def test_read_multiple_matches(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "note.md").write_text("A")
    (tmp_path / "b" / "note.md").write_text("B")

    ctx = _make_context(tmp_path, args="note")
    result = await cmd_read(ctx)
    assert "Multiple .md files match" in result.content
    assert str((tmp_path / "a" / "note.md").resolve()) in result.content
    assert str((tmp_path / "b" / "note.md").resolve()) in result.content


@pytest.mark.asyncio
async def test_read_absolute_path(tmp_path):
    file_path = tmp_path / "doc.md"
    file_path.write_text("absolute content")
    ctx = _make_context(tmp_path, args=str(file_path))
    result = await cmd_read(ctx)
    assert "absolute content" in result.content


@pytest.mark.asyncio
async def test_read_absolute_path_outside_workspace(tmp_path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("outside")
    ctx = _make_context(tmp_path, args=str(outside))
    result = await cmd_read(ctx)
    assert "must be inside the workspace" in result.content


@pytest.mark.asyncio
async def test_read_non_md_rejected(tmp_path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("text file")
    ctx = _make_context(tmp_path, args=str(file_path))
    result = await cmd_read(ctx)
    assert "only .md files" in result.content.lower()


@pytest.mark.asyncio
async def test_read_oversized_file(tmp_path):
    file_path = tmp_path / "huge.md"
    file_path.write_bytes(b"x" * (100 * 1024 + 1))
    ctx = _make_context(tmp_path, args="huge")
    result = await cmd_read(ctx)
    assert "too large" in result.content.lower()
