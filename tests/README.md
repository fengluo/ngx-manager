# 测试文档

## 概述

本项目包含全面的测试套件，覆盖单元测试、集成测试和端到端测试。测试确保nginx-manager的所有功能都能正常工作。

## 环境设置

### 快速开始

推荐使用虚拟环境来隔离测试依赖：

```bash
# 1. 创建虚拟环境
python3 -m venv .venv

# 2. 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 3. 安装开发依赖（包含测试工具）
pip install -r requirements-dev.txt

# 4. 运行测试
pytest tests/
```

### 依赖管理

项目使用统一的requirements文件管理：

- **`requirements.txt`** - 生产环境依赖
- **`requirements-dev.txt`** - 开发环境依赖（包含测试工具）

测试所需的所有依赖都包含在 `requirements-dev.txt` 中，不需要单独的测试requirements文件。

### Docker环境测试

如果需要在完全隔离的环境中测试：

```bash
# 使用Docker运行测试
docker run --rm -v $(pwd):/app -w /app python:3.9 \
  bash -c "pip install -r requirements-dev.txt && pytest tests/"
```

## 测试结构

```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                 # pytest配置和通用fixtures
├── README.md                   # 测试文档（本文件）
├── fixtures/                   # 测试数据
│   ├── __init__.py
│   └── sample_configs.py       # 示例配置数据
├── unit/                       # 单元测试
│   ├── __init__.py
│   ├── test_cli.py             # CLI测试
│   ├── test_nginx_manager.py   # Nginx管理器测试
│   ├── test_ssl_manager.py     # SSL管理器测试
│   ├── test_docker_manager.py  # Docker管理器测试
│   ├── test_env_manager.py     # 环境管理器测试
│   ├── test_template_generator.py # 模板生成器测试
│   └── test_config_settings.py # 配置设置测试
├── integration/                # 集成测试
│   ├── __init__.py
│   └── test_config_generation.py # 配置生成流程测试
└── e2e/                        # 端到端测试
    ├── __init__.py
    └── test_workflows.py       # 完整工作流测试
```

## 测试类型

### 单元测试

测试单个模块和函数的功能：

```bash
# 运行所有单元测试
pytest tests/unit/

# 运行特定单元测试
pytest tests/unit/test_nginx_manager.py

# 带详细输出
pytest tests/unit/ -v

# 带覆盖率
pytest tests/unit/ --cov=nginx_manager
```

**覆盖的功能：**
- CLI命令处理
- Nginx管理器功能
- SSL证书管理
- Docker容器管理
- 环境管理
- 模板生成
- 配置设置

### 集成测试

测试多个组件之间的交互：

```bash
# 运行集成测试
pytest tests/integration/
```

**覆盖的功能：**
- 完整的配置生成工作流程
- 模板渲染与配置验证
- 配置文件格式处理

### 端到端测试

测试完整的系统工作流程：

```bash
# 运行E2E测试（需要Docker）
pytest tests/e2e/

# 跳过慢速测试
pytest tests/e2e/ -m "not slow"
```

**覆盖的功能：**
- 完整的nginx配置生成和应用
- HTTP服务响应测试
- 证书管理工作流程

## 测试标记

测试使用pytest标记进行分类：

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - 端到端测试
- `@pytest.mark.slow` - 耗时测试
- `@pytest.mark.network` - 需要网络的测试
- `@pytest.mark.docker` - 需要Docker的测试

### 运行特定标记的测试

```bash
# 运行单元测试
pytest tests/ -m unit

# 运行集成测试
pytest tests/ -m integration

# 运行E2E测试
pytest tests/ -m e2e

# 跳过慢速测试
pytest tests/ -m "not slow"

# 跳过需要Docker的测试
pytest tests/ -m "not docker"
```

## 覆盖率报告

生成测试覆盖率报告：

```bash
# 生成覆盖率报告
pytest tests/ --cov=nginx_manager --cov-report=html

# 查看报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 故障排除

### 常见问题

1. **模块导入错误**
   ```bash
   # 确保在项目根目录运行测试
   cd /path/to/nginx-manager
   pytest tests/
   ```

2. **缺少依赖**
   ```bash
   # 重新安装开发依赖
   pip install -r requirements-dev.txt
   ```

3. **Docker相关测试失败**
   ```bash
   # 跳过Docker测试
   pytest tests/ -m "not docker"
   ```

### 调试测试

```bash
# 显示详细输出
pytest tests/ -v

# 停在第一个失败
pytest tests/ -x

# 显示本地变量
pytest tests/ -l

# 进入调试器
pytest tests/ --pdb
```

## 持续集成

项目配置了GitHub Actions进行自动化测试。每次提交都会运行：

- 单元测试
- 集成测试
- 代码覆盖率检查
- 代码质量检查（linting）

本地推荐在提交前运行：

```bash
# 运行所有测试
pytest tests/

# 运行快速测试（跳过慢速测试）
pytest tests/ -m "not slow"

# 代码格式检查
black --check nginx_manager/ tests/
flake8 nginx_manager/ tests/
``` 