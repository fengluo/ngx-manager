"""
End-to-end tests for complete ngx-manager workflow
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import os
import time
from unittest.mock import patch, Mock

from nginx_manager.core.manager import NginxManager
from nginx_manager.ssl.manager import SSLManager
from nginx_manager.templates.generator import ConfigGenerator
from nginx_manager.utils.environment import EnvironmentManager
from nginx_manager.config.settings import Settings


@pytest.mark.e2e
class TestCompleteWorkflow:
    """Test complete ngx-manager workflow from start to finish"""
    
    @pytest.fixture
    def test_workspace(self):
        """Create test workspace"""
        workspace = Path(tempfile.mkdtemp())
        
        # Create directory structure
        (workspace / "config").mkdir()
        (workspace / "nginx").mkdir()
        (workspace / "certs").mkdir()
        (workspace / "logs").mkdir()
        (workspace / "www").mkdir()
        
        yield workspace
        
        # Cleanup
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def mock_settings(self, test_workspace):
        """Mock settings for testing"""
        with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.nginx_config_dir = test_workspace / "nginx"
            mock_settings.ssl_certs_dir = test_workspace / "certs"
            mock_settings.logs_dir = test_workspace / "logs"
            mock_settings.www_dir = test_workspace / "www"
            mock_settings_class.return_value = mock_settings
            yield mock_settings

    @pytest.mark.slow
    def test_native_environment_setup_workflow(self, test_workspace, mock_settings):
        """Test complete native environment setup workflow"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            # Step 1: Environment check and setup
            env_manager = EnvironmentManager()
            
            with patch('subprocess.run') as mock_run:
                # Mock successful environment checks
                mock_run.side_effect = [
                    Mock(returncode=0, stdout='Python 3.9.0'),  # python
                    Mock(returncode=0, stderr='nginx version: nginx/1.20.0'),  # nginx
                    Mock(returncode=0, stdout='OpenSSL 1.1.1f'),  # openssl
                    Mock(returncode=0, stdout='curl 7.68.0'),  # curl
                ]
                
                env_status = env_manager.check_environment()
                
                # Verify all tools are available
                assert env_status['python']['available'] is True
                assert env_status['nginx']['available'] is True
                assert env_status['openssl']['available'] is True
                assert env_status['curl']['available'] is True
            
            # Step 2: Initialize nginx manager
            manager = NginxManager()
            
            # Step 3: Add multiple sites with different configurations
            sites_to_add = [
                {
                    'domain': 'example.com',
                    'backend': None,  # Static site
                    'ssl': True
                },
                {
                    'domain': 'api.example.com',
                    'backend': 'http://localhost:3000',
                    'ssl': True
                },
                {
                    'domain': 'test.local',
                    'backend': 'http://localhost:8080',
                    'ssl': False
                }
            ]
            
            with patch('pathlib.Path.exists', return_value=False), \
                 patch('builtins.open'), \
                 patch('subprocess.run', return_value=Mock(returncode=0)), \
                 patch.object(manager.ssl_manager, 'obtain_certificate', 
                             return_value={'success': True}):
                
                for site in sites_to_add:
                    result = manager.add_site(
                        site['domain'],
                        site['backend'],
                        ssl=site['ssl']
                    )
                    
                    assert result['success'] is True
                    assert result['domain'] == site['domain']
            
            # Step 4: List sites
            with patch('pathlib.Path.glob') as mock_glob:
                mock_config_files = [
                    Mock(stem=site['domain']) for site in sites_to_add
                ]
                mock_glob.return_value = mock_config_files
                
                sites = manager.list_sites()
                assert len(sites) == len(sites_to_add)
                for site in sites_to_add:
                    assert site['domain'] in sites
            
            # Step 5: Check nginx status
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    Mock(returncode=0),  # service status
                    Mock(returncode=0),  # nginx -t
                    Mock(returncode=0, stderr='nginx version: nginx/1.20.0')  # nginx -v
                ]
                
                status = manager.get_nginx_status()
                assert status['status'] == 'running'
                assert status['config_test'] is True
                assert '1.20.0' in status['version']
            
            # Step 6: Remove a site
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.unlink'), \
                 patch('subprocess.run', return_value=Mock(returncode=0)):
                
                result = manager.remove_site('test.local')
                assert result['success'] is True

    def test_ssl_certificate_workflow(self, test_workspace, mock_settings):
        """Test SSL certificate management workflow"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            ssl_manager = SSLManager()
            
            # Step 1: Obtain certificate
            with patch('subprocess.run', return_value=Mock(returncode=0)), \
                 patch('pathlib.Path.exists', return_value=True):
                
                result = ssl_manager.obtain_certificate('secure.example.com')
                assert result['success'] is True
                assert result['domain'] == 'secure.example.com'
            
            # Step 2: Check certificate exists
            with patch('pathlib.Path.exists', return_value=True):
                assert ssl_manager.certificate_exists('secure.example.com') is True
            
            # Step 3: Renew certificate
            with patch('subprocess.run', return_value=Mock(returncode=0)):
                result = ssl_manager.renew_certificate('secure.example.com')
                assert result['success'] is True
            
            # Step 4: List certificates
            with patch('subprocess.run') as mock_run:
                mock_output = """Main_Domain:secure.example.com
Domain:secure.example.com
Status:Valid"""
                mock_run.return_value = Mock(returncode=0, stdout=mock_output)
                
                certificates = ssl_manager.list_certificates()
                assert isinstance(certificates, list)
                assert any('secure.example.com' in cert for cert in certificates)

    def test_template_customization_workflow(self, test_workspace, mock_settings):
        """Test template customization workflow"""
        generator = ConfigGenerator()
        
        # Step 1: List available templates
        templates = generator.list_available_templates()
        assert len(templates) >= 4
        assert 'proxy_ssl.conf.j2' in templates
        
        # Step 2: Get template content
        template_content = generator.get_template_content('proxy_ssl.conf.j2')
        assert template_content is not None
        assert '{{ domain }}' in template_content
        
        # Step 3: Generate configuration with custom data
        config = generator.generate_site_config(
            domain='custom.example.com',
            backend='http://custom-backend:8080',
            ssl=True
        )
        
        assert 'custom.example.com' in config
        assert 'http://custom-backend:8080' in config
        assert 'ssl_certificate' in config
        
        # Step 4: Generate static site configuration
        static_config = generator.generate_site_config(
            domain='static.example.com',
            ssl=False
        )
        
        assert 'static.example.com' in static_config
        assert 'root /var/www/' in static_config
        assert 'ssl_certificate' not in static_config

    @pytest.mark.slow
    def test_error_recovery_workflow(self, test_workspace, mock_settings):
        """Test error recovery and handling workflow"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            manager = NginxManager()
            
            # Step 1: Test nginx configuration error
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=1, stderr="nginx: configuration file test failed")
                
                status = manager.get_nginx_status()
                assert status['config_test'] is False
            
            # Step 2: Test SSL certificate failure
            with patch.object(manager.ssl_manager, 'obtain_certificate') as mock_ssl:
                mock_ssl.return_value = {'success': False, 'error': 'Rate limit exceeded'}
                
                with patch('pathlib.Path.exists', return_value=False), \
                     patch('builtins.open'), \
                     patch('subprocess.run', return_value=Mock(returncode=0)):
                    
                    result = manager.add_site('fail.example.com', ssl=True)
                    # Should still succeed in creating config even if SSL fails
                    assert result['success'] is True
            
            # Step 3: Test site removal when file doesn't exist
            with patch('pathlib.Path.exists', return_value=False):
                result = manager.remove_site('nonexistent.example.com')
                assert result['success'] is False
                assert 'not found' in result['error']

    def test_configuration_validation_workflow(self, test_workspace, mock_settings):
        """Test configuration validation workflow"""
        generator = ConfigGenerator()
        
        # Step 1: Generate valid configuration
        valid_config = generator.generate_site_config(
            domain='valid.example.com',
            backend='http://localhost:3000',
            ssl=True
        )
        
        # Basic validation checks
        assert 'server {' in valid_config
        assert 'listen 80;' in valid_config
        assert 'listen 443 ssl;' in valid_config
        assert 'server_name valid.example.com;' in valid_config
        assert 'proxy_pass http://localhost:3000;' in valid_config
        
        # Step 2: Test configuration with security headers
        assert 'X-Real-IP' in valid_config
        assert 'X-Forwarded-For' in valid_config
        assert 'Host' in valid_config
        
        # Step 3: Test SSL configuration
        assert 'ssl_certificate' in valid_config
        assert 'ssl_certificate_key' in valid_config

    @pytest.mark.slow
    def test_performance_workflow(self, test_workspace, mock_settings):
        """Test performance under load"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            manager = NginxManager()
            generator = ConfigGenerator()
            
            # Step 1: Generate many configurations quickly
            domains = [f'perf-{i}.example.com' for i in range(50)]
            
            start_time = time.time()
            
            for domain in domains:
                config = generator.generate_site_config(
                    domain=domain,
                    backend='http://localhost:3000',
                    ssl=True
                )
                assert config is not None
                assert domain in config
            
            end_time = time.time()
            
            # Should complete within reasonable time
            assert (end_time - start_time) < 2.0
            
            # Step 2: Test site management performance
            start_time = time.time()
            
            with patch('pathlib.Path.exists', return_value=False), \
                 patch('builtins.open'), \
                 patch('subprocess.run', return_value=Mock(returncode=0)), \
                 patch.object(manager.ssl_manager, 'obtain_certificate', 
                             return_value={'success': True}):
                
                for i in range(10):
                    domain = f'mgmt-perf-{i}.example.com'
                    result = manager.add_site(domain, 'http://localhost:3000')
                    assert result['success'] is True
            
            end_time = time.time()
            
            # Should complete within reasonable time
            assert (end_time - start_time) < 3.0


@pytest.mark.e2e
@pytest.mark.integration
class TestCrossComponentIntegration:
    """Test integration between different components"""
    
    def test_manager_ssl_generator_integration(self, test_workspace):
        """Test integration between manager, SSL manager, and config generator"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.nginx_config_dir = test_workspace / "nginx"
                mock_settings.ssl_certs_dir = test_workspace / "certs"
                mock_settings.logs_dir = test_workspace / "logs"
                mock_settings.www_dir = test_workspace / "www"
                mock_settings_class.return_value = mock_settings
                
                # Initialize all components
                manager = NginxManager()
                ssl_manager = manager.ssl_manager
                generator = manager.config_generator
                
                # Test SSL certificate obtainment affects config generation
                with patch('subprocess.run', return_value=Mock(returncode=0)), \
                     patch('pathlib.Path.exists', return_value=True):
                    
                    ssl_result = ssl_manager.obtain_certificate('integrated.example.com')
                    assert ssl_result['success'] is True
                
                # Test config generation uses SSL certificate paths
                config = generator.generate_site_config(
                    domain='integrated.example.com',
                    ssl=True
                )
                
                assert 'ssl_certificate' in config
                assert 'integrated.example.com' in config
                
                # Test manager coordinates both components
                with patch('pathlib.Path.exists', return_value=False), \
                     patch('builtins.open'), \
                     patch('subprocess.run', return_value=Mock(returncode=0)):
                    
                    result = manager.add_site('integrated.example.com', ssl=True)
                    assert result['success'] is True 