# nanobot 中的内存

> **注意：** 此设计目前是最新源代码版本中的实验性功能，计划在 `v0.1.5` 正式发布。

nanobot 的内存建立在一个简单的信念上：内存应该感觉有生命力，但不应该感觉混乱。

好的内存不是一堆笔记。它是一个安静的注意力系统。它注意到什么值得保留，放手不再需要关注的东西，把生活经历变成平静、持久、有用的东西。

这就是 nanobot 中内存的形态。

## 设计理念

nanobot 不会把内存当作一个巨大的文件。

它把内存分成多个层次，因为不同类型的记忆需要不同的工具：

- `session.messages` 保存活跃的短期对话。
- `memory/history.jsonl` 是压缩后的过去对话的归档。
- `SOUL.md`、`USER.md` 和 `memory/MEMORY.md` 是持久化的知识文件。
- `GitStore` 记录这些持久化文件如何随时间变化。

这让系统在当下保持轻盈，但在时间中保持反思。

## 流程

内存在 nanobot 中分两个阶段流转。

### 阶段 1：Consolidator（合并器）

当对话增长到足以对上下文窗口造成压力时，nanobot 不会试图永远保留每条旧消息。

相反，`Consolidator` 会总结对话中最旧的安全切片，并将该摘要追加到 `memory/history.jsonl`。

这个文件是：

- 只追加的
- 基于游标的
- 优先为机器消费优化，其次才是人工检查

每一行是一个 JSON 对象：

```json
{"cursor": 42, "timestamp": "2026-04-03 00:02", "content": "- 用户偏好深色模式\n- 决定使用 PostgreSQL"}
```

它不是最终的内存。它是塑造最终内存的原材料。

### 阶段 2：Dream（梦境）

`Dream` 是更慢、更有思想的层次。它默认按 cron 调度运行，也可以手动触发。

Dream 读取：

- `memory/history.jsonl` 中的新条目
- 当前的 `SOUL.md`
- 当前的 `USER.md`
- 当前的 `memory/MEMORY.md`

然后它分两个阶段工作：

1. 它研究什么是新的，以及什么是已知的。
2. 它精确地编辑长期文件 — 不是重写所有内容，而是做出最小的诚实更改，保持内存的一致性。

这就是为什么 nanobot 的内存不仅仅是归档。它是解释性的。

## 文件结构

```
workspace/
├── SOUL.md              # 代理的长期声音和沟通风格
├── USER.md              # 关于用户的稳定知识
└── memory/
    ├── MEMORY.md        # 项目事实、决策和持久上下文
    ├── history.jsonl    # 只追加的历史摘要
    ├── .cursor          # Consolidator 写入游标
    ├── .dream_cursor    # Dream 消费游标
    └── .git/            # 长期内存文件的版本历史
```

这些文件扮演不同的角色：

- `SOUL.md` 记住 nanobot 应该如何表达。
- `USER.md` 记住用户是谁以及他们的偏好。
- `MEMORY.md` 记住关于工作本身的持久事实。
- `history.jsonl` 记住达成目标的过程中的经历。

## 为什么是 `history.jsonl`

旧的 `HISTORY.md` 格式便于随意阅读，但作为操作基础太过脆弱。

`history.jsonl` 给 nanobot 提供：

- 稳定的增量游标
- 更安全的机器解析
- 更容易的批处理
- 更清晰的迁移和压缩
- 原始历史和精选知识之间更好的边界

你仍然可以用熟悉的工具搜索它：

```bash
# grep
grep -i "关键词" memory/history.jsonl

# jq
cat memory/history.jsonl | jq -r 'select(.content | test("关键词"; "i")) | .content' | tail -20

# Python
python -c "import json; [print(json.loads(l).get('content','')) for l in open('memory/history.jsonl','r',encoding='utf-8') if l.strip() and '关键词' in l.lower()][-20:]"
```

这种差异既是技术上的，也是哲学上的：

- `history.jsonl` 是为了结构
- `SOUL.md`、`USER.md` 和 `MEMORY.md` 是为了意义

## 命令

内存不是隐藏在幕后的。用户可以检查和引导它。

| 命令 | 作用 |
|------|------|
| `/dream` | 立即运行 Dream |
| `/dream-log` | 显示最新的 Dream 内存变更 |
| `/dream-log <sha>` | 显示特定的 Dream 变更 |
| `/dream-restore` | 列出最近的 Dream 内存版本 |
| `/dream-restore <sha>` | 将内存恢复到特定变更之前的状态 |

这些命令的存在是有原因的：自动内存很强大，但用户应该始终保留检查、理解和恢复它的权利。

## 版本化内存

在 Dream 更改长期内存文件后，nanobot 可以用 `GitStore` 记录该更改。

这给内存一个自己的历史：

- 你可以检查什么改变了
- 你可以比较版本
- 你可以恢复到之前的状态

这把内存从无声的突变变成了可审计的过程。

## 配置

Dream 在 `agents.defaults.dream` 下配置：

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
|------|------|
| `intervalH` | Dream 运行频率，单位为小时 |
| `modelOverride` | 可选的 Dream 专用模型覆盖 |
| `maxBatchSize` | Dream 每次运行处理的 history 条目数 |
| `maxIterations` | Dream 编辑阶段的工具预算 |

实际意义上：

- `modelOverride: null` 表示 Dream 使用与主代理相同的模型。仅当你想让 Dream 在不同的模型上运行时才设置它。
- `maxBatchSize` 控制 Dream 一次运行中消费多少新的 `history.jsonl` 条目。更大的批次追赶更快；更小的批次更轻量、更稳定。
- `maxIterations` 限制 Dream 在更新 `SOUL.md`、`USER.md` 和 `MEMORY.md` 时可以执行多少次读取/编辑步骤。这是一个安全预算，不是质量评分。
- `intervalH` 是配置 Dream 的常规方式。内部它作为 `every` 调度运行，而不是 cron 表达式。

遗留说明：

- 较旧的基于源的配置可能仍包含 `dream.cron`。nanobot 继续支持它以保持向后兼容，但新配置应该使用 `intervalH`。
- 较旧的基于源的配置可能仍包含 `dream.model`。nanobot 继续支持它以保持向后兼容，但新配置应该使用 `modelOverride`。

## 实践

在日常使用中，这意味着：

- 对话可以保持快速，而无需携带无限上下文
- 持久事实可以随时间变得更清晰，而不是更嘈杂
- 用户可以在需要时检查和恢复内存

内存不应该感觉像垃圾堆。它应该感觉像连续性。

这就是这个设计试图保护的东西。