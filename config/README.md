# Nginx Manager 配置说明

## 配置文件统一

原来的多个配置文件 (`config.yml`, `settings.yml`, `ssl.yml`) 已经统一为单个 `config.yml` 文件，简化了配置管理。

## 配置文件结构

### 基本配置

```yaml
# 环境配置
environment: "docker"  # 可选: "docker", "native", "development"

# Nginx 配置
nginx:
  config_dir: "/etc/nginx/conf.d"  # Nginx配置文件目录
  log_dir: "/var/log/nginx"        # Nginx日志目录

# SSL 证书配置
ssl:
  certs_dir: "/app/certs"          # 证书存储目录
  email: "test@gmail.com"          # 证书申请邮箱 (必须有效)
  ca_server: "letsencrypt"         # CA服务器
  key_length: 2048                 # 私钥长度
  auto_upgrade: true               # 自动升级证书

# ACME 配置
acme:
  staging: true                    # 是否使用测试环境
  force: false                     # 强制重新申请
  debug: false                     # 调试模式
```

### CA 服务器配置

```yaml
ca_servers:
  letsencrypt:
    server: "https://acme-v02.api.letsencrypt.org/directory"
    staging_server: "https://acme-staging-v02.api.letsencrypt.org/directory"
  zerossl:
    server: "https://acme.zerossl.com/v2/DV90"
  buypass:
    server: "https://api.buypass.com/acme/directory"
    staging_server: "https://api.test4.buypass.no/acme/directory"
```

### 高级配置

```yaml
# 日志配置
logs:
  dir: "/app/logs"                 # 日志目录
  level: "info"                    # 日志级别

# 服务配置
service:
  auto_reload: true                # 自动重载nginx
  backup_configs: true             # 备份配置文件

# 高级配置
advanced:
  renewal_check_interval: 24       # 证书检查间隔(小时)
  renewal_days_before_expiry: 30   # 提前续期天数
  concurrent_cert_limit: 3         # 并发证书申请限制
  retry_attempts: 3                # 重试次数
  retry_interval: 300              # 重试间隔(秒)
  www_dir: "/var/www/html"         # Web根目录
```

## 环境变量覆盖

所有配置项都可以通过环境变量覆盖，格式为：`NGINX_MANAGER_<KEY>`

例子：
```bash
export NGINX_MANAGER_SSL_EMAIL="your@email.com"
export NGINX_MANAGER_ACME_STAGING=false
export NGINX_MANAGER_SSL_CA_SERVER="zerossl"
```

## 配置优先级

1. 环境变量 (最高优先级)
2. config.yml 文件
3. 默认值 (最低优先级)

## 迁移说明

如果您之前使用多个配置文件，请：

1. 将 `settings.yml` 和 `ssl.yml` 中的配置合并到 `config.yml`
2. 删除旧的配置文件
3. 重新启动服务

## CA 服务器说明

- **letsencrypt**: 免费，稳定，推荐用于生产环境
- **zerossl**: 免费，备选方案
- **buypass**: 免费，欧洲服务商

## 环境类型说明

- **docker**: Docker容器环境
- **native**: 原生系统环境
- **development**: 开发环境 (启用调试功能)

## 示例配置

### 生产环境
```yaml
environment: "docker"
ssl:
  email: "admin@yourdomain.com"
  ca_server: "letsencrypt"
acme:
  staging: false
```

### 测试环境
```yaml
environment: "development"
ssl:
  email: "test@example.com"
  ca_server: "letsencrypt"
acme:
  staging: true
  debug: true
``` 