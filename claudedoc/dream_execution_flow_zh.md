# Nanobot Dream 机制执行流程

在 `@nanobot/agent/memory.py` 中，`Dream` 机制被设计为一个**两阶段记忆处理器（Two-phase memory processor）**。它的核心职责是以后台定时（或 cron）的方式，将用户的短期对话历史（`history.jsonl`）分析提炼，并将其转化为长期的事实、规则或技能，持久化保存到工作区文件中（如 `MEMORY.md`、`SOUL.md`、`USER.md` 和 `skills/`）。

以下是 `Dream` 机制的完整执行流程细节：

## 1. 启动与数据准备 (Preparation)

* **获取未处理的历史：** 读取游标文件（`.dream_cursor`），从 `history.jsonl` 中拉取尚未被 Dream 处理的对话记录。每次处理存在最大批次限制（`max_batch_size`，默认 20 条）。如果没有新记录，则直接跳过执行。
* **收集当前状态：** 读取工作区核心记忆文件的当前内容，包括 `MEMORY.md`、`SOUL.md` 和 `USER.md`。
* **行老化标记 (Line Age Annotation)：** 针对 `MEMORY.md` 文件，Dream 会调用底层的 Git Blame 获取每一行的最后修改时间。如果某行距今超过了 14 天（`_STALE_THRESHOLD_DAYS = 14`），系统会在该行末尾自动追加一个老化标签（例如 `← 30d`）。这个机制用于向 LLM 提示哪些记忆可能已经过时，需要被清理或更新（如果 Git 统计报错或行数不匹配，系统会安全回退，直接传递原文）。

## 2. 第一阶段：历史分析 (Phase 1)

* **纯文本推理：** 这是一个纯大语言模型（LLM）的调用，不涉及任何工具执行。
* **输入上下文：** 将整理好的“对话历史（History）”、“当前系统日期”以及带老化标记的“记忆文件内容”合并为 Prompt，搭配 `agent/dream_phase1_zh.md` 系统模板发送给 LLM。
* **输出产物：** LLM 的任务是阅读这些对话，并输出一份**分析摘要（Analysis Result）**。它会判断这批对话中是否有需要被记忆的新事实、用户偏好的改变、过时信息的淘汰，或者是可以提取为标准技能（Skill）的通用操作。

## 3. 第二阶段：增量执行 (Phase 2)

* **工具赋权：** 系统会启动一个带工具链的代理运行器（`AgentRunner`），并为其注册最小化的文件操作工具：
  * `ReadFileTool`: 允许读取工作区和内置技能目录。
  * `EditFileTool`: 允许修改工作区文件（这是核心，LLM 必须通过精准定位**增量修改**旧内容，而非全量重写）。
  * `WriteFileTool`: 被限制仅允许在 `skills/` 目录下写入，用于创建新技能。
* **上下文去重：** 系统会扫描当前已有的自定义技能和内置技能，提取它们的 `description` 列表（`_list_existing_skills`），附在 Prompt 里，防止 LLM 重复创建同名或同功能的技能。
* **执行修改：** 将第一阶段得出的“分析摘要”和“现有技能列表”通过 `agent/dream_phase2_zh.md` 模板交付给 `AgentRunner`。AgentRunner 会在最大迭代次数（`max_iterations`）内自主循环，调用工具完成对 `MEMORY.md`、`USER.md` 或新技能文件的精确编辑。

## 4. 收尾与状态持久化 (Post-Processing)

* **日志提取：** 收集 `AgentRunner` 执行期间所有成功（`status == "ok"`）的工具调用记录，生成变更日志（Changelog）。
* **推进游标（必须执行）：** 无论执行阶段成功、失败还是抛出异常，Dream 都一定会将 `.dream_cursor` 推进到当前批次最后一条消息的 ID。这是一种**防死锁机制**，避免因为某条引起解析错误的对话导致 Dream 陷入无限循环的重试。
* **历史瘦身：** 触发 `compact_history()` 检查并丢弃超限的最老 jsonl 历史条目。
* **自动化 Git 提交：** 如果第二阶段产生了实质性的文件变更，并且项目启用了 Git（`GitStore.is_initialized()`），系统会触发一次 Auto-commit，将所有变更通过 Git 保存。Commit message 会包含修改的数量和第一阶段的分析摘要，以便后续追溯。

## 总结

`Dream` 机制精妙地解决了长上下文维护的问题：通过 **Phase 1 的全盘分析** 提炼核心意图，再通过 **Phase 2 的 Tool 使用** 实施打点编辑（Edit）。这种设计避免了传统“每次全量重写 Markdown 文件”容易导致的信息丢失和 Token 浪费，同时利用“游标管理”和“行级 Git 时效感知”保障了记忆库的健康迭代。
