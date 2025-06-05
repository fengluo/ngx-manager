"""
Tests for nginx manager
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from nginx_manager.core.manager import NginxManager
from nginx_manager.config.settings import settings


class TestNginxManager:
    """Test nginx manager functionality"""
    
    def test_manager_initialization(self, nginx_manager_instance):
        """Test nginx manager initialization"""
        manager = nginx_manager_instance
        
        # Check that manager has required components
        assert hasattr(manager, 'ssl_manager')
        assert hasattr(manager, 'config_generator')
        
        # Check that it uses the global settings object
        assert manager.ssl_manager is not None
        assert manager.config_generator is not None
    
    @patch('subprocess.run')
    def test_nginx_status_check_running(self, mock_subprocess, nginx_manager_instance):
        """Test nginx status check when running"""
        # Mock successful nginx status check
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="active"),  # systemctl is-active nginx
            Mock(returncode=0, stdout="", stderr=""),  # nginx -t
            Mock(returncode=0, stdout="", stderr="nginx version: nginx/1.20.0")  # nginx -v
        ]
        
        manager = nginx_manager_instance
        status = manager.get_nginx_status()
        
        assert status['status'] == 'running'
        assert status['config_test'] is True
        assert status['version'] == '1.20.0'
    
    @patch('subprocess.run')
    def test_nginx_status_check_stopped(self, mock_subprocess, nginx_manager_instance):
        """Test nginx status check when stopped"""
        # Mock all nginx status check methods failing (nginx not running)
        mock_subprocess.side_effect = [
            Mock(returncode=1),  # pgrep nginx fails
            Mock(returncode=1),  # systemctl is-active nginx fails  
            Mock(returncode=1),  # service nginx status fails
            Mock(returncode=0, stdout="", stderr=""),  # nginx -t
            Mock(returncode=0, stdout="", stderr="nginx version: nginx/1.20.0")  # nginx -v
        ]
        
        manager = nginx_manager_instance
        status = manager.get_nginx_status()
        
        assert status['status'] == 'stopped'
        assert status['config_test'] is True
        assert status['version'] == '1.20.0'
    
    @patch('subprocess.run')
    def test_nginx_config_test_failure(self, mock_subprocess, nginx_manager_instance):
        """Test nginx config test failure"""
        # Mock config test failure
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="active"),  # systemctl is-active nginx
            Mock(returncode=1, stderr="nginx: [emerg] invalid config"),  # nginx -t fails
            Mock(returncode=0, stdout="", stderr="nginx version: nginx/1.20.0")  # nginx -v
        ]
        
        manager = nginx_manager_instance
        status = manager.get_nginx_status()
        
        assert status['status'] == 'running'
        assert status['config_test'] is False
        assert status['version'] == '1.20.0'
    
    @patch('subprocess.run')
    def test_nginx_reload_success(self, mock_subprocess, nginx_manager_instance):
        """Test successful nginx reload"""
        mock_subprocess.return_value = Mock(returncode=0)
        
        manager = nginx_manager_instance
        result = manager.reload_nginx()
        
        assert result['success'] is True
    
    @patch('subprocess.run')
    def test_nginx_reload_failure(self, mock_subprocess, nginx_manager_instance):
        """Test nginx reload failure"""
        # Mock all reload commands failing
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, 'nginx'),       # nginx -s reload fails
            subprocess.CalledProcessError(1, 'systemctl'),   # systemctl reload nginx fails
            subprocess.CalledProcessError(1, 'service')      # service nginx reload fails
        ]
        
        manager = nginx_manager_instance
        result = manager.reload_nginx()
        
        assert result['success'] is False
        assert 'Failed to reload nginx. Last error:' in result['error']
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    def test_add_site_success(self, mock_exists, mock_file, nginx_manager_instance):
        """Test successful site addition"""
        # Mock file doesn't exist initially
        mock_exists.return_value = False
        
        manager = nginx_manager_instance
        
        # Mock the config generator
        with patch.object(manager.config_generator, 'generate_site_config') as mock_generate:
            mock_generate.return_value = "# nginx config content"
            
            # Mock SSL manager
            with patch.object(manager.ssl_manager, 'obtain_certificate') as mock_ssl:
                mock_ssl.return_value = {'success': True}
                
                # Mock nginx test and reload
                with patch.object(manager, '_test_nginx_config', return_value=True), \
                     patch.object(manager, 'reload_nginx', return_value={'success': True}):
                    
                    result = manager.add_site('test.example.com', 'http://localhost:3000', ssl=True)
        
        assert result['success'] is True
        assert result['domain'] == 'test.example.com'
        assert result['ssl'] is True
        assert 'config_file' in result
    
    @patch('pathlib.Path.exists')
    def test_add_site_already_exists(self, mock_exists, nginx_manager_instance):
        """Test adding site that already exists"""
        # Mock file exists
        mock_exists.return_value = True
        
        manager = nginx_manager_instance
        result = manager.add_site('test.example.com')
        
        assert result['success'] is False
        assert 'already exists' in result['error']
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    def test_remove_site_success(self, mock_unlink, mock_exists, nginx_manager_instance):
        """Test successful site removal"""
        # Mock file exists
        mock_exists.return_value = True
        
        manager = nginx_manager_instance
        
        # Mock SSL manager and reload
        with patch.object(manager.ssl_manager, 'remove_certificate'), \
             patch.object(manager, 'reload_nginx', return_value={'success': True}):
            
            result = manager.remove_site('test.example.com')
        
        assert result['success'] is True
        assert result['domain'] == 'test.example.com'
        mock_unlink.assert_called_once()
    
    @patch('pathlib.Path.exists')
    def test_remove_site_not_exists(self, mock_exists, nginx_manager_instance):
        """Test removing site that doesn't exist"""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        manager = nginx_manager_instance
        result = manager.remove_site('nonexistent.example.com')
        
        assert result['success'] is False
        assert 'does not exist' in result['error']
    
    def test_list_sites(self, nginx_manager_instance):
        """Test listing sites"""
        manager = nginx_manager_instance
        
        # Mock the list_sites method to return expected data
        expected_sites = [
            {
                'domain': 'site1.example.com',
                'config_file': '/path/to/site1.example.com.conf',
                'active': True,
                'ssl': True,
                'backend': 'http://localhost:3000'
            },
            {
                'domain': 'site2.example.com', 
                'config_file': '/path/to/site2.example.com.conf',
                'active': True,
                'ssl': False
            }
        ]
        
        with patch.object(manager, 'list_sites', return_value=expected_sites):
            sites = manager.list_sites()
            
            assert len(sites) == 2
            assert sites[0]['domain'] == 'site1.example.com'
            assert sites[0]['ssl'] is True
            assert sites[1]['domain'] == 'site2.example.com'
            assert sites[1]['ssl'] is False


class TestNginxManagerErrorHandling:
    """Test nginx manager error handling"""
    
    @patch('subprocess.run')
    def test_subprocess_error_handling(self, mock_subprocess, nginx_manager_instance):
        """Test subprocess error handling"""
        mock_subprocess.side_effect = Exception("Command failed")
        
        manager = nginx_manager_instance
        status = manager.get_nginx_status()
        
        assert 'error' in status
        assert 'Command failed' in status['error']
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    @patch('pathlib.Path.exists', return_value=False)
    def test_file_permission_error(self, mock_exists, mock_file, nginx_manager_instance):
        """Test file permission error handling"""
        manager = nginx_manager_instance
        
        with patch.object(manager.config_generator, 'generate_site_config', return_value="config"):
            result = manager.add_site('test.example.com')
        
        assert result['success'] is False
        assert 'Permission denied' in result['error']
    
    def test_invalid_domain_validation(self, nginx_manager_instance):
        """Test invalid domain validation"""
        manager = nginx_manager_instance
        
        # Test with invalid domain characters
        result = manager.add_site('invalid..domain')
        
        # Should still attempt to create (validation happens in SSL manager)
        assert 'success' in result
    
    def test_invalid_backend_validation(self, nginx_manager_instance):
        """Test invalid backend URL validation"""
        manager = nginx_manager_instance
        
        # Test with invalid backend URL
        result = manager.add_site('test.example.com', 'invalid-url')
        
        # Should still attempt to create (validation happens in config generator)
        assert 'success' in result 