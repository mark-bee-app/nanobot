# 安全策略

## 报告漏洞

如果您发现 nanobot 中存在安全漏洞，请通过以下方式报告：

1. **不要** 创建公开的 GitHub Issue
2. 在 GitHub 上创建私有安全公告或联系仓库维护者 (xubinrencs@gmail.com)
3. 包含以下信息：
   - 漏洞描述
   - 复现步骤
   - 潜在影响
   - 建议的修复方案（如有）

我们 aim 在 48 小时内响应安全报告。

## 安全最佳实践

### 1. API 密钥管理

**关键**：切勿将 API 密钥提交到版本控制。

```bash
# ✅ 正确：存储在配置文件中并设置受限权限
chmod 600 ~/.nanobot/config.json

# ❌ 错误：在代码中硬编码密钥或提交它们
```

**建议：**
- 将 API 密钥存储在 `~/.nanobot/config.json` 中，文件权限设置为 `0600`
- 考虑使用环境变量存储敏感密钥
- 生产环境部署使用操作系统密钥环/凭证管理器
- 定期轮换 API 密钥
- 开发和生产使用不同的 API 密钥

### 2. 频道访问控制

**重要**：生产环境务必配置 `allowFrom` 列表。

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["123456789", "987654321"]
    },
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1234567890"]
    }
  }
}
```

**安全说明：**
- 在 `v0.1.4.post3` 及更早版本中，空的 `allowFrom` 允许所有用户。自 `v0.1.4.post4` 起，空的 `allowFrom` 默认拒绝所有访问 — 设置为 `["*"]` 可显式允许所有人。
- 从 `@userinfobot` 获取您的 Telegram 用户 ID
- 使用带国家代码的完整电话号码用于 WhatsApp
- 定期审查访问日志以发现未授权访问尝试

### 3. Shell 命令执行

`exec` 工具可以执行 shell 命令。虽然危险的命令模式已被阻止，但您应该：

- ✅ **启用 bwrap 沙盒** (`"tools.exec.sandbox": "bwrap"`) 实现内核级隔离（仅限 Linux）
- ✅ 审查代理日志中的所有工具使用
- ✅ 了解代理正在运行的命令
- ✅ 使用具有有限权限的专用用户账户
- ✅ 切勿以 root 身份运行 nanobot
- ❌ 不要禁用安全检查
- ❌ 不要在包含敏感数据的系统上运行，除非经过仔细审查

**Exec 沙盒 (bwrap)：**

在 Linux 上，设置 `"tools.exec.sandbox": "bwrap"` 将使用 [bubblewrap](https://github.com/containers/bubblewrap) 沙盒包装每个 shell 命令。这使用 Linux 内核命名空间来限制进程可见内容：

- 工作区目录 → **读写**（代理正常工作）
- 媒体目录 → **只读**（可以读取上传的附件）
- 系统目录（`/usr`、`/bin`、`/lib`）→ **只读**（命令仍可工作）
- 配置文件和 API 密钥（`~/.nanobot/config.json`）→ **隐藏**（被 tmpfs 遮蔽）

需要安装 `bwrap` (`apt install bubblewrap`)。官方 Docker 镜像中已预装。**macOS 或 Windows 上不可用** — bubblewrap 依赖于 Linux 内核命名空间。

启用沙盒会自动为文件工具激活 `restrictToWorkspace`。

**被阻止的模式：**
- `rm -rf /` - 根文件系统删除
- 叉炸弹（fork bombs）
- 文件系统格式化（`mkfs.*`）
- 原始磁盘写入
- 其他破坏性操作

### 4. 文件系统访问

文件操作具有路径遍历保护，但：

- ✅ 启用 `restrictToWorkspace` 或 bwrap 沙盒以限制文件访问
- ✅ 使用专用用户账户运行 nanobot
- ✅ 使用文件系统权限保护敏感目录
- ✅ 定期审计日志中的文件操作
- ❌ 不要授予对敏感文件的无限制访问权限

### 5. 网络安全

**API 调用：**
- 默认情况下所有外部 API 调用使用 HTTPS
- 配置超时以防止请求挂起
- 如有需要，考虑使用防火墙限制出站连接

**WhatsApp 桥接：**
- 桥接绑定到 `127.0.0.1:3001`（仅限 localhost，无法从外部网络访问）
- 在配置中设置 `bridgeToken` 以启用 Python 和 Node.js 之间的共享密钥认证
- 保护 `~/.nanobot/whatsapp-auth` 中的认证数据（模式 0700）

### 6. 依赖安全

**关键**：保持依赖更新！

```bash
# 检查易受攻击的依赖
pip install pip-audit
pip-audit

# 更新到最新安全版本
pip install --upgrade nanobot-ai
```

对于 Node.js 依赖（WhatsApp 桥接）：
```bash
cd bridge
npm audit
npm audit fix
```

**重要说明：**
- 保持 `litellm` 更新到最新版本以获取安全修复
- 我们已更新 `ws` 到 `>=8.17.1` 以修复 DoS 漏洞
- 定期运行 `pip-audit` 或 `npm audit`
- 订阅 nanobot 及其依赖的安全公告

### 7. 生产环境部署

生产环境使用时：

1. **隔离环境**
   ```bash
   # 在容器或虚拟机中运行
   docker run --rm -it python:3.11
   pip install nanobot-ai
   ```

2. **使用专用用户**
   ```bash
   sudo useradd -m -s /bin/bash nanobot
   sudo -u nanobot nanobot gateway
   ```

3. **设置适当权限**
   ```bash
   chmod 700 ~/.nanobot
   chmod 600 ~/.nanobot/config.json
   chmod 700 ~/.nanobot/whatsapp-auth
   ```

4. **启用日志**
   ```bash
   # 配置日志监控
   tail -f ~/.nanobot/logs/nanobot.log
   ```

5. **使用速率限制**
   - 在 API 提供商处配置速率限制
   - 监控异常使用情况
   - 设置 LLM API 支出限制

6. **定期更新**
   ```bash
   # 每周检查更新
   pip install --upgrade nanobot-ai
   ```

### 8. 开发与生产

**开发环境：**
- 使用独立的 API 密钥
- 使用非敏感数据进行测试
- 启用详细日志
- 使用测试 Telegram 机器人

**生产环境：**
- 使用带有支出限制的专用 API 密钥
- 限制文件系统访问
- 启用审计日志
- 定期安全审查
- 监控异常活动

### 9. 数据隐私

- **日志可能包含敏感信息** - 妥善保管日志文件
- **LLM 提供商能看到您的提示** - 审查他们的隐私政策
- **聊天记录存储在本地** - 保护 `~/.nanobot` 目录
- **API 密钥以纯文本形式存储** - 生产环境使用操作系统密钥环

### 10. 事件响应

如果怀疑发生安全漏洞：

1. **立即撤销已泄露的 API 密钥**
2. **审查日志以发现未授权访问**
   ```bash
   grep "Access denied" ~/.nanobot/logs/nanobot.log
   ```
3. **检查意外的文件修改**
4. **轮换所有凭证**
5. **更新到最新版本**
6. **向维护者报告事件**

## 安全功能

### 内置安全控制

✅ **输入验证**
- 文件操作的路径遍历保护
- 危险命令模式检测
- HTTP 请求的输入长度限制

✅ **认证**
- 基于允许列表的访问控制 — 在 `v0.1.4.post3` 及更早版本中空的 `allowFrom` 允许所有；自 `v0.1.4.post4` 起拒绝所有（`["*"]` 显式允许所有）
- 失败认证尝试记录

✅ **资源保护**
- 命令执行超时（默认 60 秒）
- 输出截断（10KB 限制）
- HTTP 请求超时（10-30 秒）

✅ **安全通信**
- 所有外部 API 调用使用 HTTPS
- Telegram API 使用 TLS
- WhatsApp 桥接：仅限 localhost 绑定 + 可选令牌认证

## 已知限制

⚠️ **当前安全限制：**

1. **无速率限制** - 用户可以发送无限消息（根据需要自行添加）
2. **纯文本配置** - API 密钥以纯文本形式存储（生产环境使用密钥环）
3. **无会话管理** - 无自动会话过期
4. **有限的命令过滤** - 仅阻止明显的危险模式（在 Linux 上启用 bwrap 沙盒实现内核级隔离）
5. **无审计轨迹** - 有限的安全事件日志（根据需要增强）

## 安全检查清单

部署 nanobot 之前：

- [ ] API 密钥安全存储（不在代码中）
- [ ] 配置文件权限设置为 0600
- [ ] 为所有频道配置 `allowFrom` 列表
- [ ] 以非 root 用户运行
- [ ] Exec 沙盒已启用（`"tools.exec.sandbox": "bwrap"`）（Linux 部署）
- [ ] 文件系统权限已适当限制
- [ ] 依赖已更新到最新安全版本
- [ ] 日志已配置安全事件监控
- [ ] API 提供商已配置速率限制
- [ ] 备份和灾难恢复计划已就位
- [ ] 已审查自定义技能/工具的安全性

## 更新

**最后更新**：2026-04-05

如需获取最新安全更新和公告，请查看：
- GitHub 安全公告：https://github.com/HKUDS/nanobot/security/advisories
- 发布说明：https://github.com/HKUDS/nanobot/releases

## 许可证

详见 LICENSE 文件。
