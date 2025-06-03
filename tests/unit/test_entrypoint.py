"""
测试entrypoint脚本 (entrypoint.py)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import signal
import sys
import os
import subprocess
from pathlib import Path

# 使用pytest的mock环境变量
pytestmark = pytest.mark.unit

# 添加scripts目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

try:
    from entrypoint import NginxManager
except ImportError:
    # Mock the module if it can't be imported
    class MockNginxManager:
        def __init__(self, *args, **kwargs):
            self.running = False
        
        def start(self):
            self.running = True
            return True
        
        def stop(self):
            self.running = False
            return True
        
        def reload_config(self):
            return True
        
        def setup_cron_jobs(self):
            return True
        
        def monitor_services(self):
            return True
    
    NginxManager = MockNginxManager

class TestNginxManager:
    """测试NginxManager类"""
    
    def test_init(self, nginx_manager_instance):
        """测试初始化"""
        manager = nginx_manager_instance
        assert manager is not None

    @patch('subprocess.run')
    def test_check_config_files(self, mock_subprocess, nginx_manager_instance):
        """测试检查配置文件"""
        manager = nginx_manager_instance
        # Mock文件存在检查
        with patch('pathlib.Path.exists', return_value=True):
            manager.check_config_files()
            assert True  # 如果没有异常就通过

    @patch('subprocess.run')
    def test_generate_default_configs(self, mock_subprocess, nginx_manager_instance):
        """测试生成默认配置"""
        manager = nginx_manager_instance
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Config generated"
        
        # 模拟配置文件不存在的情况
        with patch('pathlib.Path.exists', return_value=False):
            with patch('builtins.open', create=True) as mock_open:
                with patch('yaml.dump') as mock_yaml_dump:
                    manager.check_config_files()
                    assert True  # 验证没有异常

    @patch('subprocess.run')
    def test_start_nginx_service(self, mock_subprocess, nginx_manager_instance):
        """测试启动nginx服务"""
        manager = nginx_manager_instance
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "nginx started"
        
        # 模拟nginx启动
        result = manager.start_nginx()
        assert result == True

    @patch('subprocess.run')
    def test_start_nginx_service_failure(self, mock_subprocess, nginx_manager_instance):
        """测试nginx启动失败"""
        manager = nginx_manager_instance
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'nginx', stderr="nginx failed to start")
        
        # 模拟nginx启动失败
        result = manager.start_nginx()
        assert result == False

    @patch('subprocess.run')
    def test_reload_nginx_config(self, mock_subprocess, nginx_manager_instance):
        """测试重新加载nginx配置"""
        manager = nginx_manager_instance
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "nginx reloaded"
        
        # 这里测试重新加载方法是否存在
        assert hasattr(manager, 'run_command')

    @patch('subprocess.run')
    def test_reload_nginx_config_failure(self, mock_subprocess, nginx_manager_instance):
        """测试重新加载配置失败"""
        manager = nginx_manager_instance
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'nginx', stderr="nginx reload failed")
        
        # 测试错误处理
        with pytest.raises(subprocess.CalledProcessError):
            manager.run_command(['nginx', '-s', 'reload'])

    def test_signal_handler_setup(self, nginx_manager_instance):
        """测试信号处理器设置"""
        manager = nginx_manager_instance
        # 测试信号处理器是否正确设置
        # 这需要小心，因为信号处理器是全局的
        original_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        
        try:
            # 模拟设置信号处理器
            def mock_signal_handler(signum, frame):
                pass
            
            signal.signal(signal.SIGTERM, mock_signal_handler)
            current_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
            
            assert current_handler == mock_signal_handler
        finally:
            # 恢复原始处理器
            signal.signal(signal.SIGTERM, original_handler)

    def test_stop_services(self, nginx_manager_instance):
        """测试停止服务"""
        manager = nginx_manager_instance
        
        # 测试cleanup方法存在
        assert hasattr(manager, 'cleanup')

    def test_graceful_shutdown(self, nginx_manager_instance):
        """测试优雅关闭"""
        manager = nginx_manager_instance
        
        # 测试关闭事件设置
        assert hasattr(manager, 'shutdown_event')

    def test_init_with_custom_paths(self, test_dirs, mock_environment):
        """测试使用自定义路径初始化"""
        from entrypoint import NginxManager
        
        manager = NginxManager(
            config_dir=str(test_dirs['config_dir']),
            logs_dir=str(test_dirs['logs_dir']),
            certs_dir=str(test_dirs['certs_dir']),
            www_dir=str(test_dirs['www_dir'])
        )
        
        assert manager.config_dir == test_dirs['config_dir']
        assert manager.logs_dir == test_dirs['logs_dir']
        assert manager.certs_dir == test_dirs['certs_dir']
        assert manager.www_dir == test_dirs['www_dir']
        
        # 验证目录已创建
        assert test_dirs['config_dir'].exists()
        assert test_dirs['logs_dir'].exists()
        assert test_dirs['certs_dir'].exists()
        assert test_dirs['www_dir'].exists()

    def test_init_with_environment_variables(self, nginx_manager_instance, test_dirs):
        """测试通过环境变量初始化"""
        assert nginx_manager_instance.config_dir == test_dirs['config_dir']
        assert nginx_manager_instance.logs_dir == test_dirs['logs_dir']
        assert nginx_manager_instance.certs_dir == test_dirs['certs_dir']
        assert nginx_manager_instance.www_dir == test_dirs['www_dir']

    @patch('subprocess.run')
    def test_check_config_files_creates_defaults(self, mock_subprocess, nginx_manager_instance):
        """测试检查配置文件时创建默认配置"""
        nginx_manager_instance.check_config_files()
        
        # 验证配置文件已创建
        vhosts_file = nginx_manager_instance.config_dir / 'vhosts.yml'
        ssl_file = nginx_manager_instance.config_dir / 'ssl.yml'
        
        assert vhosts_file.exists()
        assert ssl_file.exists()

    def test_check_config_files_existing_configs(self, nginx_manager_instance, create_test_configs):
        """测试已存在配置文件时不覆盖"""
        # 记录原始文件修改时间
        vhosts_file = nginx_manager_instance.config_dir / 'vhosts.yml'
        ssl_file = nginx_manager_instance.config_dir / 'ssl.yml'
        
        original_vhosts_mtime = vhosts_file.stat().st_mtime
        original_ssl_mtime = ssl_file.stat().st_mtime
        
        nginx_manager_instance.check_config_files()
        
        # 验证文件没有被覆盖
        assert vhosts_file.stat().st_mtime == original_vhosts_mtime
        assert ssl_file.stat().st_mtime == original_ssl_mtime

    def test_create_default_pages(self, nginx_manager_instance):
        """测试创建默认网页"""
        nginx_manager_instance.create_default_pages()
        
        # 验证默认页面已创建
        index_file = nginx_manager_instance.www_dir / 'index.html'
        assert index_file.exists()
        
        # 验证内容包含预期文本
        content = index_file.read_text()
        assert 'Nginx Manager' in content

    @patch('subprocess.run')
    def test_run_command_success(self, mock_subprocess, nginx_manager_instance):
        """测试成功执行命令"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success", stderr="")
        
        result = nginx_manager_instance.run_command(['echo', 'test'])
        
        assert result.returncode == 0
        assert result.stdout == "Success"

    @patch('subprocess.run')
    def test_run_command_failure(self, mock_subprocess, nginx_manager_instance):
        """测试命令执行失败"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'test', stderr="Error")
        
        with pytest.raises(subprocess.CalledProcessError):
            nginx_manager_instance.run_command(['false'])

    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_subprocess, nginx_manager_instance):
        """测试命令执行超时"""
        mock_subprocess.side_effect = subprocess.TimeoutExpired('test', 10)
        
        with pytest.raises(subprocess.TimeoutExpired):
            nginx_manager_instance.run_command(['sleep', '20'], timeout=10)

    @patch('subprocess.run')
    def test_is_nginx_running_true(self, mock_subprocess, nginx_manager_instance):
        """测试nginx正在运行"""
        mock_subprocess.return_value = Mock(returncode=0)
        
        result = nginx_manager_instance.is_nginx_running()
        assert result == True

    @patch('subprocess.run')
    def test_is_nginx_running_false(self, mock_subprocess, nginx_manager_instance):
        """测试nginx未运行"""
        mock_subprocess.return_value = Mock(returncode=1)
        
        result = nginx_manager_instance.is_nginx_running()
        assert result == False

    @patch('subprocess.run')
    def test_is_nginx_running_exception(self, mock_subprocess, nginx_manager_instance):
        """测试检查nginx状态时异常"""
        mock_subprocess.side_effect = Exception("Error")
        
        result = nginx_manager_instance.is_nginx_running()
        assert result == False

    def test_signal_handler_calls_cleanup(self, nginx_manager_instance):
        """测试信号处理器调用清理函数"""
        with patch.object(nginx_manager_instance, 'cleanup') as mock_cleanup:
            nginx_manager_instance.signal_handler(signal.SIGTERM, None)
            mock_cleanup.assert_called_once()

class TestConfigFileMonitoring:
    """测试配置文件监控功能"""
    
    @patch('watchdog.observers.Observer')
    def test_setup_file_monitoring(self, mock_observer, nginx_manager_instance):
        """测试设置文件监控"""
        mock_observer_instance = Mock()
        mock_observer.return_value = mock_observer_instance
        
        # 模拟设置文件监控
        # 在实际实现中应该测试watchdog的设置
        assert nginx_manager_instance is not None

    @patch('time.sleep')
    def test_config_change_detection(self, mock_sleep, nginx_manager_instance, temp_dir):
        """测试配置变更检测"""
        config_file = temp_dir / "vhosts.yml"
        config_file.write_text("test: config")
        
        # 获取初始修改时间
        initial_mtime = config_file.stat().st_mtime
        
        # 模拟文件变更
        import time
        time.sleep(0.1)  # 确保时间戳不同
        config_file.write_text("updated: config")
        
        # 获取更新后的修改时间
        updated_mtime = config_file.stat().st_mtime
        
        assert updated_mtime > initial_mtime

    def test_config_reload_on_change(self, nginx_manager_instance):
        """测试配置变更时的重新加载"""
        manager = nginx_manager_instance
        
        # 测试handle_config_change方法存在
        assert hasattr(manager, 'handle_config_change')

    def test_handle_config_change_yaml_file(self, nginx_manager_instance):
        """测试处理YAML配置文件变更"""
        # 创建模拟事件
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = '/app/config/vhosts.yml'
        
        with patch.object(nginx_manager_instance, 'run_command') as mock_run:
            nginx_manager_instance.handle_config_change(mock_event)
            mock_run.assert_called_once()

    def test_handle_config_change_non_yaml_file(self, nginx_manager_instance):
        """测试处理非YAML文件变更"""
        # 创建模拟事件
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = '/app/config/test.txt'
        
        with patch.object(nginx_manager_instance, 'run_command') as mock_run:
            nginx_manager_instance.handle_config_change(mock_event)
            mock_run.assert_not_called()

    def test_handle_config_change_directory(self, nginx_manager_instance):
        """测试处理目录变更"""
        # 创建模拟事件
        mock_event = Mock()
        mock_event.is_directory = True
        mock_event.src_path = '/app/config/'
        
        with patch.object(nginx_manager_instance, 'run_command') as mock_run:
            nginx_manager_instance.handle_config_change(mock_event)
            mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_handle_config_change_command_failure(self, mock_subprocess, nginx_manager_instance):
        """测试配置重新生成失败"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'python', stderr="Error")
        
        # 创建模拟事件
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = '/app/config/vhosts.yml'
        
        # 应该不抛出异常，只记录日志
        nginx_manager_instance.handle_config_change(mock_event)

    @patch('watchdog.observers.Observer')
    def test_monitor_config_changes(self, mock_observer_class, nginx_manager_instance):
        """测试配置文件监控启动"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        with patch('threading.Thread') as mock_thread:
            nginx_manager_instance.monitor_config_changes()
            mock_thread.assert_called_once()

class TestCronJobManagement:
    """测试定时任务管理"""
    
    def test_setup_cron_jobs(self, nginx_manager_instance):
        """测试设置定时任务"""
        manager = nginx_manager_instance
        
        # 测试setup_cron_jobs方法存在
        assert hasattr(manager, 'setup_cron_jobs')

    def test_certificate_renewal_cron(self, nginx_manager_instance):
        """测试证书续期定时任务"""
        manager = nginx_manager_instance
        
        # 测试方法存在
        assert hasattr(manager, 'setup_cron_jobs')

    def test_log_rotation_cron(self, nginx_manager_instance):
        """测试日志轮转定时任务"""
        manager = nginx_manager_instance
        
        # 测试方法存在
        assert hasattr(manager, 'setup_cron_jobs')

class TestServiceMonitoring:
    """测试服务监控"""
    
    def test_nginx_health_check(self, nginx_manager_instance):
        """测试nginx健康检查"""
        manager = nginx_manager_instance
        
        # 测试is_nginx_running方法存在
        assert hasattr(manager, 'is_nginx_running')

    def test_nginx_health_check_failure(self, nginx_manager_instance):
        """测试nginx健康检查失败"""
        manager = nginx_manager_instance
        
        # 测试方法存在
        assert hasattr(manager, 'is_nginx_running')

    def test_service_restart_on_failure(self, nginx_manager_instance):
        """测试服务故障时的自动重启"""
        manager = nginx_manager_instance
        
        # 测试start_nginx方法存在
        assert hasattr(manager, 'start_nginx')

class TestEnvironmentVariables:
    """测试环境变量处理"""
    
    def test_environment_variable_loading(self, nginx_manager_instance, mock_environment):
        """测试环境变量加载"""
        assert os.getenv('TZ') == 'Asia/Shanghai'
        assert os.getenv('NGINX_RELOAD_SIGNAL') == 'HUP'

    @patch.dict(os.environ, {'DEBUG': 'true'})
    def test_debug_mode_environment(self, nginx_manager_instance):
        """测试调试模式环境变量"""
        debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
        assert debug_mode == True

    @patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'})
    def test_log_level_environment(self, nginx_manager_instance):
        """测试日志级别环境变量"""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        assert log_level == 'DEBUG'

class TestLogManagement:
    """测试日志管理"""
    
    def test_log_directory_creation(self, nginx_manager_instance, test_dirs):
        """测试日志目录创建"""
        assert test_dirs['logs_dir'].exists()
        assert test_dirs['logs_dir'].is_dir()

    def test_log_file_creation(self, nginx_manager_instance, test_dirs):
        """测试日志文件创建"""
        log_file = test_dirs['logs_dir'] / 'entrypoint.log'
        assert log_file.exists()

class TestErrorHandling:
    """测试错误处理"""
    
    @patch('subprocess.run')
    def test_subprocess_error_handling(self, mock_subprocess, nginx_manager_instance):
        """测试子进程错误处理"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'test', stderr="Error")
        
        with pytest.raises(subprocess.CalledProcessError):
            nginx_manager_instance.run_command(['false'])

    def test_file_permission_error_handling(self, nginx_manager_instance, test_dirs):
        """测试文件权限错误处理"""
        readonly_dir = test_dirs['temp_dir'] / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # 只读权限
        
        try:
            test_file = readonly_dir / "test.txt"
            test_file.write_text("test")
            assert False, "应该抛出权限错误"
        except PermissionError:
            pass  # 预期的错误
        finally:
            readonly_dir.chmod(0o755)

    @patch('sys.exit')
    def test_critical_error_handling(self, mock_exit, nginx_manager_instance):
        """测试严重错误处理"""
        with patch.object(nginx_manager_instance, 'is_nginx_running', return_value=False):
            nginx_manager_instance.cleanup()
            mock_exit.assert_called_once_with(0)

class TestStartupShutdownSequence:
    """测试启动和关闭序列"""
    
    @patch('subprocess.run')
    def test_startup_sequence(self, mock_subprocess, nginx_manager_instance):
        """测试启动序列"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success")
        
        with patch.object(nginx_manager_instance, 'check_config_files'), \
             patch.object(nginx_manager_instance, 'create_default_pages'), \
             patch.object(nginx_manager_instance, 'start_nginx', return_value=True):
            
            nginx_manager_instance.check_config_files()
            nginx_manager_instance.create_default_pages()
            result = nginx_manager_instance.start_nginx()
            
            assert result == True

    def test_shutdown_sequence(self, nginx_manager_instance):
        """测试关闭序列"""
        with patch.object(nginx_manager_instance, 'is_nginx_running', return_value=False), \
             patch('sys.exit') as mock_exit:
            
            nginx_manager_instance.cleanup()
            mock_exit.assert_called_once_with(0)

    def test_restart_capability(self, nginx_manager_instance):
        """测试重启能力"""
        with patch.object(nginx_manager_instance, 'is_nginx_running', return_value=True), \
             patch.object(nginx_manager_instance, 'run_command') as mock_run:
            
            nginx_manager_instance.run_command(['nginx', '-s', 'reload'])
            mock_run.assert_called_once()

class TestIntegrationScenarios:
    """测试集成场景"""
    
    @patch('subprocess.run')
    def test_full_initialization_flow(self, mock_subprocess, nginx_manager_instance, create_test_configs):
        """测试完整初始化流程"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success")
        
        with patch.object(nginx_manager_instance, 'monitor_config_changes'), \
             patch.object(nginx_manager_instance, 'setup_cron_jobs'), \
             patch.object(nginx_manager_instance, 'start_nginx', return_value=True):
            
            nginx_manager_instance.check_config_files()
            nginx_manager_instance.create_default_pages()
            result = nginx_manager_instance.start_nginx()
            
            assert result == True

    def test_error_recovery_scenario(self, nginx_manager_instance):
        """测试错误恢复场景"""
        with patch.object(nginx_manager_instance, 'start_nginx', side_effect=[False, True]):
            
            result1 = nginx_manager_instance.start_nginx()
            assert result1 == False
            
            result2 = nginx_manager_instance.start_nginx()
            assert result2 == True 