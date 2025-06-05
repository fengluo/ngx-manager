"""
Tests for CLI functionality
"""

import pytest
import sys
from unittest.mock import patch, Mock
from click.testing import CliRunner
import subprocess

from nginx_manager.cli import cli, main
from nginx_manager.core.manager import NginxManager


class TestCLI:
    """Test CLI commands"""
    
    def test_cli_help(self):
        """Test CLI help command"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'ngx-manager' in result.output
        assert 'Commands:' in result.output
    
    @patch('nginx_manager.utils.environment.EnvironmentManager')
    @patch('nginx_manager.core.manager.NginxManager')
    def test_status_command(self, mock_manager_class, mock_env_manager_class):
        """Test status command"""
        # Mock manager instance
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_nginx_status.return_value = {
            'status': 'running',
            'config_test': True,
            'version': '1.20.0',
            'pid': '1234'
        }
        
        # Mock environment manager
        mock_env_manager = Mock()
        mock_env_manager_class.return_value = mock_env_manager
        mock_env_manager.check_environment.return_value = {
            'nginx': True,
            'python': True
        }
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert 'running' in result.output
        mock_manager.get_nginx_status.assert_called_once()
    
    @patch('nginx_manager.utils.environment.EnvironmentManager')
    @patch('nginx_manager.core.manager.NginxManager')
    def test_add_command(self, mock_manager_class, mock_env_manager_class):
        """Test add command"""
        # Mock manager instance
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.add_site.return_value = {
            'success': True,
            'domain': 'test.example.com',
            'backend': 'http://localhost:3000',
            'ssl': True
        }
        
        # Mock environment manager
        mock_env_manager = Mock()
        mock_env_manager_class.return_value = mock_env_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            'add', 
            '--domain', 'test.example.com',
            '--backend', 'http://localhost:3000',
            '--ssl'
        ])
        
        assert result.exit_code == 0
        mock_manager.add_site.assert_called_once_with(
            domain='test.example.com', 
            backend='http://localhost:3000', 
            ssl=True,
            force=False
        )
    
    @patch('nginx_manager.utils.environment.EnvironmentManager')
    @patch('nginx_manager.core.manager.NginxManager')
    def test_remove_command(self, mock_manager_class, mock_env_manager_class):
        """Test remove command"""
        # Mock manager instance
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.remove_site.return_value = {
            'success': True,
            'domain': 'test.example.com'
        }
        
        # Mock environment manager
        mock_env_manager = Mock()
        mock_env_manager_class.return_value = mock_env_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['remove', '--domain', 'test.example.com', '--force'])
        
        assert result.exit_code == 0
        mock_manager.remove_site.assert_called_once_with(domain='test.example.com')
    
    @patch('nginx_manager.utils.environment.EnvironmentManager')
    @patch('nginx_manager.core.manager.NginxManager')
    def test_list_command(self, mock_manager_class, mock_env_manager_class):
        """Test list command"""
        # Mock manager instance
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_sites.return_value = [
            {'domain': 'site1.example.com', 'ssl': True, 'active': True, 'backend': 'http://localhost:3000'},
            {'domain': 'site2.example.com', 'ssl': False, 'active': True, 'backend': 'http://localhost:8080'}
        ]
        
        # Mock environment manager
        mock_env_manager = Mock()
        mock_env_manager_class.return_value = mock_env_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['list'])
        
        assert result.exit_code == 0
        assert 'site1.example.com' in result.output
        assert 'site2.example.com' in result.output
        mock_manager.list_sites.assert_called_once()
    
    @patch('subprocess.run')
    @patch('nginx_manager.utils.environment.EnvironmentManager')
    @patch('nginx_manager.core.manager.NginxManager')
    def test_reload_command(self, mock_manager_class, mock_env_manager_class, mock_subprocess):
        """Test reload command"""
        # Mock subprocess for nginx reload
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        
        # Mock manager instance
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        # Don't mock reload_nginx, let it use the real implementation with mocked subprocess
        mock_manager_class.return_value = NginxManager()
        
        # Mock environment manager
        mock_env_manager = Mock()
        mock_env_manager_class.return_value = mock_env_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['reload'])
        
        assert result.exit_code == 0
        assert "✓" in result.output


class TestEnvironmentCLI:
    """Test environment CLI commands"""
    
    @patch('nginx_manager.utils.environment.EnvironmentManager')
    def test_setup_command(self, mock_env_manager):
        """Test setup command"""
        # Mock environment manager
        mock_manager = Mock()
        mock_env_manager.return_value = mock_manager
        mock_manager.install_dependencies.return_value = {'success': True}
        mock_manager.setup_nginx.return_value = {'success': True}
        mock_manager.setup_ssl.return_value = {'success': True}
        
        runner = CliRunner()
        result = runner.invoke(cli, ['setup'])
        
        assert result.exit_code == 0
        mock_manager.install_dependencies.assert_called_once()
        mock_manager.setup_nginx.assert_called_once()
        mock_manager.setup_ssl.assert_called_once()
    
    @patch('nginx_manager.utils.environment.EnvironmentManager')
    def test_check_command(self, mock_env_manager):
        """Test check command"""
        # Mock environment manager
        mock_manager = Mock()
        mock_env_manager.return_value = mock_manager
        mock_manager.check_environment.return_value = {
            'python': {'available': True, 'version': '3.9.0'},
            'nginx': {'available': True, 'version': '1.20.0'},
            'openssl': {'available': True, 'version': '1.1.1'},
            'curl': {'available': True, 'version': '7.68.0'}
        }
        
        runner = CliRunner()
        result = runner.invoke(cli, ['check'])
        
        assert result.exit_code == 0
        mock_manager.check_environment.assert_called_once()


class TestCLIErrorHandling:
    """Test CLI error handling"""
    
    @patch('nginx_manager.core.manager.NginxManager')
    def test_status_command_error(self, mock_manager_class):
        """Test status command with error"""
        # Mock manager with error
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_nginx_status.side_effect = Exception("Service error")
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code != 0
        assert 'error' in result.output.lower()
    
    @patch('nginx_manager.core.manager.NginxManager')
    def test_add_command_failure(self, mock_manager_class):
        """Test add command with failure"""
        # Mock manager with failure result
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.add_site.return_value = {
            'success': False,
            'error': 'Site already exists'
        }
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            'add',
            '--domain', 'existing.example.com',
            '--backend', 'http://localhost:3000'
        ])
        
        assert result.exit_code != 0
        assert 'Site already exists' in result.output
    
    def test_invalid_domain_format(self):
        """Test invalid domain format validation"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'add',
            '--domain', 'invalid..domain',
            '--backend', 'http://localhost:3000'
        ])
        
        assert result.exit_code != 0
    
    def test_invalid_backend_url(self):
        """Test invalid backend URL validation"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'add',
            '--domain', 'test.example.com',
            '--backend', 'not-a-url'
        ])
        
        assert result.exit_code != 0


class TestCLIMain:
    """Test CLI main entry point"""
    
    @patch('nginx_manager.cli.cli')
    def test_main_function(self, mock_cli):
        """Test main function"""
        with patch('sys.argv', ['ngx-manager', 'status']):
            try:
                main()
            except SystemExit:
                pass
        
        mock_cli.assert_called_once()
    
    @patch('nginx_manager.cli.cli')
    def test_main_with_args(self, mock_cli):
        """Test main function with arguments"""
        test_args = ['ngx-manager', 'add', '-d', 'test.com', '-b', 'http://localhost:3000']
        
        with patch('sys.argv', test_args):
            try:
                main()
            except SystemExit:
                pass
        
        mock_cli.assert_called_once()


class TestCLIOutput:
    """Test CLI output formatting"""
    
    @patch('nginx_manager.core.manager.NginxManager')
    def test_verbose_output(self, mock_manager_class):
        """Test verbose output option"""
        # Mock manager instance
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_nginx_status.return_value = {
            'status': 'running',
            'config_test': True,
            'version': '1.20.0',
            'pid': '1234'
        }
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status', '--verbose'])
        
        assert result.exit_code == 0
        # Verbose output should contain more details
        assert 'pid' in result.output.lower() or '1234' in result.output
    
    @patch('nginx_manager.core.manager.NginxManager')
    def test_json_output(self, mock_manager_class):
        """Test JSON output option"""
        # Mock manager instance
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_sites.return_value = [
            'site1.example.com',
            'site2.example.com'
        ]
        
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--json'])
        
        assert result.exit_code == 0
        # Should be valid JSON output
        import json
        try:
            json.loads(result.output)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON") 