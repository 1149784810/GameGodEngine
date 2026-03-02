# GameGodEngine 集群部署方案 (Kubernetes)

适用于大规模生产环境的 Kubernetes 集群部署方案，支持自动扩缩容、高可用和监控。

## 特点

- 🚀 **自动扩缩容** - 基于 CPU/内存自动调整 Pod 数量 (3-20 副本)
- 🔄 **高可用** - Pod 反亲和性、PodDisruptionBudget 保障服务不中断
- 📊 **可观测** - 集成 Prometheus + Grafana 监控
- 🔒 **安全** - NetworkPolicy 限制 Pod 间通信
- 🌐 **WebSocket 优化** - 支持长连接和会话亲和性

## 环境要求

- Kubernetes 集群 (>= 1.28)
- kubectl + helm
- 至少 3 个 Worker 节点 (4核8G)
- 云厂商负载均衡器 (CLB/ALB/NLB)

## 目录结构

```
cluster-deploy/
├── k8s/                          # Kubernetes 配置文件
│   ├── 00-namespace.yaml         # 命名空间
│   ├── 01-configmap.yaml         # 应用配置
│   ├── 02-secrets.yaml           # 密钥配置
│   ├── 03-storage.yaml           # 存储配置
│   ├── 04-redis.yaml             # Redis 集群
│   ├── 05-postgres.yaml          # PostgreSQL 数据库
│   ├── 06-deployment.yaml        # 应用部署
│   ├── 07-hpa.yaml               # 自动扩缩容
│   ├── 08-service.yaml           # 服务配置
│   ├── 09-ingress.yaml           # Ingress 配置
│   ├── 10-pdb.yaml               # Pod 中断预算
│   ├── 11-networkpolicy.yaml     # 网络策略
│   └── kustomization.yaml        # Kustomize 配置
├── docker/
│   └── Dockerfile                # 生产镜像构建
├── scripts/
│   ├── deploy.sh                 # 部署脚本
│   └── setup-cluster.sh          # 集群初始化脚本
├── .github/workflows/
│   ├── deploy.yml                # CI/CD 部署工作流
│   └── pr-check.yml              # PR 检查工作流
└── docs/
    ├── README.md                 # 快速开始
    └── DEPLOYMENT.md             # 详细部署指南
```

## 快速开始

### 1. 集群初始化

```bash
# 在新集群上安装必要组件
./scripts/setup-cluster.sh all
```

这将安装：
- Ingress Nginx Controller
- cert-manager (自动 SSL 证书)
- Prometheus + Grafana (监控)
- Metrics Server (自动扩缩容依赖)

### 2. 配置密钥

```bash
cd k8s
vim 02-secrets.yaml
# 填入 OpenAI API 密钥和其他密钥
```

### 3. 部署应用

```bash
# 使用脚本部署
../scripts/deploy.sh deploy

# 或使用 Kustomize
kustomize build . | kubectl apply -f -
```

### 4. 验证部署

```bash
# 查看状态
../scripts/deploy.sh status

# 等待就绪
../scripts/deploy.sh wait
```

## 管理命令

### 使用 deploy.sh 脚本

```bash
./scripts/deploy.sh deploy      # 部署所有资源
./scripts/deploy.sh status      # 查看状态
./scripts/deploy.sh logs        # 查看日志
./scripts/deploy.sh update <tag> # 更新镜像
./scripts/deploy.sh delete      # 删除所有资源
```

### 使用 kubectl

```bash
# 查看 Pod
kubectl get pods -n gamegodengine

# 查看 HPA
kubectl get hpa -n gamegodengine

# 查看 Ingress
kubectl get ingress -n gamegodengine
```

## 配置说明

### 自动扩缩容 (HPA)

- **最小副本**: 3
- **最大副本**: 20
- **扩容阈值**: CPU > 70% 或 内存 > 80%
- **扩容速度**: 每分钟最多 4 个 Pod
- **缩容冷却**: 5 分钟

### 资源限制

| 组件 | 请求 CPU | 限制 CPU | 请求内存 | 限制内存 |
|------|---------|---------|---------|---------|
| API | 500m | 2000m | 512Mi | 2Gi |
| Redis | 250m | 1000m | 512Mi | 2Gi |
| PostgreSQL | 500m | 2000m | 1Gi | 4Gi |

## CI/CD 配置

### GitHub Actions Secrets

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `SLACK_WEBHOOK` (可选)

### 部署流程

1. 推送到 `main` 分支触发构建
2. 构建 Docker 镜像并推送到 GHCR
3. 运行安全扫描
4. 自动部署到 Staging
5. 手动批准后部署到 Production (金丝雀部署)

## 监控和日志

### Grafana

- URL: http://<grafana-ip>:3000
- 用户名: admin
- 密码: admin123

### 查看指标

```bash
kubectl top pods -n gamegodengine
kubectl top nodes
```

## 详细文档

- [详细部署指南](docs/DEPLOYMENT.md) - 分步部署说明
- [快速开始](docs/README.md) - 快速上手指南

## 与 simple-deploy 的区别

| 特性 | simple-deploy | cluster-deploy |
|------|--------------|----------------|
| 目标环境 | 开发/测试 | 生产 |
| 部署方式 | Docker Compose | Kubernetes |
| 自动扩缩容 | ❌ | ✅ |
| 高可用 | ❌ | ✅ |
| 资源要求 | 2核4G | 3节点 4核8G |
| 复杂度 | 低 | 高 |
| 适用场景 | 个人开发、小团队 | 大规模用户、企业 |

## 许可证

MIT License
