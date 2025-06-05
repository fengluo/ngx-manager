"""
Tests for SSL manager
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta

from nginx_manager.ssl.manager import SSLManager
from nginx_manager.config.settings import settings


class TestSSLManager:
    """Test SSL manager functionality"""
    
    def test_manager_initialization(self, ssl_manager_instance):
        """Test SSL manager initialization"""
        manager = ssl_manager_instance
        
        # Check that manager has required attributes
        assert hasattr(manager, 'acme_sh_path')
        assert hasattr(manager, 'certs_dir')
        
        # Check that it uses the global settings object
        assert manager.certs_dir is not None
    
    def test_acme_sh_finding(self, ssl_manager_instance):
        """Test acme.sh executable finding"""
        manager = ssl_manager_instance
        
        # Should have found acme.sh path (mocked in fixture)
        assert manager.acme_sh_path is not None
    
    @patch('subprocess.run')
    def test_obtain_certificate_success(self, mock_subprocess, ssl_manager_instance):
        """Test successful certificate obtainment"""
        # Mock certificate doesn't exist initially
        with patch.object(ssl_manager_instance, '_certificate_exists', return_value=False):
            # Mock successful acme.sh commands
            mock_subprocess.side_effect = [
                Mock(returncode=0, stdout="Certificate obtained"),  # --issue
                Mock(returncode=0, stdout="Certificate installed")  # --install-cert
            ]
            
            manager = ssl_manager_instance
            result = manager.obtain_certificate('test.example.com')
            
            assert result['success'] is True
            assert result['domain'] == 'test.example.com'
    
    @patch('subprocess.run')
    def test_obtain_certificate_failure(self, mock_subprocess, ssl_manager_instance):
        """Test certificate obtainment failure"""
        # Mock certificate doesn't exist initially
        with patch.object(ssl_manager_instance, '_certificate_exists', return_value=False):
            # Mock failed acme.sh command
            mock_subprocess.side_effect = [
                Mock(returncode=1, stderr="Rate limit exceeded"),  # --issue fails
                Mock(returncode=1, stderr="Standalone mode failed")  # standalone fallback fails
            ]
            
            manager = ssl_manager_instance
            result = manager.obtain_certificate('test.example.com')
            
            assert result['success'] is False
            assert 'Rate limit exceeded' in result['error'] or 'Standalone mode failed' in result['error']
    
    @patch('subprocess.run')
    def test_renew_certificate_success(self, mock_subprocess, ssl_manager_instance):
        """Test successful certificate renewal"""
        # Mock certificate needs renewal
        with patch.object(ssl_manager_instance, '_certificate_needs_renewal', return_value=True):
            # Mock successful renewal
            mock_subprocess.side_effect = [
                Mock(returncode=0, stdout="Certificate renewed"),  # --renew
                Mock(returncode=0, stdout="Certificate installed")  # --install-cert
            ]
            
            manager = ssl_manager_instance
            result = manager.renew_certificate('test.example.com')
            
            assert result['success'] is True
            assert result['renewed'] is True
            assert result['domain'] == 'test.example.com'
    
    @patch('subprocess.run')
    def test_renew_certificate_failure(self, mock_subprocess, ssl_manager_instance):
        """Test certificate renewal failure"""
        # Mock certificate needs renewal
        with patch.object(ssl_manager_instance, '_certificate_needs_renewal', return_value=True):
            # Mock failed renewal
            mock_subprocess.return_value = Mock(returncode=1, stderr="Renewal failed")
            
            manager = ssl_manager_instance
            result = manager.renew_certificate('test.example.com')
            
            assert result['success'] is False
            assert 'Renewal failed' in result['error']
    
    @patch('subprocess.run')
    @patch('shutil.rmtree')
    @patch('pathlib.Path.exists')
    def test_remove_certificate_success(self, mock_exists, mock_rmtree, mock_subprocess, ssl_manager_instance):
        """Test successful certificate removal"""
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)
        
        manager = ssl_manager_instance
        result = manager.remove_certificate('test.example.com')
        
        assert result['success'] is True
        assert result['domain'] == 'test.example.com'
        mock_rmtree.assert_called_once()
    
    @patch('pathlib.Path.exists')
    def test_remove_certificate_not_found(self, mock_exists, ssl_manager_instance):
        """Test removing certificate that doesn't exist"""
        mock_exists.return_value = False
        
        manager = ssl_manager_instance
        result = manager.remove_certificate('nonexistent.example.com')
        
        assert result['success'] is True  # Should succeed even if cert doesn't exist
        assert result['domain'] == 'nonexistent.example.com'
    
    def test_certificate_exists_check(self, ssl_manager_instance):
        """Test certificate existence check"""
        manager = ssl_manager_instance
        
        # Mock certificate file exists
        with patch('pathlib.Path.exists', return_value=True):
            assert manager._certificate_exists('test.example.com') is True
        
        # Mock certificate file doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            assert manager._certificate_exists('test.example.com') is False
    
    @patch('subprocess.run')
    def test_certificate_needs_renewal_check(self, mock_subprocess, ssl_manager_instance):
        """Test certificate renewal check"""
        manager = ssl_manager_instance
        
        # Mock certificate exists
        with patch.object(manager, '_certificate_exists', return_value=True):
            # Mock certificate expires soon
            future_date = datetime.utcnow() + timedelta(days=10)
            mock_subprocess.return_value = Mock(
                returncode=0,
                stdout=f"notAfter={future_date.strftime('%b %d %H:%M:%S %Y GMT')}"
            )
            
            assert manager._certificate_needs_renewal('test.example.com') is True
        
        # Mock certificate doesn't exist
        with patch.object(manager, '_certificate_exists', return_value=False):
            assert manager._certificate_needs_renewal('test.example.com') is True
    
    @patch('pathlib.Path.iterdir')
    def test_list_certificates(self, mock_iterdir, ssl_manager_instance):
        """Test listing certificates"""
        # Mock certificate directories
        mock_cert_dirs = [
            Mock(is_dir=Mock(return_value=True), name='site1.example.com'),
            Mock(is_dir=Mock(return_value=True), name='site2.example.com'),
        ]
        mock_iterdir.return_value = mock_cert_dirs
        
        manager = ssl_manager_instance
        
        with patch.object(manager, '_certificate_exists', return_value=True), \
             patch.object(manager, '_certificate_needs_renewal', return_value=False):
            
            certificates = manager.list_certificates()
            
            assert len(certificates) == 2
            assert certificates[0]['domain'] == 'site1.example.com'
            assert certificates[1]['domain'] == 'site2.example.com'


class TestSSLManagerValidation:
    """Test SSL manager validation"""
    
    def test_acme_sh_availability_check(self, ssl_manager_instance):
        """Test acme.sh availability check"""
        manager = ssl_manager_instance
        
        # Should have acme.sh path (mocked in fixture)
        assert manager.acme_sh_path is not None


class TestSSLManagerConfiguration:
    """Test SSL manager configuration options"""
    
    @patch('subprocess.run')
    def test_staging_mode(self, mock_subprocess, ssl_manager_instance):
        """Test staging mode configuration"""
        # Mock staging mode enabled
        with patch.object(settings, 'acme_staging', True):
            with patch.object(ssl_manager_instance, '_certificate_exists', return_value=False):
                mock_subprocess.side_effect = [
                    Mock(returncode=0, stdout="Certificate obtained"),
                    Mock(returncode=0, stdout="Certificate installed")
                ]
                
                manager = ssl_manager_instance
                result = manager.obtain_certificate('test.example.com')
                
                # Check that staging flag was used
                call_args = mock_subprocess.call_args_list[0][0][0]
                assert '--staging' in call_args
    
    @patch('subprocess.run')
    def test_force_renewal(self, mock_subprocess, ssl_manager_instance):
        """Test force renewal"""
        with patch.object(ssl_manager_instance, '_certificate_needs_renewal', return_value=False):
            mock_subprocess.side_effect = [
                Mock(returncode=0, stdout="Certificate renewed"),
                Mock(returncode=0, stdout="Certificate installed")
            ]
            
            manager = ssl_manager_instance
            result = manager.renew_certificate('test.example.com', force=True)
            
            # Check that force flag was used
            call_args = mock_subprocess.call_args_list[0][0][0]
            assert '--force' in call_args


class TestSSLManagerErrorHandling:
    """Test SSL manager error handling"""
    
    def test_acme_sh_not_found_error(self):
        """Test error when acme.sh is not found"""
        with patch.object(SSLManager, '_find_acme_sh', return_value=None):
            manager = SSLManager()
            
            result = manager.obtain_certificate('test.example.com')
            
            assert result['success'] is False
            assert 'acme.sh not found' in result['error']
    
    @patch('subprocess.run')
    def test_network_error_handling(self, mock_subprocess, ssl_manager_instance):
        """Test network error handling"""
        mock_subprocess.side_effect = Exception("Network unreachable")
        
        manager = ssl_manager_instance
        result = manager.obtain_certificate('test.example.com')
        
        assert result['success'] is False
        assert 'Network unreachable' in result['error']
    
    @patch('subprocess.run')
    def test_permission_error_handling(self, mock_subprocess, ssl_manager_instance):
        """Test permission error handling"""
        mock_subprocess.side_effect = PermissionError("Permission denied")
        
        manager = ssl_manager_instance
        result = manager.obtain_certificate('test.example.com')
        
        assert result['success'] is False
        assert 'Permission denied' in result['error']
    
    @patch('subprocess.run')
    def test_rate_limit_error(self, mock_subprocess, ssl_manager_instance):
        """Test rate limit error handling"""
        with patch.object(ssl_manager_instance, '_certificate_exists', return_value=False):
            mock_subprocess.side_effect = [
                Mock(returncode=1, stderr="too many certificates already issued"),
                Mock(returncode=1, stderr="rate limit exceeded")
            ]
            
            manager = ssl_manager_instance
            result = manager.obtain_certificate('test.example.com')
            
            assert result['success'] is False
            assert ('too many' in result['error'].lower() or 'rate limit' in result['error'].lower())


class TestSSLManagerUtils:
    """Test SSL manager utility functions"""
    
    def test_ca_server_selection(self, ssl_manager_instance):
        """Test CA server URL selection"""
        manager = ssl_manager_instance
        
        # Test Let's Encrypt production
        with patch.object(settings, 'ssl_ca_server', 'letsencrypt'), \
             patch.object(settings, 'acme_staging', False):
            ca_server = manager._get_ca_server()
            assert 'acme-v02.api.letsencrypt.org' in ca_server
        
        # Test Let's Encrypt staging
        with patch.object(settings, 'ssl_ca_server', 'letsencrypt'), \
             patch.object(settings, 'acme_staging', True):
            ca_server = manager._get_ca_server()
            assert 'acme-staging-v02.api.letsencrypt.org' in ca_server
    
    @patch('subprocess.run')
    def test_command_timeout_handling(self, mock_subprocess, ssl_manager_instance):
        """Test command timeout handling"""
        mock_subprocess.side_effect = subprocess.TimeoutExpired('acme.sh', 300)
        
        manager = ssl_manager_instance
        result = manager.obtain_certificate('test.example.com')
        
        assert result['success'] is False
        assert 'timeout' in result['error'].lower() or 'TimeoutExpired' in result['error'] 