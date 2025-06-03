"""
pytest configuration and common fixtures
"""

import pytest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add scripts directory to Python path
project_root = Path(__file__).parent.parent
scripts_dir = project_root / "scripts"
sys.path.insert(0, str(scripts_dir))

@pytest.fixture(scope="function")
def temp_dir():
    """Temporary directory fixture"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture(scope="function")
def test_dirs(temp_dir):
    """Test directory structure fixture"""
    config_dir = temp_dir / "config"
    logs_dir = temp_dir / "logs"
    certs_dir = temp_dir / "certs"
    www_dir = temp_dir / "www"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    certs_dir.mkdir(parents=True, exist_ok=True)
    www_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        'temp_dir': temp_dir,
        'config_dir': config_dir,
        'logs_dir': logs_dir,
        'certs_dir': certs_dir,
        'www_dir': www_dir
    }

@pytest.fixture(scope="function")
def mock_environment(test_dirs):
    """Mock environment variables fixture"""
    env_vars = {
        'CONFIG_DIR': str(test_dirs['config_dir']),
        'LOGS_DIR': str(test_dirs['logs_dir']),
        'CERTS_DIR': str(test_dirs['certs_dir']),
        'WWW_DIR': str(test_dirs['www_dir']),
        'ACME_HOME': str(test_dirs['temp_dir'] / 'acme'),
        'TZ': 'Asia/Shanghai',
        'NGINX_RELOAD_SIGNAL': 'HUP',
        'DEBUG': 'false'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def mock_subprocess():
    """Mock subprocess fixture"""
    with patch('subprocess.run') as mock:
        mock.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock

@pytest.fixture
def mock_file_system():
    """Mock file system operations fixture"""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.is_file', return_value=True), \
         patch('pathlib.Path.is_dir', return_value=True):
        yield

@pytest.fixture(scope="function")
def cert_manager_instance(test_dirs, mock_environment):
    """SSL certificate manager instance fixture"""
    # Delayed import to avoid path issues during module-level import
    import cert_manager
    
    # Re-setup logging to avoid path conflicts
    cert_manager.setup_logging(str(test_dirs['logs_dir']))
    
    manager = cert_manager.SSLCertificateManager(
        config_dir=str(test_dirs['config_dir']),
        certs_dir=str(test_dirs['certs_dir']),
        logs_dir=str(test_dirs['logs_dir'])
    )
    
    return manager

@pytest.fixture(scope="function")
def nginx_manager_instance(test_dirs, mock_environment):
    """Nginx manager instance fixture"""
    # Delayed import to avoid path issues during module-level import
    import entrypoint
    
    # Re-setup logging to avoid path conflicts
    entrypoint.setup_logging(str(test_dirs['logs_dir']))
    
    manager = entrypoint.NginxManager(
        config_dir=str(test_dirs['config_dir']),
        logs_dir=str(test_dirs['logs_dir']),
        certs_dir=str(test_dirs['certs_dir']),
        www_dir=str(test_dirs['www_dir'])
    )
    
    return manager

@pytest.fixture
def sample_vhost_config():
    """Sample virtual host configuration"""
    return {
        "name": "test-site",
        "domains": ["test.example.com", "www.test.example.com"],
        "type": "static",
        "root": "/var/www/html",
        "ssl": True,
        "locations": [
            {
                "path": "/api",
                "type": "proxy",
                "upstream": "http://backend:8080"
            },
            {
                "path": "/static",
                "type": "static",
                "root": "/var/www/static"
            }
        ]
    }

@pytest.fixture
def sample_ssl_config():
    """Sample SSL configuration"""
    return {
        "ssl": {
            "email": "test@example.com",
            "ca_server": "letsencrypt",
            "key_length": 2048,
            "auto_upgrade": True
        },
        "acme": {
            "staging": True,
            "force": False,
            "debug": False
        },
        "advanced": {
            "renewal_check_interval": 24,
            "renewal_days_before_expiry": 30,
            "concurrent_cert_limit": 3,
            "retry_attempts": 3,
            "retry_interval": 300
        }
    }

@pytest.fixture
def create_test_configs(test_dirs, sample_vhost_config, sample_ssl_config):
    """Create test configuration files"""
    import yaml
    
    # Create vhosts configuration
    vhosts_file = test_dirs['config_dir'] / 'vhosts.yml'
    with open(vhosts_file, 'w') as f:
        yaml.dump([sample_vhost_config], f)
    
    # Create SSL configuration
    ssl_file = test_dirs['config_dir'] / 'ssl.yml'
    with open(ssl_file, 'w') as f:
        yaml.dump(sample_ssl_config, f)
    
    return {
        'vhosts_file': vhosts_file,
        'ssl_file': ssl_file
    }

@pytest.fixture
def mock_docker():
    """Mock Docker-related operations"""
    with patch('docker.from_env') as mock_docker_client:
        mock_client = Mock()
        mock_docker_client.return_value = mock_client
        
        # Mock container-related methods
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.logs.return_value = b"Container logs"
        mock_container.exec_run.return_value = Mock(exit_code=0, output=b"Success")
        
        mock_client.containers.run.return_value = mock_container
        mock_client.containers.get.return_value = mock_container
        
        # Mock image-related methods
        mock_image = Mock()
        mock_client.images.build.return_value = (mock_image, [])
        
        yield mock_client

# pytest plugin configuration
def pytest_configure(config):
    """pytest configuration"""
    config.addinivalue_line(
        "markers", "slow: Mark tests that run for a long time"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end test"
    )
    config.addinivalue_line(
        "markers", "integration: Integration test"
    )
    config.addinivalue_line(
        "markers", "unit: Unit test"
    )
    config.addinivalue_line(
        "markers", "network: Test that requires network connection"
    )
    config.addinivalue_line(
        "markers", "docker: Test that requires Docker environment"
    ) 