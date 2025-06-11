# Nginx Manager

[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于 Docker 的 Nginx 自动化管理工具，简化虚拟主机配置和 SSL 证书管理。

[🇺🇸 English Documentation](README.md)

## 功能特性

- **虚拟主机管理**: 使用简单的 YAML 文件配置多个域名和服务
- **SSL 证书自动化**: 使用 acme.sh 自动申请和续期证书
- **灵活部署**: 支持 pip 安装、Docker 和源码部署
- **多种代理模式**: 支持反向代理、静态文件和混合配置

## 快速开始

选择以下任一部署方式：

### 1. pip 安装 (推荐)

```bash
# 从 PyPI 安装
pip install nginx-manager

# 创建配置目录
mkdir -p ~/nginx-manager/{config,logs,certs}

# 启动服务
nginx-manager start
```

### 2. Docker 部署

```bash
# 拉取并运行
docker run -d --name nginx-manager \
  -p 80:80 -p 443:443 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/certs:/app/certs \
  nginx-manager:latest

# 或使用 Docker Compose
curl -O https://raw.githubusercontent.com/your-repo/nginx-manager/main/docker-compose.yml
docker-compose up -d
```

### 3. 源码安装

```bash
# 克隆仓库
git clone https://github.com/your-repo/nginx-manager.git
cd nginx-manager

# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m nginx_manager.main start
```

## 配置说明

### 虚拟主机配置 (`config/vhosts.yml`)

```yaml
# 简单代理配置
- name: "api-service"
  domains:
    - "api.example.com"
  ssl: true
  type: "proxy"
  upstream: "http://backend:8080"

# 静态文件配置
- name: "static-site"
  domains:
    - "static.example.com"
  ssl: true
  type: "static"
  root: "/var/www/html"

# 高级路径配置
- name: "mixed-service"
  domains:
    - "app.example.com"
  ssl: true
  locations:
    - path: "/api"
      type: "proxy"
      upstream: "http://api-server:8080"
    - path: "/static"
      type: "static"
      root: "/var/www/static"
    - path: "/"
      type: "static"
      root: "/var/www/html"
      try_files: "$uri $uri/ /index.html"
```

### 主配置文件 (`config/config.yml`)

```yaml
# Nginx 配置
nginx:
  log_dir: "/var/log/nginx"

# SSL 证书配置
ssl:
  certs_dir: "/tmp/certs"
  email: "your-email@example.com"           # 必填：有效邮箱地址
  ca_server: "letsencrypt"                  # letsencrypt, zerossl, buypass
  key_length: 2048
  auto_upgrade: true
  staging: false                            # 测试环境设为 true
  force: false                              # 强制重新申请证书
  debug: false                              # 调试模式
  renewal_check_interval: 24                # 检查间隔（小时）
  renewal_days_before_expiry: 30            # 提前续期天数
  concurrent_cert_limit: 3                  # 并发申请限制
  retry_attempts: 3                         # 重试次数
  retry_interval: 300                       # 重试间隔（秒）

# 日志配置
logs:
  dir: "/tmp/logs"
  level: "info"                             # debug, info, warning, error

# 服务配置
service:
  auto_reload: true                         # 自动重载 nginx
  backup_configs: true                      # 备份配置文件

# 高级配置
advanced:
  www_dir: "/var/www/html"                  # Web 根目录
```

### Nginx 配置 (`config/nginx.conf`)

主 nginx 配置文件会自动生成，但如需要可以自定义。

## 使用方法

### 命令行接口

```bash
# 启动服务
nginx-manager start

# 停止服务
nginx-manager stop

# 重启服务
nginx-manager restart

# 生成配置
nginx-manager generate

# 申请 SSL 证书
nginx-manager cert --domain example.com

# 续期所有证书
nginx-manager renew

# 查看状态
nginx-manager status

# 查看日志
nginx-manager logs
```

### Docker 命令

```bash
# 查看日志
docker logs nginx-manager

# 在容器内执行命令
docker exec nginx-manager nginx-manager status

# 重启容器
docker restart nginx-manager
```

## 开发

### 搭建开发环境

```bash
# 克隆仓库
git clone https://github.com/your-repo/nginx-manager.git
cd nginx-manager

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行测试并显示覆盖率
python -m pytest --cov=nginx_manager

# 运行特定测试文件
python -m pytest tests/test_config.py

# 运行集成测试 (需要 Docker)
python -m pytest tests/integration/
```

### 项目结构

```
nginx-manager/
├── nginx_manager/          # 主包
│   ├── __init__.py
│   ├── main.py            # CLI 入口
│   ├── config.py          # 配置管理
│   ├── generator.py       # 配置生成
│   ├── cert_manager.py    # SSL 证书管理
│   └── templates/         # Jinja2 模板
├── tests/                 # 测试套件
├── config/                # 配置文件
├── requirements.txt       # 生产依赖
├── requirements-dev.txt   # 开发依赖
├── setup.py              # 包设置
└── Dockerfile            # Docker 构建文件
```

## 问题排查

### 常见问题

1. **权限错误**: 确保用户对配置和日志目录有写权限
2. **端口冲突**: 检查 80/443 端口是否被占用
3. **SSL 证书问题**: 验证域名 DNS 解析和 80 端口可访问性
4. **配置错误**: 验证 YAML 语法和必需字段

### 调试模式

启用调试日志：

```bash
# 设置环境变量
export NGINX_MANAGER_DEBUG=1

# 或修改 config.yml
ssl:
  debug: true
logs:
  level: "debug"
```

## 贡献

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

### 开发规范

- 遵循 PEP 8 代码风格
- 为新功能编写测试
- 更新用户相关文档
- 确保所有测试通过

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 支持

- 📖 文档: [GitHub Wiki](https://github.com/your-repo/nginx-manager/wiki)
- 🐛 问题: [GitHub Issues](https://github.com/your-repo/nginx-manager/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/your-repo/nginx-manager/discussions)

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本历史和更新。 