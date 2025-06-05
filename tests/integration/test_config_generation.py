"""
Integration tests for configuration generation workflow
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
import os
from unittest.mock import patch, Mock

from nginx_manager.templates.generator import ConfigGenerator
from nginx_manager.core.manager import NginxManager
from nginx_manager.ssl.manager import SSLManager
from nginx_manager.config.settings import Settings


class TestConfigGenerationWorkflow:
    """Test complete configuration generation workflow"""
    
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
    def site_configs(self, test_workspace):
        """Create site configuration files"""
        configs = [
            {
                "domain": "example.com",
                "type": "static",
                "ssl": True,
                "www_dir": "/var/www/example.com"
            },
            {
                "domain": "api.example.com", 
                "type": "proxy",
                "backend": "http://localhost:3000",
                "ssl": True
            },
            {
                "domain": "test.local",
                "type": "static", 
                "ssl": False,
                "www_dir": "/var/www/test"
            }
        ]
        
        return configs

    @pytest.fixture
    def config_generator_with_workspace(self, test_workspace):
        """Create config generator with test workspace"""
        with patch('nginx_manager.config.settings.Settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings_instance.ssl_certs_dir = test_workspace / "certs"
            mock_settings_instance.logs_dir = test_workspace / "logs"
            mock_settings_instance.www_dir = test_workspace / "www"
            mock_settings_instance.nginx_config_dir = test_workspace / "nginx"
            
            generator = ConfigGenerator()
            generator.settings = mock_settings_instance
            return generator

    def test_complete_config_generation_workflow(self, test_workspace, site_configs, 
                                               config_generator_with_workspace):
        """Test complete configuration generation workflow"""
        generator = config_generator_with_workspace
        
        # Generate configurations for all sites
        generated_configs = []
        
        for site_config in site_configs:
            config = generator.generate_site_config(
                domain=site_config['domain'],
                backend=site_config.get('backend'),
                ssl=site_config['ssl']
            )
            
            # Verify configuration was generated
            assert config is not None
            assert site_config['domain'] in config
            
            if site_config['ssl']:
                assert 'ssl_certificate' in config
                assert 'listen 443 ssl' in config
                assert 'listen 80' in config  # HTTP redirect
            else:
                assert 'ssl_certificate' not in config
                assert 'listen 80' in config
                assert 'listen 443' not in config
            
            if site_config['type'] == 'proxy':
                assert 'proxy_pass' in config
                assert site_config['backend'] in config
            else:
                assert 'root /var/www/' in config
                assert 'try_files $uri $uri/ =404' in config
            
            generated_configs.append(config)
        
        # Verify all configurations were generated
        assert len(generated_configs) == len(site_configs)
        
        # Test template availability
        templates = generator.list_available_templates()
        assert len(templates) >= 4  # Should have all 4 base templates
        assert 'proxy_ssl.conf.j2' in templates
        assert 'static_ssl.conf.j2' in templates
        assert 'proxy_http.conf.j2' in templates
        assert 'static_http.conf.j2' in templates

    def test_nginx_manager_integration(self, test_workspace, site_configs):
        """Test nginx manager integration with config generation"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.nginx_config_dir = test_workspace / "nginx"
                mock_settings.ssl_certs_dir = test_workspace / "certs"
                mock_settings.logs_dir = test_workspace / "logs"
                mock_settings.www_dir = test_workspace / "www"
                mock_settings_class.return_value = mock_settings
                
                manager = NginxManager()
                
                # Test adding sites through manager
                with patch('pathlib.Path.exists', return_value=False), \
                     patch('builtins.open'), \
                     patch('subprocess.run', return_value=Mock(returncode=0)), \
                     patch.object(manager.ssl_manager, 'obtain_certificate', 
                                 return_value={'success': True}):
                    
                    for site_config in site_configs:
                        result = manager.add_site(
                            site_config['domain'],
                            site_config.get('backend'),
                            ssl=site_config['ssl']
                        )
                        
                        assert result['success'] is True
                        assert result['domain'] == site_config['domain']

    def test_ssl_certificate_integration(self, test_workspace):
        """Test SSL certificate management integration"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.ssl_certs_dir = test_workspace / "certs"
                mock_settings_class.return_value = mock_settings
                
                ssl_manager = SSLManager()
                
                # Test certificate obtainment workflow
                with patch('subprocess.run', return_value=Mock(returncode=0)), \
                     patch('pathlib.Path.exists', return_value=True):
                    
                    result = ssl_manager.obtain_certificate('test.example.com')
                    
                    assert result['success'] is True
                    assert result['domain'] == 'test.example.com'
                    assert 'certificate_path' in result
                    assert 'private_key_path' in result

    def test_error_handling_in_workflow(self, test_workspace, config_generator_with_workspace):
        """Test error handling in configuration workflow"""
        generator = config_generator_with_workspace
        
        # Test invalid template
        with pytest.raises(FileNotFoundError):
            generator.generate_site_config(
                domain='test.example.com',
                template_name='nonexistent.j2'
            )
        
        # Test invalid domain
        config = generator.generate_site_config(
            domain='',  # Empty domain
            ssl=True
        )
        # Should still generate config but may have issues
        assert config is not None

    def test_template_customization_workflow(self, test_workspace, config_generator_with_workspace):
        """Test template customization workflow"""
        generator = config_generator_with_workspace
        
        # Get existing template content
        template_content = generator.get_template_content('proxy_ssl.conf.j2')
        assert template_content is not None
        assert '{{ domain }}' in template_content
        assert '{{ backend }}' in template_content
        
        # Test template rendering with custom data
        config = generator.generate_site_config(
            domain='custom.example.com',
            backend='http://custom-backend:8080',
            ssl=True
        )
        
        assert 'custom.example.com' in config
        assert 'http://custom-backend:8080' in config
        assert 'ssl_certificate' in config


class TestConfigValidation:
    """Test configuration validation workflow"""
    
    def test_nginx_config_validation_integration(self, test_workspace):
        """Test nginx configuration validation"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.nginx_config_dir = test_workspace / "nginx"
                mock_settings.ssl_certs_dir = test_workspace / "certs"
                mock_settings.logs_dir = test_workspace / "logs"
                mock_settings.www_dir = test_workspace / "www"
                mock_settings_class.return_value = mock_settings
                
                manager = NginxManager()
                
                # Test nginx status and validation
                with patch('subprocess.run') as mock_run:
                    # Mock successful nginx test
                    mock_run.side_effect = [
                        Mock(returncode=0),  # service status
                        Mock(returncode=0),  # nginx -t
                        Mock(returncode=0, stderr='nginx version: nginx/1.20.0')  # nginx -v
                    ]
                    
                    status = manager.get_nginx_status()
                    
                    assert status['status'] == 'running'
                    assert status['config_test'] is True
                    assert '1.20.0' in status['version']

    def test_site_management_workflow(self, test_workspace):
        """Test complete site management workflow"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.nginx_config_dir = test_workspace / "nginx"
                mock_settings.ssl_certs_dir = test_workspace / "certs"
                mock_settings.logs_dir = test_workspace / "logs"
                mock_settings.www_dir = test_workspace / "www"
                mock_settings_class.return_value = mock_settings
                
                manager = NginxManager()
                
                # Test site addition workflow
                with patch('pathlib.Path.exists', return_value=False), \
                     patch('builtins.open'), \
                     patch('subprocess.run', return_value=Mock(returncode=0)), \
                     patch.object(manager.ssl_manager, 'obtain_certificate', 
                                 return_value={'success': True}):
                    
                    # Add site
                    result = manager.add_site('test.example.com', 'http://localhost:3000')
                    assert result['success'] is True
                    
                    # Mock site exists for listing
                    with patch('pathlib.Path.glob') as mock_glob:
                        mock_config_files = [
                            Mock(stem='test.example.com'),
                            Mock(stem='api.example.com')
                        ]
                        mock_glob.return_value = mock_config_files
                        
                        # List sites
                        sites = manager.list_sites()
                        assert 'test.example.com' in sites
                        assert 'api.example.com' in sites
                    
                    # Remove site
                    with patch('pathlib.Path.exists', return_value=True), \
                         patch('pathlib.Path.unlink'):
                        
                        result = manager.remove_site('test.example.com')
                        assert result['success'] is True


class TestPerformanceIntegration:
    """Test performance aspects of integration"""
    
    def test_multiple_site_generation_performance(self, config_generator_with_workspace):
        """Test performance with multiple site generation"""
        generator = config_generator_with_workspace
        
        # Generate configs for multiple sites
        domains = [f'site{i}.example.com' for i in range(10)]
        
        import time
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
        
        # Should complete within reasonable time (less than 1 second for 10 sites)
        assert (end_time - start_time) < 1.0
    
    def test_template_caching_behavior(self, config_generator_with_workspace):
        """Test template caching behavior"""
        generator = config_generator_with_workspace
        
        # Generate same config multiple times
        import time
        
        # First generation
        start_time = time.time()
        config1 = generator.generate_site_config(
            domain='cache-test.example.com',
            ssl=True
        )
        first_time = time.time() - start_time
        
        # Second generation (should use cached template)
        start_time = time.time()
        config2 = generator.generate_site_config(
            domain='cache-test2.example.com',
            ssl=True
        )
        second_time = time.time() - start_time
        
        # Both configs should be identical in structure
        assert config1 is not None
        assert config2 is not None
        assert 'ssl_certificate' in config1
        assert 'ssl_certificate' in config2
        
        # Second generation should be faster or similar (template cached)
        assert second_time <= first_time * 1.5  # Allow some variance 