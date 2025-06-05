"""
Tests for template generator
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from nginx_manager.templates.generator import ConfigGenerator


class TestConfigGenerator:
    """Test configuration generator"""
    
    def test_generator_initialization(self, config_generator_instance):
        """Test generator initialization"""
        generator = config_generator_instance
        
        assert generator.template_dir.exists()
        assert generator.env is not None
    
    def test_list_available_templates(self, config_generator_instance):
        """Test listing available templates"""
        generator = config_generator_instance
        templates = generator.list_available_templates()
        
        # Should include the default templates
        expected_templates = [
            'proxy_http.conf.j2',
            'proxy_ssl.conf.j2', 
            'static_http.conf.j2',
            'static_ssl.conf.j2'
        ]
        
        for template in expected_templates:
            assert template in templates
    
    def test_default_template_name_selection(self, config_generator_instance):
        """Test default template name selection"""
        generator = config_generator_instance
        
        # Test SSL proxy
        template_name = generator._get_default_template_name(ssl=True, is_proxy=True)
        assert template_name == 'proxy_ssl.conf.j2'
        
        # Test SSL static
        template_name = generator._get_default_template_name(ssl=True, is_proxy=False)
        assert template_name == 'static_ssl.conf.j2'
        
        # Test HTTP proxy
        template_name = generator._get_default_template_name(ssl=False, is_proxy=True)
        assert template_name == 'proxy_http.conf.j2'
        
        # Test HTTP static
        template_name = generator._get_default_template_name(ssl=False, is_proxy=False)
        assert template_name == 'static_http.conf.j2'
    
    def test_generate_ssl_proxy_config(self, config_generator_instance):
        """Test SSL proxy configuration generation"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='api.example.com',
            backend='http://localhost:3000',
            ssl=True
        )
        
        # Check basic structure
        assert 'api.example.com' in config
        assert 'proxy_pass http://localhost:3000' in config
        assert 'ssl_certificate' in config
        assert 'listen 443 ssl' in config
        assert 'listen 80' in config  # HTTP redirect
        assert 'return 301 https://' in config  # HTTPS redirect
        
        # Check security headers
        assert 'Strict-Transport-Security' in config
        assert 'X-Frame-Options' in config
        assert 'X-Content-Type-Options' in config
        
        # Check Let's Encrypt support
        assert '.well-known/acme-challenge' in config
    
    def test_generate_ssl_static_config(self, config_generator_instance):
        """Test SSL static configuration generation"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='static.example.com',
            ssl=True
        )
        
        # Check basic structure
        assert 'static.example.com' in config
        assert 'root /var/www/static.example.com' in config
        assert 'try_files $uri $uri/ =404' in config
        assert 'ssl_certificate' in config
        assert 'listen 443 ssl' in config
        assert 'listen 80' in config  # HTTP redirect
        
        # Should not contain proxy directives
        assert 'proxy_pass' not in config
    
    def test_generate_http_proxy_config(self, config_generator_instance):
        """Test HTTP proxy configuration generation"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='api.example.com',
            backend='http://localhost:3000',
            ssl=False
        )
        
        # Check basic structure
        assert 'api.example.com' in config
        assert 'proxy_pass http://localhost:3000' in config
        assert 'listen 80' in config
        
        # Should not contain SSL directives
        assert 'ssl_certificate' not in config
        assert 'listen 443' not in config
        assert 'return 301 https://' not in config
    
    def test_generate_http_static_config(self, config_generator_instance):
        """Test HTTP static configuration generation"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='static.example.com',
            ssl=False
        )
        
        # Check basic structure
        assert 'static.example.com' in config
        assert 'root /var/www/static.example.com' in config
        assert 'try_files $uri $uri/ =404' in config
        assert 'listen 80' in config
        
        # Should not contain SSL or proxy directives
        assert 'ssl_certificate' not in config
        assert 'proxy_pass' not in config
        assert 'listen 443' not in config
    
    def test_custom_template_name(self, config_generator_instance):
        """Test using custom template name"""
        generator = config_generator_instance
        
        # Test with existing template
        config = generator.generate_site_config(
            domain='test.example.com',
            backend='http://localhost:8080',
            template_name='proxy_ssl.conf.j2'
        )
        
        assert 'test.example.com' in config
        assert 'proxy_pass http://localhost:8080' in config
        assert 'ssl_certificate' in config
    
    def test_template_not_found_error(self, config_generator_instance):
        """Test template not found error handling"""
        generator = config_generator_instance
        
        with pytest.raises(FileNotFoundError):
            generator.generate_site_config(
                domain='test.example.com',
                template_name='nonexistent_template.j2'
            )
    
    def test_get_template_content(self, config_generator_instance):
        """Test getting template content"""
        generator = config_generator_instance
        
        # Test with existing template
        content = generator.get_template_content('proxy_ssl.conf.j2')
        assert content is not None
        assert '{{ domain }}' in content
        assert '{{ backend }}' in content
        assert 'proxy_pass' in content
        
        # Test with non-existent template
        with pytest.raises(FileNotFoundError):
            generator.get_template_content('nonexistent.j2')
    
    def test_template_variables_substitution(self, config_generator_instance):
        """Test template variable substitution"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='test.example.com',
            backend='http://backend.local:8080',
            ssl=True
        )
        
        # Check that all variables are properly substituted
        assert '{{ domain }}' not in config  # No unsubstituted variables
        assert '{{ backend }}' not in config
        assert '{{ ssl_cert_path }}' not in config
        assert '{{ ssl_key_path }}' not in config
        assert '{{ access_log }}' not in config
        assert '{{ error_log }}' not in config
        
        # Check that actual values are present
        assert 'test.example.com' in config
        assert 'http://backend.local:8080' in config
    
    def test_default_backend_fallback(self, config_generator_instance):
        """Test default backend fallback for proxy configs"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='test.example.com',
            backend=None,  # No backend specified
            ssl=False
        )
        
        # Should use default backend
        assert 'proxy_pass http://localhost:8080' in config
    
    @patch('nginx_manager.config.settings.settings')
    def test_settings_integration(self, mock_settings, config_generator_instance):
        """Test integration with settings"""
        # Mock settings paths
        mock_settings.ssl_certs_dir = Path('/custom/certs')
        mock_settings.logs_dir = Path('/custom/logs')
        
        generator = config_generator_instance
        config = generator.generate_site_config(
            domain='test.example.com',
            ssl=True
        )
        
        # Should use custom paths from settings
        assert '/custom/certs/test.example.com' in config
        assert '/custom/logs/test.example.com' in config


class TestTemplateExtension:
    """Test template extension capabilities"""
    
    def test_custom_template_directory(self):
        """Test using custom template directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_template_dir = Path(temp_dir) / "custom_templates"
            custom_template_dir.mkdir()
            
            # Create a custom template
            custom_template = custom_template_dir / "custom.conf.j2"
            custom_template.write_text("""
server {
    listen 80;
    server_name {{ domain }};
    
    # Custom configuration
    return 200 "Custom template works!";
}
""")
            
            # Test that custom template can be loaded
            # This would require modifying the ConfigGenerator to accept custom paths
            # For now, we test that the file exists and can be read
            assert custom_template.exists()
            content = custom_template.read_text()
            assert '{{ domain }}' in content
            assert 'Custom template works!' in content
    
    def test_template_syntax_validation(self, config_generator_instance):
        """Test that generated templates have valid nginx syntax structure"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='test.example.com',
            backend='http://localhost:3000',
            ssl=True
        )
        
        # Basic nginx syntax checks
        assert config.count('server {') >= 1
        assert config.count('}') >= config.count('{')
        assert 'server_name test.example.com' in config
        
        # SSL configuration structure
        ssl_directives = [
            'ssl_certificate',
            'ssl_certificate_key',
            'ssl_protocols',
            'ssl_ciphers'
        ]
        for directive in ssl_directives:
            assert directive in config
    
    def test_security_headers_presence(self, config_generator_instance):
        """Test that security headers are included in SSL templates"""
        generator = config_generator_instance
        
        config = generator.generate_site_config(
            domain='secure.example.com',
            ssl=True
        )
        
        security_headers = [
            'Strict-Transport-Security',
            'X-Frame-Options',
            'X-Content-Type-Options',
            'X-XSS-Protection',
            'Referrer-Policy'
        ]
        
        for header in security_headers:
            assert header in config 