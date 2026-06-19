# /read Slash Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/read <file>` slash command that reads a single Markdown file from the workspace, lists multiple matches, or returns a friendly error, all without invoking the LLM.

**Architecture:** Reuse the existing `CommandRouter` in `nanobot/command/builtin.py`. Add a new handler `cmd_read`, register it for exact `/read` and prefix `/read `, add its metadata to `BUILTIN_COMMAND_SPECS`, and add pytest coverage in `tests/command/test_builtin.py`.

**Tech Stack:** Python 3.11+, `pathlib`, `pytest`, `unittest.mock`.

## Global Constraints

- Only `.md` files are considered.
- Search is recursive within `loop.workspace`.
- Matching is case-insensitive on the file name.
- Absolute-path arguments are allowed only if they point inside the workspace.
- Files larger than 100 KB are rejected.
- All failures return a text `OutboundMessage`; never crash.

---

## File Structure

- **Modify:** `nanobot/command/builtin.py`
  - Add `cmd_read` handler and helper functions.
  - Add `/read` entry to `BUILTIN_COMMAND_SPECS`.
  - Register `/read` and `/read ` in `register_builtin_commands`.
- **Create:** `tests/command/test_builtin.py`
  - Cover empty arg, no match, single match, multiple matches, absolute path, non-`.md` rejection, and oversized file rejection.

---

## Task 1: Implement the `/read` command handler

**Files:**
- Modify: `nanobot/command/builtin.py`
- Test: `tests/command/test_builtin.py` (failing tests written first in Task 2)

**Interfaces:**
- Consumes: `CommandContext` with `ctx.loop.workspace` (a `pathlib.Path`) and `ctx.args`.
- Produces: `OutboundMessage` from `cmd_read(ctx: CommandContext) -> OutboundMessage`.

- [ ] **Step 1: Add imports and constants near the top of `nanobot/command/builtin.py`**

```python
from pathlib import Path
```

Add constant after imports:

```python
_READ_MAX_SIZE_BYTES = 100 * 1024  # 100 KB
```

- [ ] **Step 2: Add helper functions above `cmd_read`**

```python
def _is_within_workspace(path: Path, workspace: Path) -> bool:
    """Return True if *path* is inside *workspace*.

    Uses Path.is_relative_to (Python 3.9+). Both paths are resolved first.
    """
    try:
        return path.resolve().is_relative_to(workspace.resolve())
    except (OSError, ValueError):
        return False


def _find_md_files(workspace: Path, name: str) -> list[Path]:
    """Return .md files under *workspace* matching *name* case-insensitively.

    Matches against the full file name (e.g. "note.md") or the stem (e.g. "note").
    """
    target = name.lower()
    matches: list[Path] = []
    if not workspace.exists():
        return matches
    for path in workspace.rglob("*.md"):
        if path.name.lower() == target or path.stem.lower() == target:
            matches.append(path)
    return matches


def _format_read_result(path: Path, content: str) -> str:
    lines = [f"**{path.resolve()}**", "", content]
    return "\n".join(lines)


def _format_multiple_matches(matches: list[Path]) -> str:
    lines = ["Multiple .md files match that name:", ""]
    for idx, path in enumerate(matches, start=1):
        lines.append(f"{idx}. `{path.resolve()}`")
    lines.extend(["", "Run `/read <absolute-path>` to read the one you want."])
    return "\n".join(lines)
```

- [ ] **Step 3: Implement `cmd_read`**

Insert before `build_help_text` (or near other command handlers):

```python
async def cmd_read(ctx: CommandContext) -> OutboundMessage:
    """Read a Markdown file from the workspace.

    Usage:
        /read <file-name>       — search workspace for a .md file by name
        /read <absolute-path>   — read the specified .md file directly
    """
    msg = ctx.msg
    loop = ctx.loop
    metadata = {**dict(msg.metadata or {}), "render_as": "text"}
    arg = ctx.args.strip()

    if not arg:
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content="Usage:\n- `/read <file-name>`\n- `/read <absolute-path>`",
            metadata=metadata,
        )

    workspace = Path(loop.workspace).expanduser().resolve(strict=False)

    # Absolute path branch
    if arg.startswith("/"):
        path = Path(arg).expanduser().resolve(strict=False)
        if not _is_within_workspace(path, workspace):
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="Error: absolute path must be inside the workspace.",
                metadata=metadata,
            )
        if not path.suffix.lower() == ".md":
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="Error: only .md files can be read.",
                metadata=metadata,
            )
        if not path.is_file():
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=f"Error: file not found: `{path}`",
                metadata=metadata,
            )
        if path.stat().st_size > _READ_MAX_SIZE_BYTES:
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=f"Error: file `{path}` is too large (>100 KB).",
                metadata=metadata,
            )
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=f"Error: could not read `{path}`: {exc}",
                metadata=metadata,
            )
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=_format_read_result(path, content),
            metadata=metadata,
        )

    # Search-by-name branch
    matches = _find_md_files(workspace, arg)
    if not matches:
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=f"No matching .md file found for `{arg}` in workspace.",
            metadata=metadata,
        )

    if len(matches) > 1:
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=_format_multiple_matches(matches),
            metadata=metadata,
        )

    path = matches[0]
    if path.stat().st_size > _READ_MAX_SIZE_BYTES:
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=f"Error: file `{path}` is too large (>100 KB).",
            metadata=metadata,
        )
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=f"Error: could not read `{path}`: {exc}",
            metadata=metadata,
        )
    return OutboundMessage(
        channel=msg.channel,
        chat_id=msg.chat_id,
        content=_format_read_result(path, content),
        metadata=metadata,
    )
```

- [ ] **Step 4: Add metadata entry to `BUILTIN_COMMAND_SPECS`**

Append to the tuple:

```python
    BuiltinCommandSpec(
        "/read",
        "Read Markdown file",
        "Read a Markdown file from the workspace by name or absolute path.",
        "file-text",
        "<file-name>|<absolute-path>",
    ),
```

- [ ] **Step 5: Register the command in `register_builtin_commands`**

Add at the end of `register_builtin_commands`:

```python
    router.exact("/read", cmd_read)
    router.prefix("/read ", cmd_read)
```

- [ ] **Step 6: Run ruff and existing tests**

```bash
ruff check nanobot/command/builtin.py
pytest tests/command/test_builtin.py -v  # will fail until tests are added, but ensures import
```

Expected: ruff clean; tests fail because `tests/command/test_builtin.py` does not exist yet.

- [ ] **Step 7: Commit**

```bash
git add nanobot/command/builtin.py
git commit -m "feat(command): add /read slash command for Markdown files"
```

---

## Task 2: Add tests for `/read`

**Files:**
- Create: `tests/command/test_builtin.py`

**Interfaces:**
- Consumes: `cmd_read` from `nanobot.command.builtin`.
- Produces: Passing pytest cases.

- [ ] **Step 1: Create `tests/command/test_builtin.py` with the following content**

```python
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
```

- [ ] **Step 2: Run the tests**

```bash
pytest tests/command/test_builtin.py -v
```

Expected: 8 passed.

- [ ] **Step 3: Run the broader test suite**

```bash
pytest tests/ -q
```

Expected: All existing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add tests/command/test_builtin.py
git commit -m "test(command): add /read slash command tests"
```

---

## Task 3: Verify command palette and help text

**Files:**
- Modify: none (verification only)

- [ ] **Step 1: Check the generated help text includes `/read`**

Run a quick Python one-liner:

```bash
python - <<'PY'
from nanobot.command.builtin import build_help_text, builtin_command_palette
assert "/read" in build_help_text()
specs = builtin_command_palette()
assert any(s["command"] == "/read" for s in specs)
print("Help text and palette OK")
PY
```

Expected output:

```
Help text and palette OK
```

- [ ] **Step 2: Commit (if any docs updates are needed)**

No additional commit required unless docs change.

---

## Self-Review

- **Spec coverage:**
  - Command name `/read` → Task 1 Step 4.
  - Recursive workspace search for `.md` → Task 1 Step 2 `_find_md_files`.
  - Case-insensitive matching → Task 1 Step 2.
  - Absolute path support within workspace → Task 1 Step 3.
  - Multiple matches list → Task 1 Step 3.
  - Size limit (100 KB) → Task 1 Step 3.
  - Error handling → Task 1 Step 3 and Task 2.
  - Tests → Task 2.

- **Placeholder scan:** No TBD/TODO/fill-in-details present.
- **Type consistency:** `cmd_read(ctx: CommandContext) -> OutboundMessage` matches other command handlers. `loop.workspace` is treated as `Path` consistent with `cmd_git`.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-20-read-command.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach would you like?
