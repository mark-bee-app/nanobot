## 🧠 内存系统

nanobot 使用分层内存系统，设计上即时轻量，长期持久。

- `memory/history.jsonl` 存储仅追加的总结历史
- `SOUL.md`、`USER.md` 和 `memory/MEMORY.md` 存储由 Dream 管理的长期知识
- `Dream` 定期运行，也可手动触发
- 内存变更可通过内置命令检查和恢复

完整设计详见 [docs/MEMORY.md](docs/MEMORY.md)。