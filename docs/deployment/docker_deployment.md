# 🐳 Docker部署指南

本指南详细介绍如何使用Docker容器化部署GIS空间关联分析系统，包括单容器部署、多容器编排和生产环境部署。

## 📋 目录

- [Docker基础](#docker基础)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [单容器部署](#单容器部署)
- [多容器部署](#多容器部署)
- [生产环境部署](#生产环境部署)
- [配置管理](#配置管理)
- [性能优化](#性能优化)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)

## 🐳 Docker基础

### 什么是Docker？

Docker是一个开源的应用容器引擎，让开发者可以打包他们的应用以及依赖包到一个可移植的容器中，然后发布到任何流行的Linux机器或Windows机器上。

### 为什么使用Docker？

- **环境一致性**: 确保开发、测试和生产环境一致
- **快速部署**: 秒级启动和停止
- **资源隔离**: 容器间资源隔离，提高安全性
- **扩展性**: 易于水平扩展
- **版本管理**: 镜像版本化管理

## 🔧 系统要求

### 最低要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2核心 | 4核心+ |
| 内存 | 4GB | 8GB+ |
| 存储 | 10GB | 50GB+ |
| Docker版本 | 20.10+ | 24.0+ |
| 操作系统 | Linux/macOS/Windows | Linux (Ubuntu 20.04+) |

### 软件依赖

```bash
# 安装Docker (Ubuntu)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🚀 快速开始

### 1. 拉取预构建镜像

```bash
# 拉取最新版本
docker pull gis-association:latest

# 拉取指定版本
docker pull gis-association:v1.0.0
```

### 2. 运行容器

```bash
# 基础运行
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  gis-association:latest

# 后台运行
docker run -d \
  --name gis-association \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  gis-association:latest

# 查看运行状态
docker ps
docker logs gis-association
```

### 3. 执行分析

```bash
# 进入容器执行分析
docker exec -it gis-association \
  gis-association process \
    --input-points /app/data/points.shp \
    --input-lines /app/data/lines.shp \
    --output /app/output/result.gpkg
```

## 🏗️ 单容器部署

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 安装应用
RUN pip install -e .

# 创建数据目录
RUN mkdir -p /app/data /app/output /app/logs

# 设置权限
RUN chmod +x /app/docker-entrypoint.sh

# 暴露端口（如果需要Web服务）
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD gis-association --version || exit 1

# 设置入口点
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gis-association", "--help"]
```

### docker-entrypoint.sh

```bash
#!/bin/bash
# docker-entrypoint.sh

set -e

# 确保数据目录存在
mkdir -p /app/data /app/output /app/logs

# 设置权限
chown -R appuser:appuser /app
exec "$@"
```

### 构建镜像

```bash
# 构建镜像
docker build -t gis-association:latest .

# 构建指定版本
docker build -t gis-association:v1.0.0 .

# 查看镜像
docker images | grep gis-association
```

### 运行脚本

```bash
#!/bin/bash
# run-docker.sh

# 设置变量
IMAGE_NAME="gis-association:latest"
CONTAINER_NAME="gis-association"
DATA_DIR="./data"
OUTPUT_DIR="./output"
CONFIG_DIR="./config"

# 创建目录
mkdir -p "$DATA_DIR" "$OUTPUT_DIR" "$CONFIG_DIR"

# 运行容器
docker run -it --rm \
  --name "$CONTAINER_NAME" \
  -v "$(pwd)/$DATA_DIR:/app/data" \
  -v "$(pwd)/$OUTPUT_DIR:/app/output" \
  -v "$(pwd)/$CONFIG_DIR:/app/config" \
  -e GIS_ASSOCIATION_CONFIG_PATH=/app/config \
  -e PYTHONPATH=/app \
  "$IMAGE_NAME" "$@"
```

## 🐙 多容器部署

### docker-compose.yml

```yaml
version: '3.8'

services:
  # 主应用服务
  gis-association:
    build: .
    container_name: gis-association-app
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/gis_db
      - PYTHONPATH=/app
      - GIS_ASSOCIATION_LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data:ro
      - ./output:/app/output
      - ./config:/app/config:ro
      - ./logs:/app/logs
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis
    networks:
      - gis-network

  # PostgreSQL数据库
  postgres:
    image: postgis/postgis:14-3.2
    container_name: gis-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=gis_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d:ro
    ports:
      - "5432:5432"
    networks:
      - gis-network

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: gis-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - gis-network

  # Nginx负载均衡
  nginx:
    image: nginx:alpine
    container_name: gis-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - gis-association
    networks:
      - gis-network

  # 监控服务
  prometheus:
    image: prom/prometheus:latest
    container_name: gis-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - gis-network

  # 可视化监控
  grafana:
    image: grafana/grafana:latest
    container_name: gis-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - gis-network

# 数据卷
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local

# 网络
networks:
  gis-network:
    driver: bridge
```

### 启动多容器服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f gis-association

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## 🏭 生产环境部署

### 生产环境docker-compose.yml

```yaml
version: '3.8'

services:
  # 主应用服务 - 多实例
  gis-association:
    image: gis-association:production
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/gis_db
      - LOG_LEVEL=INFO
      - MONITORING_ENABLED=true
    volumes:
      - shared_data:/app/data:ro
      - shared_output:/app/output
    depends_on:
      - postgres
      - redis
    networks:
      - gis-network
    healthcheck:
      test: ["CMD", "gis-association", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 任务队列服务
  worker:
    image: gis-association:production
    restart: always
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
    command: ["celery", "-A", "gis_association.celery_app", "worker", "--loglevel=info"]
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/gis_db
    depends_on:
      - redis
    networks:
      - gis-network

  # 调度服务
  scheduler:
    image: gis-association:production
    restart: always
    command: ["celery", "-A", "gis_association.celery_app", "beat", "--loglevel=info"]
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    networks:
      - gis-network

  # 高可用数据库
  postgres:
    image: postgis/postgis:14-3.2
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    environment:
      - POSTGRES_DB=gis_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - gis-network

  # Redis集群
  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
    deploy:
      replicas: 3
    volumes:
      - redis_data:/data
    networks:
      - gis-network

  # 负载均衡
  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - shared_output:/var/www/output:ro
    depends_on:
      - gis-association
    networks:
      - gis-network

# 数据卷
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/postgres
  redis_data:
    driver: local
  shared_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/gis
  shared_output:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/output

networks:
  gis-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 生产环境配置

```bash
# .env.production
POSTGRES_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_redis_password_here
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
BACKUP_SCHEDULE=0 2 * * *
MONITORING_ENABLED=true
LOG_LEVEL=INFO
```

### 部署脚本

```bash
#!/bin/bash
# deploy-production.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    log_info "检查部署环境..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    # 检查环境变量文件
    if [ ! -f ".env.production" ]; then
        log_error "生产环境配置文件 .env.production 不存在"
        exit 1
    fi

    log_info "环境检查通过"
}

# 构建镜像
build_images() {
    log_info "构建生产镜像..."

    docker build -t gis-association:production --target production .

    log_info "镜像构建完成"
}

# 部署服务
deploy_services() {
    log_info "部署生产服务..."

    # 使用生产配置
    export COMPOSE_FILE="docker-compose.yml:docker-compose.prod.yml"

    # 停止现有服务
    docker-compose -f $COMPOSE_FILE down

    # 启动服务
    docker-compose -f $COMPOSE_FILE up -d

    # 等待服务启动
    sleep 30

    # 检查服务状态
    docker-compose -f $COMPOSE_FILE ps

    log_info "服务部署完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 检查主服务
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_info "主服务健康检查通过"
    else
        log_error "主服务健康检查失败"
        exit 1
    fi

    # 检查数据库连接
    if docker-compose exec -T postgres pg_isready > /dev/null 2>&1; then
        log_info "数据库连接正常"
    else
        log_error "数据库连接失败"
        exit 1
    fi

    # 检查Redis连接
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_info "Redis连接正常"
    else
        log_error "Redis连接失败"
        exit 1
    fi

    log_info "健康检查全部通过"
}

# 主函数
main() {
    log_info "开始生产环境部署..."

    check_environment
    build_images
    deploy_services
    health_check

    log_info "生产环境部署完成！"
    log_info "访问地址: http://localhost"
    log_info "监控面板: http://localhost:3000"
}

# 执行部署
main "$@"
```

## ⚙️ 配置管理

### 应用配置

```yaml
# config/docker-config.yaml
server:
  host: "0.0.0.0"
  port: 8080
  workers: 4

database:
  type: "postgresql"
  host: "postgres"
  port: 5432
  database: "gis_db"
  username: "postgres"
  password: "${POSTGRES_PASSWORD}"
  pool_size: 10
  max_overflow: 20

redis:
  host: "redis"
  port: 6379
  password: "${REDIS_PASSWORD}"
  database: 0
  max_connections: 10

storage:
  type: "file"
  base_path: "/app/data"
  output_path: "/app/output"
  cache_path: "/app/cache"

logging:
  level: "INFO"
  format: "json"
  file: "/app/logs/gis-association.log"
  max_size: "100MB"
  backup_count: 5

monitoring:
  enabled: true
  prometheus:
    port: 9090
  health_check:
    interval: 30
    timeout: 10

analysis:
  default_max_distance: 1000
  parallel_workers: 4
  chunk_size: 1000
  memory_limit: 4096
```

### Nginx配置

```nginx
# nginx/nginx.conf
upstream gis_association {
    server gis-association:8080;
    # 如果有多个实例
    # server gis-association_1:8080;
    # server gis-association_2:8080;
}

server {
    listen 80;
    server_name your-domain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL配置
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 上传限制
    client_max_body_size 100M;

    # 静态文件
    location /output/ {
        alias /var/www/output/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # API代理
    location /api/ {
        proxy_pass http://gis_association;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查
    location /health {
        access_log off;
        proxy_pass http://gis_association/health;
    }
}
```

## ⚡ 性能优化

### 容器资源优化

```yaml
# docker-compose.optimized.yml
version: '3.8'

services:
  gis-association:
    image: gis-association:production
    deploy:
      resources:
        # 资源限制
        limits:
          cpus: '4.0'
          memory: 8G
        # 资源预留
        reservations:
          cpus: '2.0'
          memory: 4G

      # 更新策略
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback

      # 重启策略
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

    # 性能调优
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

    # 安全配置
    security_opt:
      - no-new-privileges:true

    # 只读根文件系统
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

### 缓存优化

```yaml
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
      --appendonly yes
      --appendfsync everysec

    # 内存优化
    sysctls:
      - net.core.somaxconn=65535

    # 性能调优
    deploy:
      resources:
        limits:
          memory: 2G
```

### 数据库优化

```yaml
  postgres:
    image: postgis/postgis:14-3.2
    environment:
      # 性能调优参数
      - POSTGRES_SHARED_BUFFERS=256MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
      - POSTGRES_WORK_MEM=4MB
      - POSTGRES_MAINTENANCE_WORK_MEM=64MB
      - POSTGRES_CHECKPOINT_COMPLETION_TARGET=0.9
      - POSTGRES_WAL_BUFFERS=16MB
      - POSTGRES_DEFAULT_STATISTICS_TARGET=100
      - POSTGRES_RANDOM_PAGE_COST=1.1
      - POSTGRES_EFFECTIVE_IO_CONCURRENCY=200
```

## 📊 监控和日志

### Prometheus配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "gis_rules.yml"

scrape_configs:
  - job_name: 'gis-association'
    static_configs:
      - targets: ['gis-association:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
```

### 日志配置

```yaml
# logging/docker-logging.yml
version: 1

formatters:
  json:
    format: '%(asctime)s %(name)s %(levelname)s %(message)s'
    class: pythonjsonlogger.jsonlogger.JsonFormatter

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /app/logs/gis-association.log
    maxBytes: 104857600  # 100MB
    backupCount: 5

loggers:
  gis_association:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console]
```

### 监控脚本

```bash
#!/bin/bash
# monitoring.sh

# 检查容器状态
check_containers() {
    echo "=== 容器状态 ==="
    docker-compose ps

    echo -e "\n=== 容器资源使用 ==="
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 检查日志
check_logs() {
    echo "=== 应用日志 ==="
    docker-compose logs --tail=100 gis-association

    echo -e "\n=== 数据库日志 ==="
    docker-compose logs --tail=50 postgres

    echo -e "\n=== Redis日志 ==="
    docker-compose logs --tail=50 redis
}

# 性能监控
monitor_performance() {
    echo "=== 性能指标 ==="

    # CPU使用率
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}"

    # 内存使用
    docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

    # 网络IO
    docker stats --no-stream --format "table {{.Name}}\t{{.NetIO}}"
}

# 健康检查
health_check() {
    echo "=== 健康检查 ==="

    services=("gis-association" "postgres" "redis" "nginx")

    for service in "${services[@]}"; do
        health=$(docker-compose ps -q $service | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
        echo "$service: $health"
    done
}

# 主菜单
case "$1" in
    "containers")
        check_containers
        ;;
    "logs")
        check_logs
        ;;
    "performance")
        monitor_performance
        ;;
    "health")
        health_check
        ;;
    "all")
        check_containers
        echo
        health_check
        echo
        monitor_performance
        ;;
    *)
        echo "用法: $0 {containers|logs|performance|health|all}"
        exit 1
        ;;
esac
```

## 🔧 故障排除

### 常见问题

#### 1. 容器启动失败

```bash
# 查看容器状态
docker-compose ps

# 查看错误日志
docker-compose logs gis-association

# 检查镜像
docker images | grep gis-association

# 重新构建镜像
docker-compose build --no-cache gis-association
```

#### 2. 内存不足

```bash
# 查看内存使用
docker stats

# 调整容器内存限制
docker-compose -f docker-compose.yml up -d --scale gis-association=1

# 清理未使用的容器和镜像
docker system prune -a
```

#### 3. 网络连接问题

```bash
# 检查网络
docker network ls
docker network inspect gis-association_gis-network

# 测试容器间连接
docker-compose exec gis-association ping postgres
docker-compose exec gis-association ping redis

# 重建网络
docker-compose down
docker network prune
docker-compose up -d
```

#### 4. 数据库连接问题

```bash
# 检查数据库状态
docker-compose exec postgres pg_isready

# 查看数据库日志
docker-compose logs postgres

# 连接数据库
docker-compose exec postgres psql -U postgres -d gis_db

# 重置数据库
docker-compose down -v
docker-compose up -d postgres
```

### 调试命令

```bash
# 进入容器调试
docker-compose exec gis-association bash

# 查看容器内部进程
docker-compose exec gis-association ps aux

# 查看容器资源限制
docker-compose exec gis-association cat /proc/meminfo
docker-compose exec gis-association cat /proc/cpuinfo

# 监控容器性能
docker stats gis-association
```

### 备份和恢复

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U postgres gis_db > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U postgres gis_db < backup.sql

# 备份数据卷
docker run --rm -v gis-association_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# 恢复数据卷
docker run --rm -v gis-association_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

---

**通过Docker容器化部署，您可以快速、可靠地部署和扩展GIS空间关联分析系统！🐳**