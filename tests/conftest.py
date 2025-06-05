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

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
    nginx_conf_dir = temp_dir / "nginx"
    
    # Create all test directories
    for dir_path in [config_dir, logs_dir, certs_dir, www_dir, nginx_conf_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return {
        'temp_dir': temp_dir,
        'config_dir': config_dir,
        'logs_dir': logs_dir,
        'certs_dir': certs_dir,
        'www_dir': www_dir,
        'nginx_conf_dir': nginx_conf_dir
    }

@pytest.fixture(scope="function")
def mock_environment(test_dirs):
    """Mock environment variables fixture"""
    env_vars = {
        'NGINX_MANAGER_CONFIG_DIR': str(test_dirs['config_dir']),
        'NGINX_MANAGER_LOGS_DIR': str(test_dirs['logs_dir']),
        'NGINX_MANAGER_SSL_CERTS_DIR': str(test_dirs['certs_dir']),
        'NGINX_MANAGER_WWW_DIR': str(test_dirs['www_dir']),
        'NGINX_MANAGER_NGINX_CONFIG_DIR': str(test_dirs['nginx_conf_dir']),
        'NGINX_MANAGER_ENVIRONMENT_DEBUG': 'false',
        'TZ': 'Asia/Shanghai'
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
def nginx_manager_instance(test_dirs, mock_environment):
    """Nginx manager instance fixture"""
    from nginx_manager.core.manager import NginxManager
    
    with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
        mock_acme.return_value = Path('/usr/local/bin/acme.sh')
        manager = NginxManager()
        yield manager

@pytest.fixture(scope="function")
def ssl_manager_instance(test_dirs, mock_environment):
    """SSL manager instance fixture"""
    from nginx_manager.ssl.manager import SSLManager
    
    with patch.object(SSLManager, '_find_acme_sh') as mock_acme:
        mock_acme.return_value = Path('/usr/local/bin/acme.sh')
        manager = SSLManager()
        yield manager

@pytest.fixture(scope="function")
def config_generator_instance():
    """Configuration generator instance fixture"""
    from nginx_manager.templates.generator import ConfigGenerator
    return ConfigGenerator()

@pytest.fixture(scope="function")
def environment_manager_instance():
    """Environment manager instance fixture"""
    from nginx_manager.utils.environment import EnvironmentManager
    return EnvironmentManager()

@pytest.fixture(scope="function")
def settings_instance(test_dirs, mock_environment):
    """Settings instance fixture"""
    from nginx_manager.config.settings import Settings
    return Settings()

@pytest.fixture
def sample_site_config():
    """Sample site configuration"""
    return {
        "domain": "test.example.com",
        "backend": "http://localhost:3000",
        "ssl": True,
        "template": "proxy_ssl.conf.j2"
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
def create_test_configs(test_dirs, sample_site_config, sample_ssl_config):
    """Create test configuration files"""
    import yaml
    
    # Create site configuration file
    site_config_file = test_dirs['config_dir'] / 'sites.yml'
    with open(site_config_file, 'w') as f:
        yaml.dump([sample_site_config], f)
    
    # Create SSL configuration file
    ssl_config_file = test_dirs['config_dir'] / 'ssl.yml'
    with open(ssl_config_file, 'w') as f:
        yaml.dump(sample_ssl_config, f)
    
    # Create main config file
    main_config = {
        'debug': False,
        'log_level': 'INFO',
        'nginx': {
            'user': 'nginx',
            'worker_processes': 'auto'
        }
    }
    main_config_file = test_dirs['config_dir'] / 'config.yml' 
    with open(main_config_file, 'w') as f:
        yaml.dump(main_config, f)
    
    return {
        'site_config_file': site_config_file,
        'ssl_config_file': ssl_config_file,
        'main_config_file': main_config_file
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
        mock_client.containers.list.return_value = [mock_container]
        
        # Mock image-related methods
        mock_image = Mock()
        mock_client.images.build.return_value = (mock_image, [])
        mock_client.images.get.return_value = mock_image
        
        yield mock_client

@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test"""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

def pytest_configure(config):
    """Pytest configuration"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "docker: mark test as Docker-specific test"
    )
    config.addinivalue_line(
        "markers", "native: mark test as native environment test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow test"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers based on test file location
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "test_docker" in str(item.fspath):
            item.add_marker(pytest.mark.docker)
        elif "test_native" in str(item.fspath):
            item.add_marker(pytest.mark.native) 