# 贡献 nanobot

感谢你的到来。

nanobot 的构建基于一个简单的信念：好的工具应该让人感到平静、清晰和人性化。
我们非常重视有用的功能，但我们也相信能够以更少的投入获得更多：
解决方案应该强大而不笨重，雄心勃勃而不无谓地复杂。

本指南不仅关乎如何提交 PR，也关乎我们如何一起构建软件：
带着细心、清晰和对下一位阅读代码的人的尊重。

## 维护者

| 维护者 | 职责 |
|--------|------|
| [@re-bin](https://github.com/re-bin) | 项目负责人，`main` 分支 |
| [@chengyongru](https://github.com/chengyongru) | `nightly` 分支，实验性功能 |

## 分支策略

我们使用双分支模型来平衡稳定性和探索性：

| 分支 | 用途 | 稳定性 |
|------|------|--------|
| `main` | 稳定版本 | 生产就绪 |
| `nightly` | 实验性功能 | 可能存在 bug 或破坏性变更 |

### 我应该以哪个分支为目标？

**如果你的 PR 包含以下内容，请以 `nightly` 为目标：**

- 新功能或新特性
- 可能影响现有行为的重构
- API 或配置的变更

**如果你的 PR 包含以下内容，请以 `main` 为目标：**

- 没有行为变更的 bug 修复
- 文档改进
- 不影响功能的小幅调整

**如有疑虑，请以 `nightly` 为目标。** 将一个稳定的想法从 `nightly` 移到 `main`，
比在稳定分支上撤销一个有风险的变更要容易得多。

### nightly 如何合并到 main？

我们不会合并整个 `nightly` 分支。相反，稳定的功能会通过 **cherry-pick** 从 `nightly` 挑选到各个 targeting `main` 的 PR 中：

```
nightly  ──┬── 功能 A（稳定）──► PR ──► main
           ├── 功能 B（测试中）
           └── 功能 C（稳定）──► PR ──► main
```

这大约**每周**发生一次，但具体时间取决于功能何时足够稳定。

### 快速总结

| 你的变更 | 目标分支 |
|----------|----------|
| 新功能 | `nightly` |
| Bug 修复 | `main` |
| 文档 | `main` |
| 重构 | `nightly` |
| 不确定 | `nightly` |

## 开发环境设置

保持简单可靠。目标是让你能够快速进入代码：

```bash
# 克隆仓库
git clone https://github.com/HKUDS/nanobot.git
cd nanobot

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check nanobot/

# 代码格式化
ruff format nanobot/
```

## 代码风格

我们关心的不仅仅是通过 lint。我们希望 nanobot 保持小巧、平静和可读。

在贡献时，请努力让你的代码呈现：

- 简单：优先选择能解决实际问题的最小变更
- 清晰：为下一位读者优化，而不是追求巧妙
- 解耦：保持边界清晰，避免不必要的新抽象
- 诚实：不要隐藏复杂性，但也不要制造额外的复杂性
- 持久：选择易于维护、测试和扩展的解决方案

在实践中：

- 行长度：100 个字符（`ruff`）
- 目标：Python 3.11+
- Lint：`ruff` 使用规则 E, F, I, N, W（忽略 E501）
- 异步：全程使用 `asyncio`；pytest 使用 `asyncio_mode = "auto"`
- 优先选择可读的代码，而不是魔法般的代码
- 优先选择专注的补丁，而不是广泛的重写
- 如果引入新的抽象，它应该明显降低复杂性，而不是转移复杂性

## 有问题？

如果你有问题、想法或半成品的见解，欢迎你来到这里。

请随时开启 [issue](https://github.com/HKUDS/nanobot/issues)，加入社区，或直接联系：

- [Discord](https://discord.gg/MnCvHqpUGB)
- [飞书/微信](./COMMUNICATION.md)
- 邮箱：Xubin Ren (@Re-bin) — <xubinrencs@gmail.com>

感谢你在 nanobot 上花费的时间和关心。我们希望有更多人参与这个社区，我们真诚欢迎各种规模的贡献。
