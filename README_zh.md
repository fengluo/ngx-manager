# Nginx Manager

[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)](run_tests.py)

[🇺🇸 English Documentation](README.md)

一个基于Docker的Nginx自动化管理配置工具，支持虚拟主机配置、SSL证书自动申请和管理。

## 🚀 功能特性

### 1. 简化的虚拟主机配置
- 使用简单的配置文件描述虚拟主机代理服务
- 支持配置域名、API代理转发和静态文件访问路径
- 支持基于路径的代理转发和静态文件路径配置
- 自动生成标准的Nginx配置文件

### 2. 自动化配置生成
- 读取配置文件并提取虚拟主机描述
- 基于模板自动生成Nginx虚拟主机配置
- 支持多种代理模式和静态资源服务

### 3. SSL证书自动管理
- 集成 [acme.sh](https://github.com/acmesh-official/acme.sh) 自动申请SSL证书
- 容器启动时自动检查并申请缺失的证书
- 自动续期证书，无需手动干预
- 支持多种证书颁发机构

### 4. 灵活的手动操作
- 手动触发重新生成虚拟主机配置
- 手动申请或更新指定域名的SSL证书
- 支持修改acme.sh邮箱和证书服务商配置
- 提供友好的命令行接口

### 5. 友好的日志输出
- 详细的操作日志记录
- 清晰的错误信息提示
- 实时的证书申请和配置生成状态

## 📋 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 域名解析到服务器IP（用于SSL证书申请）

## 🛠️ 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd nginx-manager
```

### 2. 启动服务

```bash
# 使用Python启动脚本
python3 start.py

# 或者使用Docker Compose
python3 start.py compose-up
```

### 3. 访问服务
- HTTP: http://localhost
- HTTPS: https://localhost (如果配置了SSL)

### 4. 查看日志

```bash
# 查看容器日志
python3 start.py logs --follow

# 或使用Docker命令
docker logs -f nginx-manager
```

### 5. 停止服务

```bash
python3 start.py stop
```

## 📁 项目结构

```
nginx-manager/
├── Dockerfile                 # Docker镜像构建文件
├── docker-compose.yml         # Docker Compose配置
├── start.py                   # Python启动脚本
├── README.md                  # 项目文档
├── LICENSE                    # 许可证
├── .gitignore                 # Git忽略文件
├── config/                    # 配置文件目录
│   ├── nginx.conf            # Nginx主配置文件
│   ├── vhosts.yml            # 虚拟主机配置
│   └── ssl.yml               # SSL证书配置
├── templates/                 # 配置模板目录
│   └── vhost.conf.j2         # 虚拟主机模板
├── scripts/                   # 脚本目录
│   ├── generate-config.py    # 配置生成脚本 (Python)
│   ├── cert_manager.py       # 证书管理脚本 (Python)
│   └── entrypoint.py         # 容器启动脚本 (Python)
├── examples/                  # 示例文件
│   ├── api-service.html      # API服务示例页面
│   └── static-site.html      # 静态站点示例页面
├── logs/                      # 日志目录 (自动创建)
├── certs/                     # 证书目录 (自动创建)
└── nginx-conf/                # 生成的nginx配置 (自动创建)
```

**重要目录说明**：
- `nginx-conf/` - **核心功能目录**，包含所有生成的Nginx虚拟主机配置文件
  - 每个虚拟主机会生成对应的 `.conf` 文件
  - 文件名格式：`{vhost-name}.conf`
  - 映射到容器的 `/etc/nginx/conf.d/` 目录
  - 支持实时查看、编辑和调试配置

## 🔧 配置说明

### 虚拟主机配置 (vhosts.yml)

支持两种配置格式：

**格式一：完整格式**
```yaml
- name: "服务名称"
  domains:
    - "域名1"
    - "域名2"
  ssl: true|false         # 是否启用SSL
  
  # 简单模式配置（向后兼容）
  type: "proxy|static"     # 代理模式或静态文件模式
  upstream: "后端服务地址"   # 仅proxy模式需要
  root: "静态文件根目录"     # 仅static模式需要
  auth_basic: true|false  # 是否启用基础认证
  
  # 高级路径配置模式
  locations:
    - path: "/路径"        # 匹配路径，支持正则表达式
      type: "proxy|static" # 该路径的处理类型
      
      # 代理配置（type: proxy时使用）
      upstream: "后端服务地址"
      proxy_pass_path: "/重写路径"  # 可选：重写传递给后端的路径
      proxy_read_timeout: "30s"   # 可选：读取超时
      proxy_connect_timeout: "5s" # 可选：连接超时
      proxy_send_timeout: "30s"   # 可选：发送超时
      websocket: true|false       # 可选：WebSocket支持
      
      # 静态文件配置（type: static时使用）
      root: "文件根目录"
      try_files: "$uri $uri/ /index.html"  # 可选：try_files指令
      expires: "30d"              # 可选：缓存过期时间
      autoindex: true|false       # 可选：目录浏览
      
      # 通用配置
      auth_basic: true|false      # 可选：基础认证
      auth_basic_user_file: "认证文件路径"  # 可选：认证文件
      custom_config: |            # 可选：自定义Nginx配置
        # 额外的location配置指令
        add_header X-Custom-Header "value";
  
  # 全局自定义配置
  custom_config: |        # 可选：server级别自定义配置
    # 额外的server配置指令
```

**格式二：简化格式（推荐）**
```yaml
# 直接使用数组，省略vhosts键
- name: "服务名称"
  domains:
    - "域名1"
    - "域名2"
  ssl: true|false
  # ... 其他配置项与完整格式相同
```

**格式选择建议**：
- **简化格式**：适合大多数场景，配置更简洁直观
- **完整格式**：适合需要在配置文件中添加全局元数据或注释的复杂项目

### SSL配置 (ssl.yml)

```yaml
ssl:
  email: "证书申请邮箱"
  ca_server: "证书颁发机构"  # letsencrypt, zerossl, buypass
  key_length: 2048         # 密钥长度
  auto_upgrade: true       # 自动升级acme.sh

acme:
  staging: false           # 是否使用测试环境
  force: false            # 强制重新申请证书
  debug: false            # 调试模式
```

### 路径匹配规则

支持以下路径匹配模式：

```yaml
locations:
  # 精确匹配
  - path: "= /exact"
    type: "proxy"
    upstream: "http://service:8080"
  
  # 前缀匹配（默认）
  - path: "/api"
    type: "proxy"
    upstream: "http://api:8080"
  
  # 正则匹配
  - path: "~ ^/files/(.+)\\.(jpg|jpeg|png|gif)$"
    type: "static"
    root: "/var/www/images"
  
  # 不区分大小写的正则匹配
  - path: "~* \\.(css|js)$"
    type: "static"
    root: "/var/www/assets"
    expires: "1y"
  
  # 优先前缀匹配
  - path: "^~ /static"
    type: "static"
    root: "/var/www"
```

### 配置优先级和最佳实践

1. **匹配优先级**（按Nginx规则）：
   - `= /exact` - 精确匹配（最高优先级）
   - `^~ /prefix` - 优先前缀匹配
   - `~ regex` 和 `~* regex` - 正则匹配（按配置顺序）
   - `/prefix` - 普通前缀匹配（最低优先级）

2. **配置建议**：
   ```yaml
   locations:
     # 1. 精确匹配特殊路径
     - path: "= /"
       type: "static"
       root: "/var/www/html"
       try_files: "index.html"
     
     # 2. 优先前缀匹配静态资源
     - path: "^~ /static"
       type: "static"
       root: "/var/www"
       expires: "1y"
     
     # 3. API路径代理
     - path: "/api"
       type: "proxy"
       upstream: "http://backend:8080"
     
     # 4. 正则匹配文件类型
     - path: "~* \\.(css|js|png|jpg|jpeg|gif|ico|svg)$"
       type: "static"
       root: "/var/www/assets"
       expires: "30d"
     
     # 5. 默认处理（放在最后）
     - path: "/"
       type: "static"
       root: "/var/www/html"
       try_files: "$uri $uri/ /index.html"
   ```

3. **常见配置模式**：
   ```yaml
   # SPA应用配置
   - path: "/api"
     type: "proxy"
     upstream: "http://api-server:8080"
   - path: "/"
     type: "static"
     root: "/var/www/spa"
     try_files: "$uri $uri/ /index.html"
   
   # 文件上传和下载
   - path: "/upload"
     type: "proxy"
     upstream: "http://upload-service:8080"
     client_max_body_size: "100m"
   - path: "/files"
     type: "static"
     root: "/var/www/uploads"
     autoindex: true
   
   # WebSocket代理
   - path: "/ws"
     type: "proxy"
     upstream: "http://websocket-server:8080"
     websocket: true
   ```

## 🎯 使用示例

### 启动服务

```bash
# 基本启动
python3 start.py

# 重新构建并启动
python3 start.py build --no-cache

# 前台运行（用于调试）
python3 start.py start --no-detach

# 使用Docker Compose
python3 start.py compose-up
```

### 管理容器

```bash
# 查看状态
python3 start.py status

# 查看日志
python3 start.py logs

# 跟踪日志
python3 start.py logs --follow

# 重启服务
python3 start.py restart

# 停止服务
python3 start.py stop
```

### 手动操作

```bash
# 进入容器
docker exec -it nginx-manager bash

# 手动生成配置
docker exec nginx-manager python3 /app/scripts/generate-config.py --all

# 手动申请证书
docker exec nginx-manager python3 /app/scripts/cert_manager.py --domain example.com

# 手动更新所有证书
docker exec nginx-manager python3 /app/scripts/cert_manager.py --renew-all

# 查看证书列表
docker exec nginx-manager python3 /app/scripts/cert_manager.py --list
```

## 🔍 故障排除

### 常见问题

1. **证书申请失败**
   - 检查域名DNS解析是否正确
   - 确认80端口可以正常访问
   - 查看证书申请日志：`docker exec nginx-manager cat /app/logs/cert.log`

2. **配置生成失败**
   - 检查配置文件语法是否正确
   - 确认模板文件存在
   - 查看配置生成日志

3. **Nginx启动失败**
   - 检查生成的配置文件语法
   - 确认上游服务可达性
   - 查看Nginx错误日志

4. **配置文件映射问题**
   - 确认 `nginx-conf/` 目录存在且有写权限
   - 检查Docker卷映射是否正确：`-v $(pwd)/nginx-conf:/etc/nginx/conf.d`
   - 验证生成的配置文件：`ls -la nginx-conf/`
   - 查看配置文件内容是否正确：`cat nginx-conf/*.conf`

5. **配置不生效问题**
   - 确认配置文件已生成：`docker exec nginx-manager ls -la /etc/nginx/conf.d/`
   - 检查Nginx是否重新加载：`docker exec nginx-manager nginx -s reload`
   - 验证配置语法：`docker exec nginx-manager nginx -t`
   - 查看Nginx进程状态：`docker exec nginx-manager ps aux | grep nginx`

### 调试模式

启用调试模式获取更详细的日志：

```bash
# 修改ssl.yml中的debug设置
acme:
  debug: true

# 重启容器
docker-compose restart
```

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Nginx](https://nginx.org/) - 高性能Web服务器
- [acme.sh](https://github.com/acmesh-official/acme.sh) - ACME协议客户端
- [Let's Encrypt](https://letsencrypt.org/) - 免费SSL证书服务

## 📞 支持

如果您遇到问题或有建议，请：

1. 查看 [Issues](https://github.com/your-username/nginx-manager/issues) 页面
2. 创建新的 Issue 描述问题
3. 联系维护者：your-email@example.com

---

**注意**: 请确保在生产环境中使用前充分测试配置，并定期备份重要数据。

## 🔍 技术架构

### 核心组件
- **Nginx**: 高性能Web服务器和反向代理
- **Python**: 统一的脚本语言，用于配置生成和证书管理
- **acme.sh**: SSL证书自动申请和管理
- **Jinja2**: 强大的模板引擎
- **Docker**: 容器化部署

### 脚本说明
- `start.py`: Python启动脚本，负责Docker容器管理
- `scripts/entrypoint.py`: 容器启动脚本，负责初始化和服务启动
- `scripts/generate-config.py`: 配置生成脚本，基于YAML配置生成nginx配置
- `scripts/cert_manager.py`: SSL证书管理脚本，集成acme.sh

### 设计优势
1. **统一语言**: 全部使用Python，提高代码一致性和维护性
2. **模块化设计**: 各功能模块独立，便于扩展和维护
3. **配置驱动**: 基于YAML配置文件，简化管理
4. **自动化**: 支持配置监控、证书自动续期
5. **容器化**: Docker部署，环境一致性好 