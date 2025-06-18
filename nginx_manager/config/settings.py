"""
Unified configuration management supporting both environment variables and config files
"""

import os
import platform
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv


class Settings:
    """Unified configuration management class"""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize settings
        
        Args:
            config_dir: Configuration directory path
        """
        # Load environment variables from .env file
        try:
            load_dotenv()
        except (AssertionError, AttributeError):
            # Handle cases where dotenv can't find the calling frame (e.g., in tests)
            pass
        
        # Set default paths
        if config_dir is None:
            # Try to find config directory in different locations
            config_dir = self._find_config_dir()
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.yml"
        
        # Load configuration
        self._config = self._load_config()
    
    def _find_config_dir(self) -> Path:
        """Find configuration directory in different locations"""
        possible_paths = [
            # Environment variable
            os.getenv("NGINX_MANAGER_CONFIG_DIR"),
            # Current working directory
            Path.cwd() / "config",
            # User home directory
            Path.home() / ".ngx-manager" / "config",
            # System config directory
            Path("/etc/ngx-manager"),
            # Package directory (for development)
            Path(__file__).parent.parent.parent.parent / "config",
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                return Path(path)
        
        # Default to current working directory
        config_dir = Path.cwd() / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from unified config.yml file"""
        config = {}
        
        # Load main config file
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            # Create default config if it doesn't exist
            self._create_default_config()
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        
        return config
    
    def _get_default_nginx_config_dir(self) -> Path:
        """Get default nginx configuration directory based on system"""
        system = platform.system()
        if system == 'Darwin':  # macOS
            return Path('/usr/local/etc/nginx/servers')
        else:  # Linux and other Unix-like systems
            return Path('/etc/nginx/conf.d')
    
    def _get_default_ssl_certs_dir(self) -> Path:
        """Get default SSL certificates directory based on system"""
        system = platform.system()
        if system == 'Darwin':  # macOS
            return Path.home() / ".nginx-manager" / "certs"
        else:  # Linux and other Unix-like systems (including Docker)
            return Path("/app/certs")
    
    def _get_default_logs_dir(self) -> Path:
        """Get default logs directory based on system"""
        system = platform.system()
        if system == 'Darwin':  # macOS
            return Path.home() / ".nginx-manager" / "logs"
        else:  # Linux and other Unix-like systems (including Docker)
            return Path("/app/logs")
    
    def _get_default_www_dir(self) -> Path:
        """Get default www directory based on system"""
        system = platform.system()
        if system == 'Darwin':  # macOS
            return Path("/usr/local/var/www")
        else:  # Linux and other Unix-like systems
            return Path("/var/www/html")
    
    def _create_default_config(self) -> None:
        """Create default configuration file"""
        default_config = {
            'nginx': {
                'config_dir': str(self._get_default_nginx_config_dir()),
                'log_dir': str(self._get_default_logs_dir()),
                'log_level': 'info',
                'www_dir': str(self._get_default_www_dir())
            },
            'ssl': {
                'certs_dir': str(self._get_default_ssl_certs_dir()),
                'email': 'admin@example.com',
                'ca_server': 'letsencrypt',
                'key_length': 2048,
                'auto_upgrade': True,
                'staging': False,
                'force': False,
                'debug': False,
                'renewal_check_interval': 24,
                'renewal_days_before_expiry': 30,
                'concurrent_cert_limit': 3,
                'retry_attempts': 3,
                'retry_interval': 300
            }
        }
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    def get(self, key: str, default: Any = None, use_env: bool = True) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key (supports dot notation like 'ssl.email')
            default: Default value if key not found
            use_env: Whether to check environment variables first
            
        Returns:
            Configuration value
        """
        # Check environment variable first if enabled
        if use_env:
            env_key = key.upper().replace('.', '_')
            env_value = os.getenv(f"NGINX_MANAGER_{env_key}")
            if env_value is not None:
                return self._convert_env_value(env_value)
        
        # Check config file
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type"""
        # Handle boolean values
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Handle numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def save(self) -> None:
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
    
    # Nginx configuration properties
    @property
    def nginx_config_dir(self) -> Path:
        """Get nginx configuration directory"""
        # First check for explicit configuration or environment override
        config_value = self.get('nginx.config_dir', None, use_env=True)
        if config_value:
            return Path(config_value)
        
        # Auto-detect based on system
        return self._get_default_nginx_config_dir()
    
    @property
    def nginx_log_dir(self) -> Path:
        """Get nginx log directory"""
        return Path(self.get('nginx.log_dir', '/var/log/nginx'))
    
    # SSL configuration properties
    @property
    def ssl_certs_dir(self) -> Path:
        """Get SSL certificates directory"""
        return Path(self.get('ssl.certs_dir', str(self._get_default_ssl_certs_dir())))
    
    @property
    def ssl_email(self) -> str:
        """Get SSL email for certificate registration"""
        return self.get('ssl.email', 'admin@example.com')
    
    @property
    def ssl_ca_server(self) -> str:
        """Get SSL CA server"""
        return self.get('ssl.ca_server', 'letsencrypt')
    
    @ssl_ca_server.setter
    def ssl_ca_server(self, value: str) -> None:
        """Set SSL CA server"""
        self.set('ssl.ca_server', value)
    
    @property
    def ssl_key_length(self) -> int:
        """Get SSL key length"""
        return self.get('ssl.key_length', 2048)
    
    @property
    def ssl_auto_upgrade(self) -> bool:
        """Check if SSL auto upgrade is enabled"""
        return self.get('ssl.auto_upgrade', True)
    
    # ACME configuration properties
    @property
    def acme_staging(self) -> bool:
        """Check if using ACME staging environment"""
        return self.get('ssl.staging', False)
    
    @acme_staging.setter
    def acme_staging(self, value: bool) -> None:
        """Set ACME staging mode"""
        self.set('ssl.staging', value)
    
    @property
    def acme_force(self) -> bool:
        """Check if forcing certificate renewal"""
        return self.get('ssl.force', False)
    
    @property
    def acme_debug(self) -> bool:
        """Check if ACME debug mode is enabled"""
        return self.get('ssl.debug', False)
    
    # Logs configuration properties
    @property
    def logs_dir(self) -> Path:
        """Get logs directory"""
        return Path(self.get('nginx.log_dir', str(self._get_default_logs_dir())))
    
    @property
    def logs_level(self) -> str:
        """Get log level"""
        return self.get('nginx.log_level', 'info')
    
    @property
    def www_dir(self) -> Path:
        """Get web root directory"""
        return Path(self.get('nginx.www_dir', str(self._get_default_www_dir())))
    
    @property
    def renewal_check_interval(self) -> int:
        """Get renewal check interval in hours"""
        return self.get('ssl.renewal_check_interval', 24)
    
    @property
    def renewal_days_before_expiry(self) -> int:
        """Get days before expiry to start renewal"""
        return self.get('ssl.renewal_days_before_expiry', 30)
    
    @property
    def concurrent_cert_limit(self) -> int:
        """Get concurrent certificate limit"""
        return self.get('ssl.concurrent_cert_limit', 3)
    
    @property
    def retry_attempts(self) -> int:
        """Get retry attempts"""
        return self.get('ssl.retry_attempts', 3)
    
    @property
    def retry_interval(self) -> int:
        """Get retry interval in seconds"""
        return self.get('ssl.retry_interval', 300)
    
    # Legacy properties for backward compatibility
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled (legacy)"""
        return self.acme_debug


# Global settings instance
settings = Settings() 