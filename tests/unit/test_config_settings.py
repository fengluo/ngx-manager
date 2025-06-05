"""
Tests for configuration system
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from nginx_manager.config.settings import Settings


class TestSettings:
    """Test configuration settings"""
    
    def test_settings_initialization(self, mock_environment):
        """Test settings initialization"""
        settings = Settings()
        
        assert settings.config_dir.exists()
        # These directories may not exist initially but should be accessible
        assert isinstance(settings.logs_dir, Path)
        assert isinstance(settings.ssl_certs_dir, Path)
        assert isinstance(settings.www_dir, Path)
        assert isinstance(settings.nginx_config_dir, Path)
    
    def test_debug_mode_detection(self):
        """Test debug mode detection"""
        # Test debug enabled
        with patch.dict(os.environ, {'NGINX_MANAGER_ENVIRONMENT_DEBUG': 'true'}):
            settings = Settings()
            assert settings.debug is True
        
        # Test debug disabled
        with patch.dict(os.environ, {'NGINX_MANAGER_ENVIRONMENT_DEBUG': 'false'}):
            settings = Settings()
            assert settings.debug is False
        
        # Test default (no environment variable)
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.debug is False
    
    def test_environment_variable_override(self):
        """Test environment variable overrides"""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_config_dir = Path(temp_dir) / "custom_config"
            custom_config_dir.mkdir()
            
            with patch.dict(os.environ, {'NGINX_MANAGER_CONFIG_DIR': str(custom_config_dir)}):
                settings = Settings()
                assert settings.config_dir == custom_config_dir
    
    def test_path_properties(self, settings_instance):
        """Test path properties"""
        settings = settings_instance
        
        # Test that all paths are Path objects
        assert isinstance(settings.config_dir, Path)
        assert isinstance(settings.logs_dir, Path)
        assert isinstance(settings.ssl_certs_dir, Path)
        assert isinstance(settings.www_dir, Path)
        assert isinstance(settings.nginx_config_dir, Path)
    
    def test_nginx_config_paths(self):
        """Test nginx config paths with system auto-detection"""
        # Clear any configuration override
        with patch.dict(os.environ, {}, clear=False):
            if 'NGINX_MANAGER_NGINX_CONFIG_DIR' in os.environ:
                del os.environ['NGINX_MANAGER_NGINX_CONFIG_DIR']
            
            # Test macOS detection
            with patch('platform.system', return_value='Darwin'):
                settings = Settings()
                assert str(settings.nginx_config_dir) == '/usr/local/etc/nginx/servers'
            
            # Test Linux detection
            with patch('platform.system', return_value='Linux'):
                settings = Settings()
                assert str(settings.nginx_config_dir) == '/etc/nginx/conf.d'
            
            # Test other Unix-like systems (default to Linux path)
            with patch('platform.system', return_value='FreeBSD'):
                settings = Settings()
                assert str(settings.nginx_config_dir) == '/etc/nginx/conf.d'
    
    def test_nginx_config_paths_override(self):
        """Test nginx config paths with override"""
        # Test environment variable override
        custom_path = '/custom/nginx/path'
        with patch.dict(os.environ, {'NGINX_MANAGER_NGINX_CONFIG_DIR': custom_path}):
            settings = Settings()
            assert str(settings.nginx_config_dir) == custom_path
    
    def test_config_get_method(self):
        """Test configuration get method"""
        settings = Settings()
        
        # Test default values
        assert settings.get('nonexistent.key', 'default') == 'default'
        
        # Test environment variable override
        with patch.dict(os.environ, {'NGINX_MANAGER_SSL_EMAIL': 'test@example.com'}):
            assert settings.get('ssl.email') == 'test@example.com'
    
    def test_config_set_and_get(self):
        """Test configuration set and get methods"""
        settings = Settings()
        
        # Test setting and getting values
        settings.set('test.key', 'test_value')
        assert settings.get('test.key') == 'test_value'
        
        # Test nested keys
        settings.set('nested.deep.key', 'nested_value')
        assert settings.get('nested.deep.key') == 'nested_value'
    
    def test_settings_consistency(self):
        """Test that settings behave consistently"""
        # Multiple Settings instances should use same environment
        settings1 = Settings()
        settings2 = Settings()
        
        # Should have consistent behavior
        assert type(settings1.debug) == type(settings2.debug)


class TestSettingsValidation:
    """Test settings validation"""
    
    def test_invalid_paths_handling(self):
        """Test handling of invalid paths"""
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "nonexistent"
            with patch.dict(os.environ, {'NGINX_MANAGER_CONFIG_DIR': str(invalid_path)}):
                # Should create directories if they don't exist
                settings = Settings()
                # Directory should be created
                assert settings.config_dir.exists()
    
    def test_environment_variable_types(self):
        """Test environment variable type conversion"""
        settings = Settings()
        
        # Test boolean conversion
        test_cases = [
            ('true', True),
            ('True', True), 
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('off', False),
        ]
        
        for env_value, expected in test_cases:
            converted = settings._convert_env_value(env_value)
            assert converted == expected, f"Failed for {env_value} -> {expected}"
        
        # Test numeric conversion
        assert settings._convert_env_value('123') == 123
        assert settings._convert_env_value('123.45') == 123.45
        assert settings._convert_env_value('not_a_number') == 'not_a_number' 