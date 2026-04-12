## 🐳 Docker

> [!TIP]
> `-v ~/.nanobot:/root/.nanobot` 标志将本地配置目录挂载到容器，使配置和工作区在容器重启后持久保存。

### Docker Compose

```bash
docker compose run --rm nanobot-cli onboard   # 首次设置
vim ~/.nanobot/config.json                     # 添加 API 密钥
docker compose up -d nanobot-gateway           # 启动网关
```

```bash
docker compose run --rm nanobot-cli agent -m "Hello!"   # 运行 CLI
docker compose logs -f nanobot-gateway                   # 查看日志
docker compose down                                      # 停止
```

### Docker

```bash
# 构建镜像
docker build -t nanobot .

# 初始化配置（仅首次）
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot onboard

# 在主机上编辑配置以添加 API 密钥
vim ~/.nanobot/config.json

# 运行网关（连接已启用的渠道，如 Telegram/Discord/Mochat）
docker run -v ~/.nanobot:/root/.nanobot -p 18790:18790 nanobot gateway

# 或运行单个命令
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot agent -m "Hello!"
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot status
```

## 🐧 Linux 服务

将网关作为 systemd 用户服务运行，使其自动启动并在失败时重启。

**1. 查找 nanobot 二进制路径：**

```bash
which nanobot   # 例如 /home/user/.local/bin/nanobot
```

**2. 创建服务文件** 位于 `~/.config/systemd/user/nanobot-gateway.service`（如需替换 `ExecStart` 路径）：

```ini
[Unit]
Description=Nanobot Gateway
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/nanobot gateway
Restart=always
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=%h

[Install]
WantedBy=default.target
```

**3. 启用并启动：**

```bash
systemctl --user daemon-reload
systemctl --user enable --now nanobot-gateway
```

**常用操作：**

```bash
systemctl --user status nanobot-gateway        # 查看状态
systemctl --user restart nanobot-gateway       # 配置变更后重启
journalctl --user -u nanobot-gateway -f        # 查看日志
```

如果编辑 `.service` 文件本身，重启前需运行 `systemctl --user daemon-reload`。

> **注意：**用户服务仅在登录时运行。要在注销后保持网关运行，启用 lingering：
>
> ```bash
> loginctl enable-linger $USER
> ```