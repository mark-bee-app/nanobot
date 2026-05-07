# nanobot Skill 加载机制深入分析

## 1. 机制概述

nanobot 的 **Skill 加载机制** 主要承担系统能力扩充与引导大模型的工作。它的核心设计理念是：
- 区分**高频常用能力**与**低频外围能力**。
- 提供一套基于 Markdown + YAML Frontmatter 的简易文件格式 (`SKILL.md`)，并内置自动化解析和验证依赖的能力。
- 将技能注入到 System Prompt（系统提示词）中，让大模型能获知其自身所具备的能力，并能自主选择挂载合适的工具（如读文件工具 `ReadFileTool`）查阅其不熟悉的技能详情。

## 2. 源码位置及主要类

理解 Skill 机制主要关注以下两个核心文件：
1. **技能加载器**：`nanobot/agent/skills.py` (`SkillsLoader` 类)
2. **上下文构建器**：`nanobot/agent/context.py` (`ContextBuilder` 类)

### `SkillsLoader` (`nanobot/agent/skills.py`)
`SkillsLoader` 负责在文件系统层面上发现、解析并过滤技能。核心关注以下方法：
- `list_skills(filter_unavailable=True)`：遍历工作区 `skills/` 和系统默认内置技能目录 (`BUILTIN_SKILLS_DIR`)。它可以根据环境（`bins`, `env`）过滤掉当前设备无法运行的技能。
- `get_skill_metadata()`：解析 `SKILL.md` 顶部的 YAML Frontmatter，提取 `description`, `always` 标记等元数据。
- `get_always_skills()`：筛选出配置了 `always=true` 的技能列表。
- `build_skills_summary()`：构建其余技能（非 `always=true`）的纯文本清单，包含“技能名称、描述及所在文件路径”。

### `ContextBuilder` (`nanobot/agent/context.py`)
`ContextBuilder` 负责将各种上下文（包含技能）组合成供大语言模型消费的 `System Prompt`。
- `build_system_prompt()` 核心方法：
  - 先通过 `SkillsLoader.get_always_skills()` 找到必须内嵌的技能。
  - 使用 `load_skills_for_context()` 剥离其 YAML 头部（`_strip_frontmatter`），然后将纯 Markdown 内容全文拼接进提示词。
  - 调用 `build_skills_summary(exclude=set(always_skills))` 拿到剩余所有可用技能的清单，并使用 `agent/skills_section.md` 的模板格式化后拼接，从而让大模型“知道”还有哪些潜在技能可用。

## 3. 如何阅读这部分代码？

阅读 Skill 加载机制的源码时，推荐按照以下数据流向进行：

**Step 1：理解文件结构**
先随便打开一个内置技能文件（例如 `nanobot/skills/github/SKILL.md`）。你会看到它是 YAML + Markdown 的结构：
```markdown
---
description: Read and create GitHub PRs, issues and comments
metadata:
  nanobot:
    requires:
      bins: ["gh"]
---
### ...具体指引说明...
```

**Step 2：探索 `SkillsLoader` 如何解析这个文件**
来到 `nanobot/agent/skills.py`：
- 看 `_STRIP_SKILL_FRONTMATTER` 正则表达式是如何分离 YAML 和文本的。
- 跟踪 `get_always_skills()` 和 `build_skills_summary()`，注意它是如何利用 `_check_requirements()` 来判断 `gh` (GitHub CLI) 是否安装并决定该技能是否“available”的。

**Step 3：观察 Prompt 注入流程**
转到 `nanobot/agent/context.py` 中的 `build_system_prompt()`：
- 重点看这几行代码：
  ```python
  always_skills = self.skills.get_always_skills()
  if always_skills:
      always_content = self.skills.load_skills_for_context(always_skills)
      # 全文载入
      parts.append(f"# Active Skills\n\n{always_content}")

  skills_summary = self.skills.build_skills_summary(exclude=set(always_skills))
  if skills_summary:
      # 仅给个目录
      parts.append(render_template("agent/skills_section.md", skills_summary=skills_summary))
  ```

**Step 4：联系机制差异（参考之前整理的文档）**
结合之前整理的 `Heartbeat`、`Cron`、`Dream` 的异同分析，你可以发现在 `nanobot/agent/loop.py` (即 AgentLoop 的外层封装) 中，普通的交互（包括 Cron/Heartbeat Phase 2）都会常规调用 `ContextBuilder` 进行 Prompt 组装。而类似于 Dream 这样的特殊机制，它的 Prompt 组装逻辑则是自己手写的，因此并没有走上述 `ContextBuilder.build_system_prompt()` 这套“全文展开”和“依赖过滤”的复杂流程。

通过这四步，你就能完全掌握 nanobot 的 Skill 加载与分发逻辑了。