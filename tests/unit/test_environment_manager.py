"""
Tests for environment manager
"""

import pytest
import platform
from pathlib import Path
from unittest.mock import patch, Mock, mock_open

from nginx_manager.utils.environment import EnvironmentManager


class TestEnvironmentManager:
    """Test environment manager functionality"""
    
    def test_manager_initialization(self, environment_manager_instance):
        """Test environment manager initialization"""
        manager = environment_manager_instance
        
        assert manager.system in ['linux', 'darwin', 'windows']
        assert manager.distro is not None
    
    @patch('platform.system')
    @patch('platform.release')
    def test_platform_detection(self, mock_release, mock_system):
        """Test platform detection"""
        # Test Linux
        mock_system.return_value = 'Linux'
        mock_release.return_value = '5.4.0-42-generic'
        
        manager = EnvironmentManager()
        assert manager.system == 'linux'
        
        # Test macOS
        mock_system.return_value = 'Darwin'
        mock_release.return_value = '20.6.0'
        
        manager = EnvironmentManager()
        assert manager.system == 'darwin'
        
        # Test Windows
        mock_system.return_value = 'Windows'
        mock_release.return_value = '10'
        
        manager = EnvironmentManager()
        assert manager.system == 'windows'
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_linux_distro_detection(self, mock_read_text, mock_exists):
        """Test Linux distribution detection"""
        # Mock /etc/os-release exists
        mock_exists.return_value = True
        mock_read_text.return_value = """
NAME="Ubuntu"
VERSION="20.04.3 LTS (Focal Fossa)"
ID=ubuntu
VERSION_ID="20.04"
"""
        
        with patch('platform.system', return_value='Linux'):
            manager = EnvironmentManager()
            assert manager.distro == 'ubuntu'
        
        # Test CentOS
        mock_read_text.return_value = """
NAME="CentOS Linux"
VERSION="8 (Core)"
ID="centos"
VERSION_ID="8"
"""
        
        with patch('platform.system', return_value='Linux'):
            manager = EnvironmentManager()
            assert manager.distro == 'centos'
    
    @patch('subprocess.run')
    def test_check_environment(self, mock_run, environment_manager_instance):
        """Test environment status check"""
        manager = environment_manager_instance
        
        # Mock successful command checks
        mock_run.side_effect = [
            Mock(returncode=0, stdout='Python 3.9.0'),  # python --version
            Mock(returncode=0, stdout='nginx version: nginx/1.20.0'),  # nginx -v
            Mock(returncode=0, stdout='OpenSSL 1.1.1f'),  # openssl version
            Mock(returncode=0, stdout='curl 7.68.0'),  # curl --version
        ]
        
        status = manager.check_environment()
        
        assert 'python' in status
        assert 'nginx' in status
        assert 'openssl' in status
        assert 'curl' in status
        
        for tool in status.values():
            assert 'available' in tool
            assert tool['available'] is True
    
    @patch('subprocess.run')
    def test_check_environment_missing_tools(self, mock_run, environment_manager_instance):
        """Test environment check with missing tools"""
        manager = environment_manager_instance
        
        # Mock some tools missing
        mock_run.side_effect = [
            Mock(returncode=0, stdout='Python 3.9.0'),  # python available
            Mock(returncode=1, stderr='nginx: command not found'),  # nginx missing
            Mock(returncode=0, stdout='OpenSSL 1.1.1f'),  # openssl available
            Mock(returncode=1, stderr='curl: command not found'),  # curl missing
        ]
        
        status = manager.check_environment()
        
        assert status['python']['available'] is True
        assert status['nginx']['available'] is False
        assert status['openssl']['available'] is True
        assert status['curl']['available'] is False


class TestDependencyInstallation:
    """Test dependency installation"""
    
    @patch('subprocess.run')
    def test_install_dependencies_ubuntu(self, mock_run, environment_manager_instance):
        """Test dependency installation on Ubuntu"""
        manager = environment_manager_instance
        manager.distro = 'ubuntu'
        
        # Mock successful installation
        mock_run.return_value = Mock(returncode=0, stdout="Installation successful")
        
        result = manager.install_dependencies()
        
        assert result['success'] is True
        # Should call apt update and install
        calls = mock_run.call_args_list
        assert any('apt' in str(call) and 'update' in str(call) for call in calls)
        assert any('apt' in str(call) and 'install' in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_install_dependencies_centos(self, mock_run, environment_manager_instance):
        """Test dependency installation on CentOS"""
        manager = environment_manager_instance
        manager.distro = 'centos'
        
        # Mock successful installation
        mock_run.return_value = Mock(returncode=0, stdout="Installation successful")
        
        result = manager.install_dependencies()
        
        assert result['success'] is True
        # Should call yum or dnf install
        calls = mock_run.call_args_list
        assert any(('yum' in str(call) or 'dnf' in str(call)) and 'install' in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_install_dependencies_macos(self, mock_run, environment_manager_instance):
        """Test dependency installation on macOS"""
        manager = environment_manager_instance
        manager.system = 'darwin'
        
        # Mock brew available and successful installation
        mock_run.return_value = Mock(returncode=0, stdout="Installation successful")
        
        with patch.object(manager, '_check_command_exists', return_value=True):
            result = manager.install_dependencies()
            
            assert result['success'] is True
            # Should call brew install
            calls = mock_run.call_args_list
            assert any('brew' in str(call) and 'install' in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_install_dependencies_failure(self, mock_run, environment_manager_instance):
        """Test dependency installation failure"""
        manager = environment_manager_instance
        
        # Mock installation failure
        mock_run.return_value = Mock(returncode=1, stderr="Installation failed")
        
        result = manager.install_dependencies()
        
        assert result['success'] is False
        assert 'error' in result


class TestNginxSetup:
    """Test nginx setup functionality"""
    
    @patch('subprocess.run')
    def test_setup_nginx_success(self, mock_run, environment_manager_instance):
        """Test successful nginx setup"""
        manager = environment_manager_instance
        
        # Mock nginx config operations
        with patch('pathlib.Path.exists', return_value=True), \
             patch.object(manager, '_get_nginx_main_config_path', 
                         return_value=Path('/etc/nginx/nginx.conf')), \
             patch.object(manager, '_nginx_config_includes_our_dir', return_value=True):
            
            mock_run.return_value = Mock(returncode=0)  # nginx -t
            result = manager.setup_nginx()
            
            assert result['success'] is True
    
    @patch('subprocess.run')
    def test_setup_nginx_config_test_failure(self, mock_run, environment_manager_instance):
        """Test nginx setup with config test failure"""
        manager = environment_manager_instance
        
        # Mock nginx config test failure
        mock_run.return_value = Mock(returncode=1, stderr="nginx: configuration file test failed")
        
        with patch('pathlib.Path.exists', return_value=True):
            result = manager.setup_nginx()
            
            assert result['success'] is False
            assert 'configuration' in result['error']
    
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.exists')
    def test_nginx_config_include_detection(self, mock_exists, mock_read_text, environment_manager_instance):
        """Test nginx config include directive detection"""
        manager = environment_manager_instance
        
        # Mock nginx.conf exists
        mock_exists.return_value = True
        
        # Mock nginx.conf content with include directive
        mock_read_text.return_value = """
user nginx;
worker_processes auto;

http {
    include /etc/nginx/mime.types;
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
"""
        
        nginx_conf_path = Path('/etc/nginx/nginx.conf')
        
        # Test sites-enabled directory
        result = manager._nginx_config_includes_our_dir(nginx_conf_path, Path('/etc/nginx/sites-enabled'))
        assert result is True
        
        # Test non-included directory
        result = manager._nginx_config_includes_our_dir(nginx_conf_path, Path('/etc/nginx/servers'))
        assert result is False


class TestSSLSetup:
    """Test SSL/ACME setup functionality"""
    
    @patch('subprocess.run')
    def test_setup_ssl_acme_not_installed(self, mock_run, environment_manager_instance):
        """Test SSL setup when acme.sh is not installed"""
        manager = environment_manager_instance
        
        # Mock acme.sh not installed
        with patch.object(manager, '_check_acme_sh', return_value=False):
            mock_run.return_value = Mock(returncode=0, stdout="acme.sh installed")
            
            result = manager.setup_ssl()
            
            assert result['success'] is True
            # Should install acme.sh
            calls = mock_run.call_args_list
            assert any('acme.sh' in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_setup_ssl_acme_already_installed(self, mock_run, environment_manager_instance):
        """Test SSL setup when acme.sh is already installed"""
        manager = environment_manager_instance
        
        # Mock acme.sh already installed
        with patch.object(manager, '_check_acme_sh', return_value=True):
            result = manager.setup_ssl()
            
            assert result['success'] is True
            # Should not try to install acme.sh
            calls = mock_run.call_args_list
            assert len(calls) == 0 or not any('install' in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_setup_ssl_installation_failure(self, mock_run, environment_manager_instance):
        """Test SSL setup with installation failure"""
        manager = environment_manager_instance
        
        # Mock acme.sh installation failure
        with patch.object(manager, '_check_acme_sh', return_value=False):
            mock_run.return_value = Mock(returncode=1, stderr="Installation failed")
            
            result = manager.setup_ssl()
            
            assert result['success'] is False
            assert 'error' in result


class TestUtilityMethods:
    """Test utility methods"""
    
    @patch('subprocess.run')
    def test_check_command_exists(self, mock_run, environment_manager_instance):
        """Test command existence check"""
        manager = environment_manager_instance
        
        # Test command exists
        mock_run.return_value = Mock(returncode=0)
        assert manager._check_command_exists('nginx') is True
        
        # Test command doesn't exist
        mock_run.return_value = Mock(returncode=1)
        assert manager._check_command_exists('nonexistent') is False
    
    @patch('subprocess.run')
    def test_get_command_version(self, mock_run, environment_manager_instance):
        """Test command version extraction"""
        manager = environment_manager_instance
        
        # Test nginx version
        mock_run.return_value = Mock(returncode=0, stderr='nginx version: nginx/1.20.0')
        version = manager._get_command_version('nginx', ['-v'])
        assert version == '1.20.0'
        
        # Test python version
        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0')
        version = manager._get_command_version('python3', ['--version'])
        assert version == '3.9.0'
        
        # Test version not found
        mock_run.return_value = Mock(returncode=0, stdout='No version info')
        version = manager._get_command_version('unknown', ['--version'])
        assert version == 'unknown'
    
    @patch('pathlib.Path.exists')
    def test_check_acme_sh(self, mock_exists, environment_manager_instance):
        """Test acme.sh existence check"""
        manager = environment_manager_instance
        
        # Test acme.sh exists in common locations
        mock_exists.side_effect = lambda path: str(path) == '/usr/local/bin/acme.sh'
        assert manager._check_acme_sh() is True
        
        # Test acme.sh doesn't exist
        mock_exists.return_value = False
        assert manager._check_acme_sh() is False
    
    def test_get_nginx_main_config_path(self, environment_manager_instance):
        """Test nginx main config path detection"""
        manager = environment_manager_instance
        
        # Test different systems
        test_cases = [
            ('ubuntu', '/etc/nginx/nginx.conf'),
            ('centos', '/etc/nginx/nginx.conf'),
            ('darwin', ['/opt/homebrew/etc/nginx/nginx.conf', '/usr/local/etc/nginx/nginx.conf'])
        ]
        
        for distro, expected_paths in test_cases:
            manager.distro = distro if distro != 'darwin' else None
            manager.system = 'darwin' if distro == 'darwin' else 'linux'
            
            config_path = manager._get_nginx_main_config_path()
            
            if isinstance(expected_paths, list):
                assert str(config_path) in expected_paths
            else:
                assert str(config_path) == expected_paths


class TestEnvironmentManagerErrorHandling:
    """Test environment manager error handling"""
    
    @patch('subprocess.run')
    def test_subprocess_error_handling(self, mock_run, environment_manager_instance):
        """Test subprocess error handling"""
        manager = environment_manager_instance
        
        # Mock subprocess error
        mock_run.side_effect = Exception("Command failed")
        
        result = manager.install_dependencies()
        
        assert result['success'] is False
        assert 'error' in result
    
    @patch('pathlib.Path.read_text')
    def test_file_read_error_handling(self, mock_read_text, environment_manager_instance):
        """Test file read error handling"""
        manager = environment_manager_instance
        
        # Mock file read error
        mock_read_text.side_effect = PermissionError("Permission denied")
        
        with patch('pathlib.Path.exists', return_value=True):
            # Should handle the error gracefully
            result = manager._nginx_config_includes_our_dir(
                Path('/etc/nginx/nginx.conf'), 
                Path('/etc/nginx/sites-enabled')
            )
            assert result is False  # Should fail gracefully
    
    def test_unsupported_system_handling(self):
        """Test handling of unsupported systems"""
        with patch('platform.system', return_value='FreeBSD'):
            # Should handle unknown systems gracefully
            manager = EnvironmentManager()
            assert manager.system == 'freebsd'  # Should normalize to lowercase
    
    @patch('subprocess.run')
    def test_permission_error_handling(self, mock_run, environment_manager_instance):
        """Test permission error handling"""
        manager = environment_manager_instance
        
        # Mock permission error
        mock_run.side_effect = PermissionError("Permission denied")
        
        result = manager.install_dependencies()
        
        assert result['success'] is False
        assert 'permission' in result['error'].lower() 