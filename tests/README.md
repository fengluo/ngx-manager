# 测试文档

## 概述

本项目包含全面的测试套件，覆盖单元测试、集成测试和端到端测试。测试确保nginx-manager的所有功能都能正常工作。

## ⚠️ 重要：环境隔离

为了避免污染全局Python环境，强烈推荐使用虚拟环境运行测试。

### 🔒 环境隔离选项

1. **自动隔离环境（推荐）**
   ```bash
   # 首次使用：创建隔离的测试环境
   python3 run_tests.py --setup-env
   
   # 运行测试（使用隔离环境）
   python3 run_tests.py --quick --use-venv
   ```

2. **手动虚拟环境**
   ```bash
   # 创建虚拟环境
   python3 -m venv test-env
   
   # 激活虚拟环境
   source test-env/bin/activate  # Linux/macOS
   # 或
   test-env\Scripts\activate     # Windows
   
   # 安装依赖并运行测试
   python3 run_tests.py --install-deps
   python3 run_tests.py --quick
   ```

3. **Docker环境（完全隔离）**
   ```bash
   # 使用Docker运行测试
   docker run --rm -v $(pwd):/app -w /app python:3.9 \
     bash -c "pip install -r tests/requirements.txt && python run_tests.py --quick"
   ```

### 🚨 环境安全检查

测试运行器会自动检查环境状态：

- ✅ **虚拟环境中** - 安全，可直接运行
- ⚠️ **全局环境中** - 会警告并询问确认
- 🔧 **存在.test-venv** - 提示使用`--use-venv`参数

### 💡 避免全局污染的最佳实践

```bash
# ❌ 不推荐：直接在全局环境安装
python3 run_tests.py --install-deps --force-global

# ✅ 推荐：使用隔离环境
python3 run_tests.py --setup-env
python3 run_tests.py --quick --use-venv

# ✅ 或者手动创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate
python3 run_tests.py --install-deps
```

## 测试结构

```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                 # pytest配置和通用fixtures
├── requirements.txt            # 测试依赖
├── README.md                   # 测试文档（本文件）
├── fixtures/                   # 测试数据
│   ├── __init__.py
│   └── sample_configs.py       # 示例配置数据
├── unit/                       # 单元测试
│   ├── __init__.py
│   ├── test_generate_config.py # 配置生成测试
│   ├── test_cert_manager.py    # 证书管理测试
│   ├── test_start.py           # 启动脚本测试
│   └── test_entrypoint.py      # 容器入口测试
├── integration/                # 集成测试
│   ├── __init__.py
│   └── test_config_generation.py # 配置生成流程测试
└── e2e/                        # 端到端测试
    ├── __init__.py
    └── test_docker_workflow.py  # Docker工作流测试
```

## 快速开始

### 1. 设置隔离环境（推荐）

```bash
# 创建并设置测试环境
python3 run_tests.py --setup-env

# 验证环境
python3 run_tests.py --check-deps
```

### 2. 运行测试

```bash
# 快速测试（使用隔离环境）
python3 run_tests.py --quick --use-venv

# 完整测试
python3 run_tests.py --all --use-venv

# 跳过慢速测试
python3 run_tests.py --all --skip-slow --use-venv
```

### 3. 传统方式（需要手动管理环境）

```bash
# 安装依赖（会提示环境选择）
python3 run_tests.py --install-deps

# 检查测试环境
python3 run_tests.py --check-deps

# 运行所有测试
python3 run_tests.py --all
```

## 测试类型

### 单元测试

测试单个模块和函数的功能：

```bash
# 运行所有单元测试（使用隔离环境）
python3 run_tests.py --unit --use-venv

# 运行特定单元测试
python3 run_tests.py --test tests/unit/test_generate_config.py --use-venv

# 带详细输出
python3 run_tests.py --unit --verbose --use-venv
```

**覆盖的功能：**
- 配置文件加载和验证
- nginx配置生成
- SSL证书管理
- Docker容器管理
- 容器入口点逻辑

### 集成测试

测试多个组件之间的交互：

```bash
# 运行集成测试
python3 run_tests.py --integration --use-venv
```

**覆盖的功能：**
- 完整的配置生成工作流程
- 模板渲染与配置验证
- 配置文件格式处理
- 配置重新加载机制

### 端到端测试

测试完整的系统工作流程：

```bash
# 运行E2E测试（需要Docker）
python3 run_tests.py --e2e --use-venv

# 跳过慢速E2E测试
python3 run_tests.py --e2e --skip-slow --use-venv
```

**覆盖的功能：**
- Docker镜像构建和启动
- 完整的nginx配置生成和应用
- HTTP服务响应测试
- 证书管理工作流程
- 容器日志和监控

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
# 只运行快速测试
pytest -m "not slow"

# 只运行需要Docker的测试
pytest -m "docker"

# 运行单元测试，排除慢速测试
pytest -m "unit and not slow"
```

## 代码覆盖率

测试包含代码覆盖率收集：

```bash
# 运行测试并生成覆盖率报告（使用隔离环境）
python3 run_tests.py --unit --coverage-report --use-venv

# 查看HTML覆盖率报告
open htmlcov/index.html
```

**覆盖率目标：**
- 总体覆盖率 ≥ 80%
- 核心模块覆盖率 ≥ 90%

## 性能测试

项目包含性能测试来确保配置生成的效率：

```bash
# 运行性能测试
pytest tests/ --benchmark-only

# 生成性能报告
pytest tests/ --benchmark-json=benchmark.json
```

## 测试数据

测试使用`tests/fixtures/sample_configs.py`中定义的示例数据：

- `SIMPLE_STATIC_CONFIG` - 简单静态站点
- `SIMPLE_PROXY_CONFIG` - 简单代理配置
- `COMPLEX_CONFIG` - 复杂多location配置
- `MICROSERVICES_CONFIG` - 微服务配置
- `INVALID_CONFIGS` - 无效配置（错误测试）

## CI/CD集成

项目使用GitHub Actions进行持续集成：

- **代码检查** - flake8, mypy, black, isort
- **多版本测试** - Python 3.8-3.11
- **Docker测试** - 镜像构建和功能测试
- **安全扫描** - safety, bandit
- **覆盖率报告** - 上传到Codecov

## 本地开发

### 运行特定测试

```bash
# 测试特定文件
python3 run_tests.py --test tests/unit/test_generate_config.py --use-venv

# 测试特定类（直接使用pytest）
source .test-venv/bin/activate  # 激活隔离环境
pytest tests/unit/test_generate_config.py::TestNginxConfigGenerator

# 测试特定方法
pytest tests/unit/test_generate_config.py::TestNginxConfigGenerator::test_init_with_valid_configs
```

### 调试测试

```bash
# 详细输出
python3 run_tests.py --unit --verbose --use-venv

# 进入调试模式（需要激活虚拟环境）
source .test-venv/bin/activate
pytest --pdb tests/unit/test_generate_config.py::test_specific_function

# 输出print语句
pytest -s tests/unit/test_generate_config.py
```

### 代码质量检查

```bash
# 运行代码检查（使用隔离环境）
python3 run_tests.py --lint --use-venv

# 单独运行各种检查（需要先激活环境）
source .test-venv/bin/activate
flake8 scripts/ start.py tests/
mypy scripts/ start.py --ignore-missing-imports
black --check scripts/ start.py tests/
isort --check-only scripts/ start.py tests/
```

## 环境管理命令参考

### 新项目设置

```bash
# 1. 克隆项目
git clone <项目地址>
cd nginx-manager

# 2. 设置隔离测试环境
python3 run_tests.py --setup-env

# 3. 运行快速测试验证
python3 run_tests.py --quick --use-venv
```

### 日常开发工作流

```bash
# 检查环境状态
python3 run_tests.py --check-deps

# 运行相关测试
python3 run_tests.py --unit --use-venv

# 代码提交前的完整检查
python3 run_tests.py --lint --use-venv
python3 run_tests.py --all --skip-slow --use-venv
```

### 环境重置

```bash
# 删除测试环境
rm -rf .test-venv

# 重新创建
python3 run_tests.py --setup-env
```

## 测试最佳实践

### 1. 测试命名

- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试方法：`test_*`
- 描述性命名：`test_should_generate_config_when_valid_input`

### 2. 测试结构

- **Arrange** - 设置测试数据
- **Act** - 执行被测试的操作
- **Assert** - 验证结果

### 3. Mock使用

- Mock外部依赖（文件系统、网络、子进程）
- 使用`@patch`装饰器
- 测试边界条件和错误情况

### 4. Fixtures

- 使用fixtures提供测试数据
- 共享fixtures放在`conftest.py`
- 使用适当的scope（function, class, module, session）

### 5. 环境隔离

- 优先使用虚拟环境
- 避免全局环境污染
- 使用项目提供的环境管理工具

## 故障排除

### 常见问题

1. **环境污染问题**
   ```bash
   # 创建隔离环境
   python3 run_tests.py --setup-env
   
   # 使用隔离环境运行测试
   python3 run_tests.py --quick --use-venv
   ```

2. **Docker测试失败**
   ```bash
   # 确保Docker运行
   docker version
   
   # 检查权限
   docker run hello-world
   ```

3. **依赖安装失败**
   ```bash
   # 使用隔离环境重新安装
   rm -rf .test-venv
   python3 run_tests.py --setup-env
   ```

4. **权限错误**
   ```bash
   # Linux/macOS
   chmod +x run_tests.py
   
   # Windows
   python run_tests.py --help
   ```

### 环境状态检查

```bash
# 检查当前环境
python3 run_tests.py --check-deps

# 查看详细环境信息
python3 -c "
import sys
print(f'Python: {sys.executable}')
print(f'虚拟环境: {hasattr(sys, \"real_prefix\") or (hasattr(sys, \"base_prefix\") and sys.base_prefix != sys.prefix)}')
"
```

### 获取帮助

```bash
# 查看测试运行器帮助
python3 run_tests.py --help

# 查看pytest帮助
pytest --help

# 查看可用的测试标记
pytest --markers
```

## 贡献指南

### 添加新测试

1. 确定测试类型（单元/集成/E2E）
2. 在相应目录创建测试文件
3. 使用适当的fixtures和mock
4. 添加必要的测试标记
5. 确保测试通过并提供良好的覆盖率
6. 在隔离环境中验证测试

### 测试代码规范

- 遵循项目代码风格
- 测试应该快速、可靠、独立
- 使用描述性的断言消息
- 避免在测试中使用硬编码路径
- 优先使用虚拟环境进行测试

---

## 联系信息

如有测试相关问题，请通过以下方式联系：

- 创建Issue
- 提交Pull Request
- 查看项目文档 