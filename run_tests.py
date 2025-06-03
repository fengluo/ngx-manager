#!/usr/bin/env python3
"""
测试运行脚本
提供不同级别和类型的测试运行选项
支持虚拟环境隔离，避免污染全局Python环境
"""

import argparse
import subprocess
import sys
import os
import venv
from pathlib import Path
import tempfile
import shutil
from typing import List, Optional

def is_in_virtual_env():
    """检查是否在虚拟环境中"""
    return (hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))

def create_test_venv():
    """创建测试专用虚拟环境"""
    venv_path = Path(".test-venv")
    
    if venv_path.exists():
        print(f"📁 测试虚拟环境已存在: {venv_path}")
        return venv_path
    
    print(f"🔧 创建测试虚拟环境: {venv_path}")
    try:
        venv.create(venv_path, with_pip=True)
        print(f"✅ 虚拟环境创建成功: {venv_path}")
        return venv_path
    except Exception as e:
        print(f"❌ 创建虚拟环境失败: {e}")
        return None

def get_venv_python(venv_path):
    """获取虚拟环境中的Python解释器路径"""
    if os.name == 'nt':  # Windows
        return venv_path / "Scripts" / "python.exe"
    else:  # Unix/Linux/macOS
        return venv_path / "bin" / "python"

def run_command(cmd, description="", use_venv=None):
    """运行命令并处理结果"""
    if description:
        print(f"\n{'='*60}")
        print(f"🔍 {description}")
        print(f"{'='*60}")
    
    # 如果指定了虚拟环境，替换Python解释器路径
    if use_venv and cmd[0] == sys.executable:
        venv_python = get_venv_python(use_venv)
        if venv_python.exists():
            cmd[0] = str(venv_python)
            print(f"🔧 使用虚拟环境Python: {venv_python}")
    
    print(f"💻 执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=False, text=True, capture_output=True)
        
        if result.stdout:
            print("📋 输出:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ 错误:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description or '命令'} 成功完成")
        else:
            print(f"❌ {description or '命令'} 失败 (退出码: {result.returncode})")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"💥 执行失败: {e}")
        return False

def install_dependencies(use_isolated_env=True):
    """安装测试依赖"""
    requirements_file = Path("tests/requirements.txt")
    if not requirements_file.exists():
        print("⚠️ 测试依赖文件不存在: tests/requirements.txt")
        return False
    
    venv_path = None
    
    # 检查当前环境状态
    if not is_in_virtual_env() and use_isolated_env:
        print("\n⚠️ 警告: 未检测到虚拟环境")
        
        response = input("是否创建隔离的测试环境? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            venv_path = create_test_venv()
            if not venv_path:
                print("❌ 无法创建虚拟环境，将安装到当前环境")
        else:
            print("⚠️ 将安装到当前Python环境（可能会污染全局环境）")
            confirm = input("确认继续? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ 用户取消安装")
                return False
    
    # 构建安装命令
    if venv_path:
        python_exe = get_venv_python(venv_path)
        cmd = [str(python_exe), "-m", "pip", "install", "-r", str(requirements_file)]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
    
    success = run_command(cmd, "安装测试依赖")
    
    if success and venv_path:
        print(f"\n📝 要使用测试环境，请运行:")
        if os.name == 'nt':
            print(f"   .test-venv\\Scripts\\activate")
        else:
            print(f"   source .test-venv/bin/activate")
        print(f"   或者使用 --use-venv 参数")
    
    return success

def setup_isolated_environment():
    """设置隔离的测试环境"""
    if is_in_virtual_env():
        print("✅ 已在虚拟环境中")
        return True
    
    venv_path = create_test_venv()
    if not venv_path:
        return False
    
    # 安装基础依赖
    python_exe = get_venv_python(venv_path)
    
    # 升级pip
    cmd = [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"]
    if not run_command(cmd, "升级pip"):
        return False
    
    # 安装测试依赖
    requirements_file = Path("tests/requirements.txt")
    if requirements_file.exists():
        cmd = [str(python_exe), "-m", "pip", "install", "-r", str(requirements_file)]
        if not run_command(cmd, "安装测试依赖"):
            return False
    
    print(f"\n🎉 隔离测试环境设置完成！")
    print(f"📁 环境路径: {venv_path.absolute()}")
    
    return True

def run_unit_tests(verbose=False, coverage=True, use_venv=None):
    """运行单元测试"""
    cmd = [sys.executable, "-m", "pytest", "tests/unit/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=scripts", "--cov=start", "--cov-report=term-missing"])
    
    cmd.append("-m")
    cmd.append("unit")
    
    return run_command(cmd, "运行单元测试", use_venv=use_venv)

def run_integration_tests(verbose=False, use_venv=None):
    """运行集成测试"""
    cmd = [sys.executable, "-m", "pytest", "tests/integration/"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.append("-m")
    cmd.append("integration")
    
    return run_command(cmd, "运行集成测试", use_venv=use_venv)

def run_e2e_tests(verbose=False, skip_slow=False, use_venv=None):
    """运行端到端测试"""
    cmd = [sys.executable, "-m", "pytest", "tests/e2e/"]
    
    if verbose:
        cmd.append("-v")
    
    if skip_slow:
        cmd.extend(["-m", "e2e and not slow"])
    else:
        cmd.extend(["-m", "e2e"])
    
    return run_command(cmd, "运行端到端测试", use_venv=use_venv)

def run_all_tests(verbose=False, skip_slow=False, coverage=True, use_venv=None):
    """运行所有测试"""
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    if skip_slow:
        cmd.extend(["-m", "not slow"])
    
    if coverage:
        cmd.extend([
            "--cov=scripts", 
            "--cov=start", 
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    return run_command(cmd, "运行所有测试", use_venv=use_venv)

def run_specific_test(test_path, verbose=False, use_venv=None):
    """运行特定测试"""
    cmd = [sys.executable, "-m", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, f"运行特定测试: {test_path}", use_venv=use_venv)

def lint_code(use_venv=None):
    """代码检查"""
    success = True
    
    # 检查是否安装了flake8
    try:
        subprocess.run([sys.executable, "-m", "flake8", "--version"], 
                      check=True, capture_output=True)
        
        cmd = [sys.executable, "-m", "flake8", "scripts/", "start.py", "tests/"]
        if not run_command(cmd, "代码风格检查 (flake8)", use_venv=use_venv):
            success = False
    except subprocess.CalledProcessError:
        print("⚠️ flake8 未安装，跳过代码风格检查")
    
    # 检查是否安装了mypy
    try:
        subprocess.run([sys.executable, "-m", "mypy", "--version"], 
                      check=True, capture_output=True)
        
        cmd = [sys.executable, "-m", "mypy", "scripts/", "start.py"]
        if not run_command(cmd, "类型检查 (mypy)", use_venv=use_venv):
            success = False
    except subprocess.CalledProcessError:
        print("⚠️ mypy 未安装，跳过类型检查")
    
    return success

def check_dependencies():
    """检查依赖是否满足"""
    print("\n🔍 检查测试环境...")
    
    # 检查环境类型
    if is_in_virtual_env():
        print("✅ 当前在虚拟环境中")
    else:
        print("⚠️ 当前在全局Python环境中")
        if Path(".test-venv").exists():
            print("💡 发现测试虚拟环境，建议使用 --use-venv 参数")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查pytest是否可用
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                              check=True, capture_output=True, text=True)
        print(f"✅ {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        print("❌ pytest 未安装")
        return False
    
    # 检查项目结构
    required_dirs = ["tests", "scripts"]
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            print(f"❌ 缺少目录: {dir_name}")
            return False
        print(f"✅ 目录存在: {dir_name}")
    
    return True

def generate_coverage_report(use_venv=None):
    """生成覆盖率报告"""
    print("\n📊 生成详细覆盖率报告...")
    
    # HTML报告
    cmd = [sys.executable, "-m", "coverage", "html"]
    if run_command(cmd, "生成HTML覆盖率报告", use_venv=use_venv):
        print("📄 HTML报告已生成: htmlcov/index.html")
    
    # XML报告
    cmd = [sys.executable, "-m", "coverage", "xml"]
    if run_command(cmd, "生成XML覆盖率报告", use_venv=use_venv):
        print("📄 XML报告已生成: coverage.xml")

def print_banner(text: str, color: str = "blue"):
    """打印彩色横幅"""
    colors = {
        "blue": "\033[94m",
        "green": "\033[92m", 
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "reset": "\033[0m"
    }
    
    color_code = colors.get(color, colors["blue"])
    reset_code = colors["reset"]
    
    print(f"\n{color_code}============================================================")
    print(f"🔍 {text}")
    print(f"============================================================{reset_code}")

def check_docker_available() -> bool:
    """检查Docker是否可用"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def build_docker_image(tag: str = "nginx-manager:test") -> bool:
    """构建Docker镜像用于测试"""
    print_banner(f"构建Docker镜像: {tag}", "cyan")
    
    if not check_docker_available():
        print("❌ Docker不可用，跳过镜像构建")
        return False
    
    try:
        # 构建镜像
        print(f"🔧 构建镜像: {tag}")
        result = subprocess.run([
            'docker', 'build', 
            '-t', tag,
            '-f', 'Dockerfile',
            '.'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Docker镜像构建成功: {tag}")
            return True
        else:
            print(f"❌ Docker镜像构建失败:")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Docker镜像构建超时")
        return False
    except Exception as e:
        print(f"❌ Docker镜像构建出错: {e}")
        return False

def check_environment_safety(args):
    """检查环境安全性"""
    if args.force_global:
        print("⚠️ 强制使用全局环境")
        return
    
    if not is_in_virtual_env() and not args.use_venv:
        print("\n⚠️ 警告: 将在全局Python环境中运行测试")
        if Path(".test-venv").exists():
            print("💡 建议使用 --use-venv 参数使用隔离环境")
        else:
            print("💡 建议先运行 --setup-env 创建隔离环境")
        
        confirm = input("继续使用全局环境? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ 用户取消，请使用 --setup-env 或 --use-venv")
            sys.exit(1)

def setup_test_environment(args):
    """设置测试环境并返回Python命令"""
    if args.setup_env:
        if setup_isolated_environment():
            print("✅ 测试环境设置完成")
            sys.exit(0)
        else:
            print("❌ 测试环境设置失败")
            sys.exit(1)
    
    if args.use_venv:
        venv_path = Path(".test-venv")
        if not venv_path.exists():
            print("❌ 测试虚拟环境不存在，请先运行 --setup-env")
            sys.exit(1)
        return str(venv_path / "bin" / "python")
    
    return sys.executable

def run_tests_with_retry(pytest_cmd, args, max_retries=1):
    """运行测试，支持重试"""
    # 确定测试类型标题
    if args.unit:
        test_type = "单元测试"
    elif args.integration:
        test_type = "集成测试"
    elif args.e2e:
        test_type = "端到端测试"
    elif args.all:
        test_type = "所有测试"
    else:
        test_type = "测试"
    
    print_banner(f"运行{test_type}")
    
    # 显示要执行的命令
    if args.use_venv:
        print(f"🔧 使用虚拟环境Python: .test-venv/bin/python")
    else:
        print(f"🔧 使用Python: {sys.executable}")
    
    # 构建完整的pytest命令
    cmd = [pytest_cmd[0], '-m', 'pytest'] + pytest_cmd[1:]
    print(f"💻 执行命令: {' '.join(cmd)}")
    
    for attempt in range(max_retries + 1):
        try:
            print("📋 输出:")
            result = subprocess.run(cmd, text=True)
            
            if result.returncode == 0:
                print(f"\n✅ 运行{test_type} 成功完成")
                return True
            else:
                if attempt < max_retries:
                    print(f"\n⚠️ 尝试 {attempt + 1} 失败，正在重试...")
                else:
                    print(f"\n❌ 运行{test_type} 失败 (退出码: {result.returncode})")
                    return False
                    
        except KeyboardInterrupt:
            print(f"\n❌ 用户中断了{test_type}")
            return False
        except Exception as e:
            print(f"\n❌ 运行{test_type}时出错: {e}")
            return False
    
    return False

def print_final_success(args):
    """打印最终成功信息"""
    print_banner("测试完成", "green")
    print("🎉 所有测试成功完成！")
    
    # 提供覆盖率报告提示
    if args.coverage or args.html_cov:
        print("\n📊 覆盖率报告:")
        if args.html_cov and Path("htmlcov/index.html").exists():
            print("📄 HTML报告已生成: htmlcov/index.html")
        if args.xml_cov and Path("coverage.xml").exists():
            print("📄 XML报告已生成: coverage.xml")

def print_final_failure(args):
    """打印最终失败信息"""
    print_banner("测试失败", "red")
    print("💥 部分测试失败！")
    print("\n🔧 调试建议:")
    print("   1. 查看上面的错误信息")
    print("   2. 使用 -v 参数获取详细输出")
    print("   3. 单独运行失败的测试文件")

def main():
    parser = argparse.ArgumentParser(description="nginx-manager 测试运行器")
    
    # 测试类型选项
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument('--unit', action='store_true', help='仅运行单元测试')
    test_group.add_argument('--integration', action='store_true', help='仅运行集成测试')
    test_group.add_argument('--e2e', action='store_true', help='仅运行端到端测试')
    test_group.add_argument('--all', action='store_true', help='运行所有测试')
    
    # 环境选项
    env_group = parser.add_mutually_exclusive_group()
    env_group.add_argument('--setup-env', action='store_true', help='设置测试环境后运行')
    env_group.add_argument('--use-venv', action='store_true', help='使用虚拟环境运行测试')
    env_group.add_argument('--force-global', action='store_true', help='强制使用全局环境')
    
    # 其他选项
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--html-cov', action='store_true', help='生成HTML覆盖率报告')
    parser.add_argument('--xml-cov', action='store_true', help='生成XML覆盖率报告')
    parser.add_argument('--no-docker-build', action='store_true', help='跳过Docker镜像构建')
    
    args = parser.parse_args()
    
    # 默认运行单元测试
    if not any([args.unit, args.integration, args.e2e, args.all]):
        args.unit = True
    
    # 检查环境安全性
    check_environment_safety(args)
    
    # 设置测试环境
    python_cmd = setup_test_environment(args)
    
    # 构建Docker镜像（如果需要E2E测试且未跳过）
    docker_build_success = True
    if (args.e2e or args.all) and not args.no_docker_build:
        docker_build_success = build_docker_image()
        if not docker_build_success:
            print("⚠️ Docker镜像构建失败，E2E测试可能会失败")
    
    # 构建pytest命令
    test_paths = []
    markers = []
    
    if args.unit:
        test_paths.append('tests/unit/')
        markers.append('unit')
    if args.integration:
        test_paths.append('tests/integration/')
        markers.append('integration')
    if args.e2e:
        test_paths.append('tests/e2e/')
        markers.append('e2e')
    if args.all:
        test_paths = ['tests/']
    
    if not test_paths:
        test_paths = ['tests/unit/']  # 默认单元测试
    
    # 构建pytest命令
    pytest_cmd = [python_cmd] + test_paths
    
    if args.verbose:
        pytest_cmd.append('-v')
    
    # 添加覆盖率选项
    if args.coverage or args.html_cov or args.xml_cov:
        pytest_cmd.extend(['--cov=scripts', '--cov=start'])
        pytest_cmd.append('--cov-report=term-missing')
        
        if args.html_cov:
            pytest_cmd.append('--cov-report=html')
        if args.xml_cov:
            pytest_cmd.append('--cov-report=xml')
    
    # 添加标记过滤
    if markers and not args.all:
        marker_expr = ' or '.join(markers)
        pytest_cmd.extend(['-m', marker_expr])
    
    # 运行测试
    success = run_tests_with_retry(pytest_cmd, args)
    
    if success:
        print_final_success(args)
    else:
        print_final_failure(args)
        sys.exit(1)

if __name__ == "__main__":
    main() 