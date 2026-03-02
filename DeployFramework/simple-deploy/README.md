# GameGodEngine 简单开发部署方案

适用于 Linux 服务器的轻量级开发部署方案，使用 Docker Compose 一键启动。

## 特点

- ✅ **简单快速** - 一条命令启动所有服务
- ✅ **开发友好** - 代码热重载，修改即时生效
- ✅ **资源占用低** - 适合 2核4G 及以上配置的服务器
- ✅ **易于管理** - 提供便捷的管理脚本

## 环境要求

- Linux 服务器（Ubuntu 18.04+/CentOS 7+/Debian 10+）
- 2核 CPU / 4GB 内存 / 20GB 磁盘
- 开放端口：8000（HTTP）

## 快速开始（3步走）

### 方式一：一键安装（推荐）

在 Linux 服务器上执行：

```bash
# 1. 下载安装脚本
curl -fsSL https://raw.githubusercontent.com/your-repo/GameGodEngine/main/DeployFramework/simple-deploy/scripts/install.sh -o install.sh

# 2. 运行安装（需要 root 权限）
sudo bash install.sh

# 3. 配置环境变量
sudo nano /opt/gamegodengine/.env
# 填入你的 OpenAI API 密钥: OPENAI_API_KEY=sk-xxx

# 4. 启动服务
sudo gge start
```

### 方式二：手动部署

如果你已经安装了 Docker：

```bash
# 1. 克隆代码
git clone https://github.com/your-repo/GameGodEngine.git
cd GameGodEngine/DeployFramework/simple-deploy

# 2. 配置环境
cp .env.example .env
nano .env  # 填入 OPENAI_API_KEY

# 3. 启动服务
bash scripts/quick-start.sh
```

## 目录结构

```
simple-deploy/
├── docker-compose.yml          # Docker Compose 配置
├── .env.example                # 环境变量示例
├── docker/
│   └── Dockerfile.simple       # 简化版 Dockerfile
├── nginx/
│   └── nginx.simple.conf       # Nginx 配置
├── scripts/
│   ├── install.sh              # 一键安装脚本
│   └── quick-start.sh          # 快速启动脚本
└── README.md                   # 本文件
```

## 管理命令

### 使用 gge 命令（推荐）

如果使用了 `install.sh` 安装，可以使用 `gge` 命令管理：

```bash
sudo gge start      # 启动服务
sudo gge stop       # 停止服务
sudo gge restart    # 重启服务
sudo gge status     # 查看状态
sudo gge logs       # 查看日志
sudo gge shell      # 进入容器
sudo gge update     # 更新并重启
```

### 使用 Docker Compose 命令

```bash
cd /opt/gamegodengine  # 或你的项目目录

# 启动
docker compose up -d

# 停止
docker compose down

# 查看日志
docker compose logs -f

# 重启
docker compose restart

# 进入容器
docker compose exec gamegodengine /bin/sh

# 查看状态
docker compose ps
```

### 使用 Systemd（如果已安装）

```bash
# 启动
sudo systemctl start gamegodengine

# 停止
sudo systemctl stop gamegodengine

# 查看状态
sudo systemctl status gamegodengine

# 开机自启
sudo systemctl enable gamegodengine
```

## 访问服务

启动后，可以通过以下地址访问：

- **API 服务**: http://服务器IP:8000
- **API 文档 (Swagger)**: http://服务器IP:8000/docs
- **API 文档 (ReDoc)**: http://服务器IP:8000/redoc

## 配置说明

### 环境变量 (.env)

```bash
# 必需
OPENAI_API_KEY=sk-your-openai-api-key

# 可选
LOG_LEVEL=debug          # 日志级别: debug/info/warning/error
WORKERS=2                # Uvicorn worker 数量
```

### 端口修改

如果需要修改端口，编辑 `docker-compose.yml`：

```yaml
services:
  gamegodengine:
    ports:
      - "8080:8000"    # 将主机 8080 映射到容器 8000
```

## 开发工作流

### 1. 本地开发 → 服务器部署

```bash
# 本地修改代码后，推送到 GitHub
git add .
git commit -m "update"
git push origin main

# 在服务器上更新
ssh user@server
cd /opt/gamegodengine
sudo gge update
```

### 2. 直接在服务器上开发

```bash
# 进入服务器
ssh user@server

# 编辑代码
sudo nano /opt/gamegodengine/server/api.py

# 代码会自动热重载，无需重启服务
```

### 3. 查看日志调试

```bash
# 实时查看日志
sudo gge logs

# 查看最近 100 行
sudo gge logs --tail=100

# 查看特定服务的日志
docker compose logs -f gamegodengine
```

## 常见问题

### Q: 服务启动失败？

```bash
# 检查日志
sudo gge logs

# 常见原因：
# 1. 端口被占用 - 修改 docker-compose.yml 中的端口映射
# 2. 内存不足 - 增加服务器内存或减少 WORKERS
# 3. .env 配置错误 - 检查 OPENAI_API_KEY 是否设置
```

### Q: 如何更新代码？

```bash
# 方法 1: 使用 gge 命令
sudo gge update

# 方法 2: 手动更新
cd /opt/gamegodengine
git pull
sudo gge restart
```

### Q: 如何备份数据？

```bash
# 备份生成的项目
tar -czf projects-backup.tar.gz /opt/gamegodengine/projects/

# 恢复
tar -xzf projects-backup.tar.gz -C /
```

### Q: 如何完全卸载？

```bash
# 停止服务
sudo gge stop

# 删除容器和数据
sudo docker compose down -v

# 删除项目目录
sudo rm -rf /opt/gamegodengine

# 删除系统服务
sudo systemctl disable gamegodengine
sudo rm /etc/systemd/system/gamegodengine.service

# 删除管理脚本
sudo rm /usr/local/bin/gge
```

## 性能优化

### 低内存服务器（2G 内存）

编辑 `docker-compose.yml`：

```yaml
services:
  gamegodengine:
    deploy:
      resources:
        limits:
          memory: 1G
    environment:
      - WORKERS=1    # 减少 worker 数量
```

### 使用 Nginx（可选）

如果需要使用 Nginx：

```bash
# 启动时包含 nginx
docker compose --profile with-nginx up -d
```

## 安全建议

1. **防火墙配置**
   ```bash
   # 只开放必要端口
   sudo ufw allow 8000/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

2. **使用 HTTPS（生产环境）**
   - 使用 Nginx + Let's Encrypt
   - 或部署在反向代理后面

3. **定期更新**
   ```bash
   # 更新系统
   sudo apt update && sudo apt upgrade -y
   
   # 更新 Docker 镜像
   sudo docker compose pull
   sudo gge restart
   ```

## 技术支持

遇到问题？

1. 查看日志：`sudo gge logs`
2. 检查状态：`sudo gge status`
3. 重启服务：`sudo gge restart`

## 许可证

MIT License
