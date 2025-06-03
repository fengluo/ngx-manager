"""
测试证书管理脚本 (cert_manager.py)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import yaml
import subprocess
from pathlib import Path
import tempfile
import shutil
import os

# 使用pytest的mock环境变量
pytestmark = pytest.mark.unit

class TestSSLCertificateManager:
    """测试SSL证书管理器"""
    
    def test_init_with_custom_paths(self, test_dirs, mock_environment):
        """测试使用自定义路径初始化"""
        from cert_manager import SSLCertificateManager
        
        manager = SSLCertificateManager(
            config_dir=str(test_dirs['config_dir']),
            certs_dir=str(test_dirs['certs_dir']),
            logs_dir=str(test_dirs['logs_dir'])
        )
        
        assert manager.config_dir == test_dirs['config_dir']
        assert manager.certs_dir == test_dirs['certs_dir']
        assert manager.logs_dir == test_dirs['logs_dir']
        
        # 验证目录已创建
        assert test_dirs['config_dir'].exists()
        assert test_dirs['certs_dir'].exists()
        assert test_dirs['logs_dir'].exists()

    def test_init_with_environment_variables(self, cert_manager_instance, test_dirs):
        """测试通过环境变量初始化"""
        manager = cert_manager_instance
        
        assert manager.config_dir == test_dirs['config_dir']
        assert manager.certs_dir == test_dirs['certs_dir']
        assert manager.logs_dir == test_dirs['logs_dir']

    def test_load_ssl_config_success(self, cert_manager_instance, create_test_configs):
        """测试成功加载SSL配置"""
        manager = cert_manager_instance
        config = manager.load_ssl_config()
        
        assert 'ssl' in config
        assert 'acme' in config
        assert config['ssl']['email'] == 'test@example.com'
        assert config['ssl']['ca_server'] == 'letsencrypt'

    def test_load_ssl_config_missing_file(self, cert_manager_instance):
        """测试SSL配置文件不存在时使用默认配置"""
        manager = cert_manager_instance
        config = manager.load_ssl_config()
        
        # 应该返回默认配置
        assert config['ssl']['email'] == 'admin@example.com'
        assert config['ssl']['ca_server'] == 'letsencrypt'

    def test_get_default_ssl_config(self, cert_manager_instance):
        """测试获取默认SSL配置"""
        manager = cert_manager_instance
        config = manager.get_default_ssl_config()
        
        assert 'ssl' in config
        assert 'acme' in config
        assert 'advanced' in config
        assert config['ssl']['ca_server'] == 'letsencrypt'

    def test_get_ca_server_url_letsencrypt_production(self, cert_manager_instance):
        """测试获取Let's Encrypt生产环境URL"""
        manager = cert_manager_instance
        manager.ssl_config['ssl']['ca_server'] = 'letsencrypt'
        manager.ssl_config['acme']['staging'] = False
        
        url = manager.get_ca_server_url()
        assert url == 'https://acme-v02.api.letsencrypt.org/directory'

    def test_get_ca_server_url_letsencrypt_staging(self, cert_manager_instance):
        """测试获取Let's Encrypt测试环境URL"""
        manager = cert_manager_instance
        manager.ssl_config['ssl']['ca_server'] = 'letsencrypt'
        manager.ssl_config['acme']['staging'] = True
        
        url = manager.get_ca_server_url()
        assert url == 'https://acme-staging-v02.api.letsencrypt.org/directory'

    def test_get_ca_server_url_zerossl(self, cert_manager_instance):
        """测试获取ZeroSSL URL"""
        manager = cert_manager_instance
        manager.ssl_config['ssl']['ca_server'] = 'zerossl'
        
        url = manager.get_ca_server_url()
        assert url == 'https://acme.zerossl.com/v2/DV90'

    def test_get_ca_server_url_buypass(self, cert_manager_instance):
        """测试获取Buypass URL"""
        manager = cert_manager_instance
        manager.ssl_config['ssl']['ca_server'] = 'buypass'
        manager.ssl_config['acme']['staging'] = False
        
        url = manager.get_ca_server_url()
        assert url == 'https://api.buypass.com/acme/directory'

    def test_get_ca_server_url_invalid(self, cert_manager_instance):
        """测试无效CA服务器"""
        manager = cert_manager_instance
        manager.ssl_config['ssl']['ca_server'] = 'invalid'
        
        with pytest.raises(ValueError, match="不支持的CA服务器"):
            manager.get_ca_server_url()

    @patch('subprocess.run')
    def test_run_command_success(self, mock_subprocess, cert_manager_instance):
        """测试成功执行命令"""
        manager = cert_manager_instance
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success", stderr="")
        
        result = manager.run_command(['echo', 'test'])
        
        assert result.returncode == 0
        assert result.stdout == "Success"

    @patch('subprocess.run')
    def test_run_command_failure(self, mock_subprocess, cert_manager_instance):
        """测试命令执行失败"""
        manager = cert_manager_instance
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'test', stderr="Error")
        
        with pytest.raises(subprocess.CalledProcessError):
            manager.run_command(['false'])

    @patch('subprocess.run')
    def test_init_acme_success(self, mock_subprocess, cert_manager_instance):
        """测试成功初始化acme.sh"""
        manager = cert_manager_instance
        
        # 简化Mock - 直接假设acme.sh存在，ca目录不存在
        with patch('pathlib.Path.exists') as mock_exists:
            # 第一次调用检查acme.sh(存在)，第二次调用检查ca目录(不存在)
            mock_exists.side_effect = [True, False]
            
            result = manager.init_acme()
            
            assert result == True
            assert mock_subprocess.call_count >= 2  # 设置CA + 注册账户

    def test_init_acme_missing_binary(self, cert_manager_instance):
        """测试acme.sh不存在"""
        manager = cert_manager_instance
        
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False
            result = manager.init_acme()
            assert result == False

    def test_cert_exists_true(self, cert_manager_instance):
        """测试证书存在"""
        manager = cert_manager_instance
        domain = "test.example.com"
        
        cert_dir = manager.certs_dir / domain
        cert_dir.mkdir(parents=True, exist_ok=True)
        
        cert_file = cert_dir / 'fullchain.cer'
        key_file = cert_dir / f'{domain}.key'
        
        cert_file.touch()
        key_file.touch()
        
        assert manager.cert_exists(domain) == True

    def test_cert_exists_false(self, cert_manager_instance):
        """测试证书不存在"""
        manager = cert_manager_instance
        assert manager.cert_exists("nonexistent.example.com") == False

    @patch('subprocess.run')
    def test_cert_needs_renewal_expired(self, mock_subprocess, cert_manager_instance):
        """测试需要更新的证书"""
        manager = cert_manager_instance
        domain = "test.example.com"
        
        # Mock openssl命令返回已过期证书
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="notAfter=Jan  1 00:00:00 2020 GMT"
        )
        
        cert_dir = manager.certs_dir / domain
        cert_dir.mkdir(parents=True, exist_ok=True)
        cert_file = cert_dir / 'fullchain.cer'
        cert_file.touch()
        
        result = manager.cert_needs_renewal(domain)
        assert result == True

    def test_cert_needs_renewal_missing_cert(self, cert_manager_instance):
        """测试证书文件不存在"""
        manager = cert_manager_instance
        result = manager.cert_needs_renewal("nonexistent.example.com")
        assert result == True

    @patch('subprocess.run')
    def test_issue_cert_success(self, mock_subprocess, cert_manager_instance):
        """测试成功申请证书"""
        manager = cert_manager_instance
        domain = "test.example.com"
        
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success")
        
        result = manager.issue_cert(domain)
        assert result == True
        
        # 验证证书目录已创建
        cert_dir = manager.certs_dir / domain
        assert cert_dir.exists()

    @patch('subprocess.run')
    def test_issue_cert_retry_success(self, mock_subprocess, cert_manager_instance):
        """测试重试后成功申请证书"""
        manager = cert_manager_instance
        domain = "test.example.com"
        
        # 设置短重试间隔用于测试
        manager.ssl_config['advanced']['retry_attempts'] = 2
        manager.ssl_config['advanced']['retry_interval'] = 0.1
        
        # 第一次失败，第二次成功
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, 'acme.sh', stderr="Rate limited"),
            Mock(returncode=0, stdout="Success")
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = manager.issue_cert(domain)
            
        assert result == True
        assert mock_subprocess.call_count == 2

    @patch('subprocess.run')
    def test_issue_cert_failure(self, mock_subprocess, cert_manager_instance):
        """测试证书申请失败"""
        manager = cert_manager_instance
        domain = "test.example.com"
        
        # 设置少量重试用于测试
        manager.ssl_config['advanced']['retry_attempts'] = 1
        
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'acme.sh', stderr="Failed")
        
        result = manager.issue_cert(domain)
        assert result == False

    @patch('subprocess.run')
    def test_renew_cert_success(self, mock_subprocess, cert_manager_instance):
        """测试成功更新证书"""
        manager = cert_manager_instance
        domain = "test.example.com"
        
        mock_subprocess.return_value = Mock(returncode=0, stdout="Renewed")
        
        result = manager.renew_cert(domain)
        assert result == True

    @patch('subprocess.run')
    def test_renew_cert_failure(self, mock_subprocess, cert_manager_instance):
        """测试证书更新失败"""
        manager = cert_manager_instance
        domain = "test.example.com"
        
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'acme.sh', stderr="Failed")
        
        result = manager.renew_cert(domain)
        assert result == False

    def test_get_ssl_domains_with_ssl_enabled(self, cert_manager_instance, create_test_configs):
        """测试获取启用SSL的域名"""
        manager = cert_manager_instance
        domains = manager.get_ssl_domains()
        
        assert len(domains) == 1
        assert "test.example.com" in domains

    def test_get_ssl_domains_missing_config(self, cert_manager_instance):
        """测试配置文件不存在时获取SSL域名"""
        manager = cert_manager_instance
        domains = manager.get_ssl_domains()
        
        assert domains == []

    def test_get_ssl_domains_no_ssl_vhosts(self, cert_manager_instance, test_dirs):
        """测试没有启用SSL的虚拟主机"""
        manager = cert_manager_instance
        
        # 创建没有SSL的配置
        vhosts_config = [
            {
                "name": "test-site",
                "domains": ["test.example.com"],
                "type": "static",
                "root": "/var/www/html",
                "ssl": False
            }
        ]
        
        vhosts_file = test_dirs['config_dir'] / 'vhosts.yml'
        with open(vhosts_file, 'w') as f:
            yaml.dump(vhosts_config, f)
        
        domains = manager.get_ssl_domains()
        assert domains == []

    @patch('subprocess.run')
    def test_check_and_issue_all_certs_success(self, mock_subprocess, cert_manager_instance, create_test_configs):
        """测试检查并申请所有证书成功"""
        manager = cert_manager_instance
        
        # Mock所有需要的subprocess调用
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success")
        
        # Mock cert_exists返回False，cert_needs_renewal返回True
        with patch.object(manager, 'cert_exists', return_value=False), \
             patch.object(manager, 'issue_cert', return_value=True), \
             patch.object(manager, 'reload_nginx'):
            
            result = manager.check_and_issue_all_certs()
            
        assert result == True

    @patch('subprocess.run')
    def test_renew_all_certs_success(self, mock_subprocess, cert_manager_instance):
        """测试更新所有证书成功"""
        manager = cert_manager_instance
        
        mock_subprocess.return_value = Mock(returncode=0, stdout="All renewed")
        
        with patch.object(manager, 'reload_nginx'):
            result = manager.renew_all_certs()
            
        assert result == True

    @patch('subprocess.run')
    def test_list_certs(self, mock_subprocess, cert_manager_instance):
        """测试列出证书"""
        manager = cert_manager_instance
        
        mock_subprocess.return_value = Mock(returncode=0, stdout="cert1.com\ncert2.com")
        
        # 创建一些测试证书文件
        cert_dir = manager.certs_dir / "test.com"
        cert_dir.mkdir(parents=True, exist_ok=True)
        (cert_dir / "test.cer").touch()
        (cert_dir / "test.key").touch()
        
        # 这个方法主要是打印输出，我们验证它不会抛出异常
        manager.list_certs()

    @patch('subprocess.run')
    def test_update_email_success(self, mock_subprocess, cert_manager_instance, test_dirs):
        """测试更新邮箱成功"""
        manager = cert_manager_instance
        new_email = "new@example.com"
        
        mock_subprocess.return_value = Mock(returncode=0, stdout="Email updated")
        
        result = manager.update_email(new_email)
        
        assert result == True
        assert manager.ssl_config['ssl']['email'] == new_email
        
        # 验证配置文件已更新
        ssl_config_file = test_dirs['config_dir'] / 'ssl.yml'
        assert ssl_config_file.exists()

    @patch('subprocess.run')
    def test_reload_nginx_success(self, mock_subprocess, cert_manager_instance):
        """测试重新加载nginx成功"""
        manager = cert_manager_instance
        
        mock_subprocess.return_value = Mock(returncode=0, stdout="Reloaded")
        
        # 这个方法不返回值，我们验证它不会抛出异常
        manager.reload_nginx()

    @patch('subprocess.run')
    def test_reload_nginx_failure(self, mock_subprocess, cert_manager_instance):
        """测试重新加载nginx失败"""
        manager = cert_manager_instance
        
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'nginx', stderr="Failed")
        
        # 即使失败也不应该抛出异常，只是记录日志
        manager.reload_nginx()

class TestSSLCertificateManagerCLI:
    """测试SSL证书管理器命令行接口"""
    
    @patch('cert_manager.SSLCertificateManager')
    def test_main_init(self, mock_manager_class):
        """测试初始化命令"""
        from cert_manager import main
        mock_manager = Mock()
        mock_manager.init_acme.return_value = True
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', ['cert_manager.py', '--init']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch('cert_manager.SSLCertificateManager')
    def test_main_check_all(self, mock_manager_class):
        """测试检查所有证书命令"""
        from cert_manager import main
        mock_manager = Mock()
        mock_manager.init_acme.return_value = True
        mock_manager.check_and_issue_all_certs.return_value = True
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', ['cert_manager.py', '--check-all']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch('cert_manager.SSLCertificateManager')
    def test_main_no_args(self, mock_manager_class):
        """测试没有参数时显示帮助"""
        from cert_manager import main
        
        with patch('sys.argv', ['cert_manager.py']):
            # 没有参数时应该正常退出
            main()

    @patch('cert_manager.SSLCertificateManager')
    def test_main_keyboard_interrupt(self, mock_manager_class):
        """测试键盘中断"""
        from cert_manager import main
        mock_manager = Mock()
        mock_manager.init_acme.side_effect = KeyboardInterrupt()
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', ['cert_manager.py', '--init']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('cert_manager.SSLCertificateManager')
    def test_main_exception(self, mock_manager_class):
        """测试一般异常"""
        from cert_manager import main
        mock_manager = Mock()
        mock_manager.init_acme.side_effect = Exception("Test error")
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', ['cert_manager.py', '--init']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1 