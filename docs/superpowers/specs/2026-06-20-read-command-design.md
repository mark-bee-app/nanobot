# /read Slash Command Design

## Date

2026-06-20

## Context

nanobot already has a built-in slash command system (`nanobot.command`). Commands are registered in `nanobot/command/builtin.py` and routed through `nanobot/command/router.py`. The user wants a new command that reads a Markdown file from the workspace without invoking the LLM.

## Goal

Add a `/read <file>` slash command that:

1. Accepts a Markdown file name or an absolute path.
2. Returns the file content if exactly one matching `.md` file is found.
3. Returns a list of absolute paths if multiple matching files exist.
4. Returns a clear hint if no matching file exists.
5. Does not invoke the LLM.

## Design Decisions

- **Command name**: `/read`
- **Search scope**: Recursively search the configured workspace (`loop.workspace`).
- **File type**: Only `.md` files are considered.
- **Case sensitivity**: Case-insensitive name matching.
- **Absolute path support**: If the argument is an absolute path pointing to a `.md` file inside the workspace, read it directly.
- **Security**: Only files within the configured workspace are accessible; paths outside the workspace are rejected.
- **Multiple matches**: Return a numbered list of absolute paths; user can rerun with the desired path.
- **Size limit**: Refuse to send files larger than a configurable threshold (default 100 KB) to avoid flooding chat.
- **Error handling**: All errors return a text message, never crash the command.

## Data Flow

1. User sends `/read <arg>`.
2. If `<arg>` is empty → return usage hint.
3. If `<arg>` is an absolute path and exists and ends with `.md` → read and return its content.
4. Otherwise, recursively search `loop.workspace` for files whose name equals `<arg>` (case-insensitive) and end with `.md`.
5. If no matches → return "No matching .md file found."
6. If exactly one match → return its absolute path and content.
7. If multiple matches → return a numbered list of absolute paths and ask the user to rerun with the desired path.

## Architecture

- Add a new command handler `cmd_read` in `nanobot/command/builtin.py`.
- Register it in `register_builtin_commands` as both `exact("/read")` and `prefix("/read ", cmd_read)`.
- Add `BuiltinCommandSpec` metadata for the command palette.
- Reuse `OutboundMessage` with `render_as: text`.

## Error Scenarios

- Empty argument
- No matching `.md` file
- Multiple matching files
- File path is not a `.md` file
- File is unreadable due to permissions
- File exceeds the size threshold

## Testing

Add pytest cases in `tests/command/test_builtin.py` covering:

- Empty argument
- No match
- Single match
- Multiple matches
- Absolute path read
- Non-`.md` rejection
- Oversized file rejection

## Open Questions

None at this time.
