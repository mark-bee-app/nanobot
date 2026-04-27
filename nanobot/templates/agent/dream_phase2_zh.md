根据以下分析更新记忆文件。
- [FILE] 条目：将描述的内容添加到适当的文件中
- [FILE-REMOVE] 条目：从记忆文件中删除相应的内容
- [SKILL] 条目：使用 write_file 在 skills/<name>/SKILL.md 下创建一个新技能

## 文件路径（相对于工作区根目录）
- SOUL.md
- USER.md
- memory/MEMORY.md
- skills/<name>/SKILL.md（仅适用于 [SKILL] 条目）

不要猜测路径。

## 编辑规则
- 直接编辑 — 下面提供了文件内容，不需要使用 read_file
- 使用完全相同的文本作为 old_text，包括周围的空行以实现唯一匹配
- 将对同一文件的更改批量合并到一次 edit_file 调用中
- 对于删除：将部分标题 + 所有项目符号作为 old_text，new_text 为空
- 仅进行精确编辑 — 绝不要重写整个文件
- 如果没有要更新的内容，则停止，不调用任何工具

## 技能创建规则（适用于 [SKILL] 条目）
- 使用 write_file 创建 skills/<name>/SKILL.md
- 在写入之前，使用 read_file 读取 `{{ skill_creator_path }}` 作为格式参考（frontmatter 结构、命名规范、质量标准）
- **去重检查**：读取下面列出的现有技能，以验证新技能是否在功能上存在冗余。如果现有技能已经涵盖了相同的工作流程，则跳过创建。
- 包含带有 name 和 description 字段的 YAML frontmatter
- 保持 SKILL.md 在 2000 字以内 — 简洁且可操作
- 包含：何时使用、步骤、输出格式，以及至少一个示例
- 不要覆盖现有的技能 — 如果技能目录已经存在，则跳过
- 引用代理有权访问的特定工具（read_file、write_file、exec、web_search 等）
- 技能是指令集，而不是代码 — 不要包含实现代码

## 质量
- 每一行都必须具有独立的价值
- 在清晰的标题下使用简洁的项目符号
- 缩减（不是删除）时：保留基本事实，删除冗长的细节
- 如果不确定是否删除，请保留但添加“(verify currency)”
