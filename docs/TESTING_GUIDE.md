# nginx-manager 测试指南

## 🚨 关于环境污染问题

您的担心是正确的！直接安装测试依赖**确实会污染全局Python环境**。为了解决这个问题，我们提供了多种环境隔离方案。

## 🛡️ 安全的测试方式

### 方式1：自动隔离环境（推荐）

```bash
# 首次使用：创建隔离的测试环境
python3 run_tests.py --setup-env

# 使用隔离环境运行测试
python3 run_tests.py --quick --use-venv
python3 run_tests.py --all --use-venv
```

### 方式2：手动虚拟环境

```bash
# 创建虚拟环境
python3 -m venv test-env

# 激活虚拟环境
source test-env/bin/activate  # Linux/macOS
# 或 
test-env\Scripts\activate     # Windows

# 安装依赖并测试
pip install -r tests/requirements.txt
python3 run_tests.py --quick
```

### 方式3：Docker完全隔离

```bash
# 使用Docker运行测试（完全隔离）
docker run --rm -v $(pwd):/app -w /app python:3.9 \
  bash -c "pip install -r tests/requirements.txt && python run_tests.py --quick"
```

## ⚠️ 环境安全检查

测试运行器会自动检查环境并发出警告：

```bash
# 检查当前环境状态
python3 run_tests.py --check-deps

# 可能的输出：
# ✅ 当前在虚拟环境中          - 安全
# ⚠️ 当前在全局Python环境中   - 会警告
# 💡 发现测试虚拟环境         - 提示使用--use-venv
```

## 🔍 避免全局污染的具体步骤

### 全新项目设置

```bash
git clone <项目地址>
cd nginx-manager

# 🔧 设置隔离环境（一次性）
python3 run_tests.py --setup-env

# 🧪 运行测试（日常使用）
python3 run_tests.py --quick --use-venv
```

### 如果已经在全局环境中

```bash
# ❌ 如果你不小心运行了这个命令：
python3 run_tests.py --install-deps

# 系统会警告并询问确认：
# ⚠️ 警告: 未检测到虚拟环境
# 是否创建隔离的测试环境? (y/N): y  ← 选择 y

# 或者你可以强制使用全局环境（不推荐）：
python3 run_tests.py --install-deps --force-global
```

## 📁 文件结构说明

项目会创建以下隔离文件：

```
nginx-manager/
├── .test-venv/           # 测试专用虚拟环境（自动创建）
├── htmlcov/              # 覆盖率报告
├── .coverage             # 覆盖率数据
└── .pytest_cache/        # pytest缓存
```

这些都已在`.gitignore`中排除，不会被提交到版本控制。

## 🧹 清理环境

如果需要重置测试环境：

```bash
# 删除测试虚拟环境
rm -rf .test-venv

# 重新创建
python3 run_tests.py --setup-env
```

## 🎯 常用命令速查

| 命令 | 说明 |
|------|------|
| `python3 run_tests.py --setup-env` | 创建隔离测试环境 |
| `python3 run_tests.py --check-deps` | 检查环境状态 |
| `python3 run_tests.py --quick --use-venv` | 快速测试（隔离环境） |
| `python3 run_tests.py --all --use-venv` | 全部测试（隔离环境） |
| `python3 run_tests.py --lint --use-venv` | 代码检查（隔离环境） |

## 💡 最佳实践

1. **总是使用隔离环境**：优先选择虚拟环境
2. **一次设置，长期使用**：运行`--setup-env`创建环境后，使用`--use-venv`参数
3. **CI/CD友好**：GitHub Actions已配置自动环境隔离
4. **团队协作**：团队成员都使用相同的隔离环境方案

## ❓ 常见问题

**Q: 为什么不默认使用虚拟环境？**  
A: 为了兼容性和用户选择权，但我们强烈推荐使用隔离环境。

**Q: `.test-venv`目录很大，能删除吗？**  
A: 可以删除，用`--setup-env`重新创建即可。

**Q: 可以使用conda环境吗？**  
A: 可以，激活conda环境后直接运行测试即可。

**Q: Docker方式有什么优势？**  
A: 完全隔离，包括操作系统层面，适合CI/CD和跨平台测试。

---

## 📧 总结

**您的担心是对的**：直接安装测试依赖会污染全局环境。

**解决方案**：我们提供了完善的环境隔离机制，包括：
- 自动虚拟环境创建
- 环境状态检查和警告
- 多种隔离方案选择
- 安全的默认行为

**推荐用法**：
```bash
python3 run_tests.py --setup-env     # 一次性设置
python3 run_tests.py --quick --use-venv  # 日常测试
```

这样就能安全地运行测试，完全避免全局环境污染！ 