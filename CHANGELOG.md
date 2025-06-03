# 变更日志

## v2.0.0 - Python统一语言重构 (2024-12-19)

### 🔄 重大变更
- **统一语言**: 将所有Shell脚本重写为Python，实现语言统一
- **启动方式变更**: 使用 `python3 start.py` 替代 `./start.sh`
- **脚本重构**: 所有核心脚本都使用Python实现
- **基础镜像变更**: 将Dockerfile基础镜像从`nginx:1.25-alpine`改为`nginx`（Debian版本）

### ✨ 新增功能
- **Python启动脚本** (`start.py`): 
  - 完整的Docker容器管理功能
  - 支持构建、启动、停止、重启、日志查看等操作
  - 兼容Docker和Docker Compose两种启动方式
  - 丰富的命令行参数和帮助信息

- **Python容器启动脚本** (`scripts/entrypoint.py`):
  - 完整的容器初始化流程
  - 智能的配置文件检查和默认配置生成
  - 优雅的信号处理和服务关闭
  - 配置文件实时监控（基于watchdog）
  - 自动化的定时任务设置

- **Python证书管理脚本** (`scripts/cert_manager.py`):
  - 面向对象的证书管理架构
  - 支持多CA服务器（Let's Encrypt、ZeroSSL、Buypass）
  - 智能的证书过期检查和自动续期
  - 完整的错误处理和重试机制
  - 详细的日志记录

### 🛠️ 改进优化
- **代码一致性**: 统一使用Python，提高代码可读性和维护性
- **错误处理**: 更完善的异常处理和错误恢复机制
- **日志系统**: 统一的日志格式和输出方式
- **配置验证**: 更严格的配置文件验证和默认值处理
- **模块化设计**: 各功能模块独立，便于扩展和测试
- **Nginx兼容性**: 修复HTTP/2语法以兼容新版本nginx，解决SSL共享内存区域冲突
- **包管理优化**: 使用系统包管理器安装Python依赖，避免pip环境管理问题

### 🗑️ 移除内容
- 删除 `start.sh` (Shell启动脚本)
- 删除 `scripts/entrypoint.sh` (Shell容器启动脚本)
- 删除 `scripts/cert-manager.sh` (Shell证书管理脚本)

### 📝 文档更新
- 更新 `README.md` 以反映Python统一语言的变化
- 更新启动命令和使用示例
- 更新项目结构说明
- 添加技术架构说明

### 🔧 技术细节
- **依赖管理**: 在Dockerfile中添加了dcron支持定时任务
- **权限设置**: 所有Python脚本都设置了执行权限
- **兼容性**: 保持与原有配置文件格式的完全兼容
- **性能**: Python脚本在功能丰富的同时保持良好的性能
- **基础镜像**: 从Alpine Linux改为Debian，提供更好的Python生态支持
- **HTTP/2支持**: 更新nginx模板以支持新版本的HTTP/2语法（`http2 on`）
- **SSL配置**: 为每个虚拟主机使用独立的SSL共享内存区域，避免冲突

### 📋 迁移指南
如果您正在使用v1.x版本，请按以下步骤迁移：

1. **更新启动方式**:
   ```bash
   # 旧方式
   ./start.sh
   
   # 新方式
   python3 start.py
   ```

2. **更新手动操作命令**:
   ```bash
   # 旧方式
   docker exec nginx-manager /app/scripts/cert-manager.sh --list
   
   # 新方式
   docker exec nginx-manager python3 /app/scripts/cert_manager.py --list
   ```

3. **配置文件**: 无需修改，完全兼容现有配置

4. **Docker映射**: 无需修改，目录映射保持不变

5. **重新构建镜像**: 由于基础镜像变更，需要重新构建Docker镜像

### 🎯 下一步计划
- [ ] 添加Web管理界面
- [ ] 支持配置文件热重载
- [ ] 添加监控和告警功能
- [ ] 支持更多SSL证书提供商
- [ ] 添加配置文件模板库

---

## v1.0.0 - 初始版本 (2024-12-18)

### ✨ 初始功能
- 基于YAML的虚拟主机配置
- 自动SSL证书申请和管理
- Docker容器化部署
- 基于路径的代理和静态文件配置
- 配置文件映射和调试支持 