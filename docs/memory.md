# nanobot 中的记忆系统

nanobot 的记忆系统建立在一个简单的理念之上：记忆应该让人感觉是鲜活的，但绝不应该混乱。

好的记忆不应该只是一堆笔记。它是一种安静的注意力系统。它能注意到什么值得保留，放手那些不再需要被关注的事物，并将经历转化为平静、持久且有用的东西。

这就是 nanobot 记忆系统的形态。

## 设计理念

nanobot 并没有把记忆当作一个巨大的文件来处理。

它将记忆分层，因为不同类型的记忆需要使用不同的工具：

- `session.messages` 保存着正在进行的短期对话。
- `memory/history.jsonl` 是一份持续滚动的、压缩过的历史对话归档。
- `SOUL.md`、`USER.md` 和 `memory/MEMORY.md` 是持久化的知识文件。
- `GitStore` 负责记录这些持久化文件随时间的变化。

这种设计使得系统在当下保持轻量，同时随着时间推移能够不断反思和沉淀。

## 工作流

记忆在 nanobot 中的流转分为两个阶段。

### 阶段 1：整合器 (Consolidator)

当对话增长到足以对上下文窗口造成压力时，nanobot 并不会试图永久携带每一条旧消息。

相反，`Consolidator` 会选取最旧的一段安全对话切片进行总结，并将该摘要追加到 `memory/history.jsonl` 中。

这个文件具有以下特点：

- 只能追加 (append-only)
- 基于游标 (cursor-based)
- 优先为机器读取优化，其次才是人类查看

每一行都是一个 JSON 对象：

```json
{"cursor": 42, "timestamp": "2026-04-03 00:02", "content": "- 用户偏好深色模式\n- 决定使用 PostgreSQL"}
```

它并不是最终的记忆，而是塑造最终记忆的素材。

### 阶段 2：梦境 (Dream)

`Dream` 是一个更缓慢、更深思熟虑的记忆层。默认情况下，它按 cron 定时任务计划运行，也可以手动触发。

Dream 会读取：

- `memory/history.jsonl` 中的新条目
- 当前的 `SOUL.md`
- 当前的 `USER.md`
- 当前的 `memory/MEMORY.md`

然后它分两个阶段工作：

1. 它会研究什么是新的信息，什么是已经知道的信息。
2. 它对外科手术式地编辑长期记忆文件，而不是重写所有内容。它通过做出能保持记忆连贯性的最小、最真实的改动来实现。

这就是为什么 nanobot 的记忆不仅仅是简单的存档，它具有理解和解释的能力。

## 文件结构

```text
workspace/
├── SOUL.md              # 机器人的长期性格声音和沟通风格
├── USER.md              # 关于用户的稳定知识
└── memory/
    ├── MEMORY.md        # 项目事实、决策和持久的上下文
    ├── history.jsonl    # 只能追加的历史摘要
    ├── .cursor          # Consolidator 的写入游标
    ├── .dream_cursor    # Dream 的消费游标
    └── .git/            # 长期记忆文件的版本历史
```

这些文件扮演着不同的角色：

- `SOUL.md` 记住 nanobot 听起来应该是什么样的。
- `USER.md` 记住用户是谁以及他们的偏好。
- `MEMORY.md` 记住关于工作本身什么是保持真实的。
- `history.jsonl` 记住在到达当前状态的过程中发生了什么。

## 为什么使用 `history.jsonl`

旧的 `HISTORY.md` 格式虽然方便日常阅读，但作为运行基础来说太脆弱了。

`history.jsonl` 为 nanobot 带来了：

- 稳定的增量游标
- 更安全的机器解析
- 更容易进行批处理
- 更清晰的数据迁移和压缩
- 在原始历史记录和精心策划的知识之间建立了更好的边界

你仍然可以使用熟悉的工具来搜索它：

```bash
# grep
grep -i "keyword" memory/history.jsonl

# jq
cat memory/history.jsonl | jq -r 'select(.content | test("keyword"; "i")) | .content' | tail -20

# Python
python -c "import json; [print(json.loads(l).get('content','')) for l in open('memory/history.jsonl','r',encoding='utf-8') if l.strip() and 'keyword' in l.lower()][-20:]"
```

这种改变在技术层面和哲学层面上都有意义：

- `history.jsonl` 用于结构
- `SOUL.md`、`USER.md` 和 `MEMORY.md` 用于意义

## 命令

记忆并不是隐藏在幕后的。用户可以随时检查并引导它。

| 命令 | 作用 |
|---------|--------------|
| `/dream` | 立即运行 Dream |
| `/dream-log` | 显示最新一次的 Dream 记忆更改 |
| `/dream-log <sha>` | 显示某次特定的 Dream 更改 |
| `/dream-restore` | 列出最近的 Dream 记忆版本 |
| `/dream-restore <sha>` | 将记忆恢复到特定更改之前的状态 |

这些命令的存在是有原因的：自动记忆固然强大，但用户应该始终保留检查、理解和恢复它的权利。

## 版本化记忆

在 Dream 更改了长期记忆文件之后，nanobot 会使用 `GitStore` 记录下这次更改。

这赋予了记忆自身的历史：

- 你可以检查什么被改变了
- 你可以比较不同版本
- 你可以恢复到之前的状态

这将记忆从悄无声息的突变，转变为一个可审计的过程。

## 配置

Dream 的配置在 `agents.defaults.dream` 下：

```json
{
  "agents": {
    "defaults": {
      "dream": {
        "intervalH": 2,
        "modelOverride": null,
        "maxBatchSize": 20,
        "maxIterations": 10
      }
    }
  }
}
```

| 字段 | 含义 |
|-------|---------|
| `intervalH` | Dream 运行的频率，以小时为单位 |
| `modelOverride` | 可选的 Dream 专属模型覆盖设置 |
| `maxBatchSize` | Dream 每次运行处理多少条历史记录 |
| `maxIterations` | Dream 编辑阶段的工具调用预算上限 |

在实际应用中：

- `modelOverride: null` 意味着 Dream 使用与主代理相同的模型。只有当你希望 Dream 在不同的模型上运行时才设置它。
- `maxBatchSize` 控制 Dream 在一次运行中消费多少条新的 `history.jsonl` 记录。较大的批次追赶速度更快；较小的批次则更轻量、更稳定。
- `maxIterations` 限制了 Dream 在更新 `SOUL.md`、`USER.md` 和 `MEMORY.md` 时可以采取多少次读取/编辑步骤。这是一个安全预算，而不是质量分数。
- `intervalH` 是配置 Dream 的常规方式。在内部，它是作为一个 `every` 计划运行的，而不是一个 cron 表达式。

遗留说明：

- 较旧的基于源的配置可能仍然包含 `dream.cron`。nanobot 为了向后兼容继续支持它，但新配置应该使用 `intervalH`。
- 较旧的基于源的配置可能仍然包含 `dream.model`。nanobot 为了向后兼容继续支持它，但新配置应该使用 `modelOverride`。

## 实际意义

在日常使用中，这意味着：

- 对话可以保持快速响应，而无需携带无限的上下文
- 持久的事实会随着时间的推移变得越来越清晰，而不是越来越嘈杂
- 用户可以在需要时检查和恢复记忆

记忆不应该感觉像是一个垃圾场。它应该感觉像是一种延续性。

这正是这个设计所试图保护的。