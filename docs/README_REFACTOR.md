# Nginx Manager 重构说明

本文档说明了nginx-manager项目的重构内容和新的使用方法。

## 重构概述

### 主要改进

1. **统一配置管理** - 支持环境变量和配置文件的统一配置系统
2. **原生安装支持** - 完整的原生环境安装和依赖管理
3. **标准Python包结构** - 符合Python最佳实践的包结构
4. **虚拟环境支持** - 完整的虚拟环境管理和激活脚本
5. **分离测试环境** - 独立的原生和Docker环境测试
6. **精简配置文件** - 移除冗余配置，保留核心功能
7. **改进的CLI接口** - 更加直观和功能完整的命令行界面
8. **简化目录结构** - 移除不必要的嵌套，直接使用根目录下的nginx_manager包

### 最终项目结构

```
nginx-manager/
├── nginx_manager/              # 主要源代码包
│   ├── __init__.py            # 包初始化文件
│   ├── cli.py                 # 命令行接口
│   ├── config/                # 配置管理模块
│   │   ├── __init__.py
│   │   └── settings.py        # 统一配置系统
│   ├── core/                  # 核心功能模块
│   │   ├── __init__.py
│   │   └── manager.py         # Nginx管理器
│   ├── ssl/                   # SSL证书管理模块
│   │   ├── __init__.py
│   │   └── manager.py         # SSL管理器
│   ├── templates/             # 配置模板模块
│   │   ├── __init__.py
│   │   └── generator.py       # 配置生成器
│   └── utils/                 # 工具模块
│       ├── __init__.py
│       ├── environment.py     # 环境管理
│       └── docker.py          # Docker管理
├── tests/                     # 测试代码
│   ├── test_native.py         # 原生环境测试
│   ├── test_docker.py         # Docker环境测试
│   └── ...                    # 其他测试文件
├── scripts/                   # 开发脚本
│   └── setup_venv.py          # 虚拟环境设置
├── config/                    # 配置文件
│   ├── config.yml             # 主配置文件
│   └── ssl.yml                # SSL配置文件
├── requirements.txt           # 生产依赖
├── requirements-dev.txt       # 开发依赖
├── setup.py                   # 包安装配置
├── nginx_manager.py           # 直接运行入口
├── Makefile                   # 开发任务管理
├── Dockerfile                 # Docker构建文件
├── activate.sh                # 虚拟环境激活脚本
└── README_REFACTOR.md         # 重构说明文档
```

## 重构亮点

### 1. 简化的包结构
- **移除了 `src/` 目录**：直接使用根目录下的 `nginx_manager/` 包
- **减少嵌套层级**：从 `src/nginx_manager/` 简化为 `nginx_manager/`
- **符合Python标准**：遵循Python包的最佳实践

### 2. 完整的模块化设计
- **配置管理** (`nginx_manager/config/`)：统一的配置系统
- **核心功能** (`nginx_manager/core/`)：Nginx管理核心逻辑
- **SSL管理** (`nginx_manager/ssl/`)：证书申请和管理
- **模板系统** (`nginx_manager/templates/`)：配置文件生成
- **工具模块** (`nginx_manager/utils/`)：环境和Docker管理

### 3. 双环境支持
- **原生环境**：直接在系统上安装和运行
- **Docker环境**：容器化部署和管理
- **自动检测**：根据环境自动选择合适的运行模式

## 安装和使用

### 原生环境安装

#### 1. 快速设置（推荐）

```bash
# 设置开发环境
make setup-dev

# 或设置生产环境
make setup-prod

# 激活虚拟环境
source activate.sh
```

#### 2. 手动设置

```bash
# 创建虚拟环境
python3 scripts/setup_venv.py --dev

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements-dev.txt
pip install -e .
```

#### 3. 系统依赖安装

```bash
# 自动安装系统依赖
nginx-manager setup

# 或分步安装
nginx-manager setup --install-deps
nginx-manager setup --setup-nginx  
nginx-manager setup --setup-ssl
```

### Docker环境使用

#### 1. 使用Makefile（推荐）

```bash
# 构建并启动
make docker-build
make docker-start

# 查看日志
make docker-logs

# 停止容器
make docker-stop
```

#### 2. 使用CLI命令

```bash
# 构建并启动Docker容器
nginx-manager docker start --build

# 停止Docker容器
nginx-manager docker stop
```

#### 3. 手动Docker操作

```bash
# 构建镜像
docker build -t nginx-manager .

# 启动容器
docker run -d --name nginx-manager \
  -p 80:80 -p 443:443 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/certs:/app/certs \
  nginx-manager
```

## 配置系统

### 环境变量支持

配置可以通过环境变量覆盖，格式为 `NGINX_MANAGER_<配置键>`：

```bash
# 设置SSL邮箱
export NGINX_MANAGER_SSL_EMAIL="your@email.com"

# 设置配置目录
export NGINX_MANAGER_CONFIG_DIR="/custom/config/path"
```

### 配置文件

主要配置文件：
- `config/config.yml` - 主配置文件
- `config/ssl.yml` - SSL专用配置

### 配置优先级

1. 环境变量（最高优先级）
2. 配置文件
3. 默认值（最低优先级）

## 基本使用

### 站点管理

```bash
# 查看状态
nginx-manager status

# 添加站点（带SSL）
nginx-manager add -d example.com -b http://localhost:3000

# 添加静态站点
nginx-manager add -d static.example.com

# 添加HTTP站点（无SSL）
nginx-manager add -d test.local -b http://localhost:8080 --no-ssl

# 列出所有站点
nginx-manager list

# 移除站点
nginx-manager remove -d example.com
```

### SSL证书管理

```bash
# 续期所有证书
nginx-manager renew

# 续期特定域名证书
nginx-manager renew -d example.com

# 强制续期
nginx-manager renew -d example.com --force
```

### Nginx管理

```bash
# 重载配置
nginx-manager reload

# 测试配置
nginx -t
```

## 开发和测试

### 运行测试

```bash
# 运行所有测试
make test

# 运行原生环境测试
make test-native

# 运行Docker环境测试  
make test-docker

# 运行覆盖率测试
make test-coverage
```

### 代码质量

```bash
# 代码格式化
make format

# 代码检查
make lint

# 检查依赖
make check-deps
```

### 开发工具

```bash
# 直接运行（无需安装）
python nginx_manager.py --help

# 快速添加开发站点
make dev-server

# 清理构建文件
make clean
```

## 环境兼容性

### 支持的操作系统

#### Linux
- Ubuntu/Debian (apt)
- CentOS/RHEL/Fedora (yum/dnf)
- Arch Linux (pacman)

#### macOS
- 通过Homebrew安装依赖

#### Docker
- 支持所有Docker环境

### Python版本要求

- Python 3.8+

### 系统依赖

- nginx
- openssl
- curl
- socat (SSL证书申请)
- cron (证书自动续期)

## 配置迁移

### 从旧版本迁移

1. **备份现有配置**
   ```bash
   cp -r config config.backup
   ```

2. **使用新的配置格式**
   - 旧的分散配置文件合并到 `config/config.yml`
   - SSL配置移动到 `config/ssl.yml`

3. **环境变量设置**
   ```bash
   # 替换旧的环境变量格式
   export NGINX_MANAGER_SSL_EMAIL="your@email.com"
   export NGINX_MANAGER_SSL_CA_SERVER="letsencrypt"
   ```

## 性能优化

### 精简的依赖

重构后移除了不必要的依赖：
- 移除了重复的Python包
- 精简了Docker镜像大小
- 优化了启动时间

### 改进的架构

- 模块化设计，按需加载
- 更好的错误处理和恢复
- 改进的日志记录

## 故障排除

### 常见问题

1. **导入错误**
   ```bash
   # 确保虚拟环境已激活
   source activate.sh
   
   # 或重新安装
   pip install -e .
   ```

2. **权限问题**
   ```bash
   # 确保有nginx配置目录写权限
   sudo chown -R $USER:$USER /usr/local/etc/nginx/servers
   ```

3. **Docker问题**
   ```bash
   # 检查Docker是否运行
   docker info
   
   # 清理旧容器
   make docker-stop
   ```

### 调试模式

```bash
# 启用详细输出
nginx-manager -v status

# 查看日志
tail -f logs/nginx-manager.log
```

## 贡献指南

### 开发环境设置

```bash
# 克隆仓库
git clone <repository-url>
cd nginx-manager

# 设置开发环境
make setup-dev
source activate.sh

# 运行测试
make test
```

### 提交代码

```bash
# 格式化代码
make format

# 运行检查
make lint

# 运行测试
make test

# 提交
git commit -m "your changes"
```

## 路线图

### 已完成 ✅
- [x] 统一配置管理
- [x] 原生环境支持
- [x] 标准Python包结构
- [x] 虚拟环境支持
- [x] 分离测试环境
- [x] 精简配置文件
- [x] 简化目录结构

### 计划中 🚧
- [ ] Web界面管理
- [ ] 高级负载均衡配置
- [ ] 自动备份和恢复
- [ ] 监控和警报
- [ ] 插件系统

## 支持

如果您在使用过程中遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查 [GitHub Issues](https://github.com/yourusername/nginx-manager/issues)
3. 提交新的Issue描述问题

## 许可证

本项目使用MIT许可证。详见LICENSE文件。 