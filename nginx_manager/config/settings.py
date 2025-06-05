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
            Path.home() / ".nginx-manager" / "config",
            # System config directory
            Path("/etc/nginx-manager"),
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
        """Load configuration from file"""
        config = {}
        
        # Load main config file
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        
        # Load SSL config if exists
        ssl_config_file = self.config_dir / "ssl.yml"
        if ssl_config_file.exists():
            with open(ssl_config_file, 'r', encoding='utf-8') as f:
                ssl_config = yaml.safe_load(f) or {}
                config.update(ssl_config)
        
        return config
    
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
    
    # Commonly used configuration properties
    @property
    def nginx_config_dir(self) -> Path:
        """Get nginx configuration directory"""
        # First check for explicit configuration or environment override
        config_value = self.get('nginx.config_dir', None, use_env=True)
        if config_value:
            return Path(config_value)
        
        # Auto-detect based on system
        system = platform.system()
        if system == 'Darwin':  # macOS
            return Path('/usr/local/etc/nginx/servers')
        else:  # Linux and other Unix-like systems
            return Path('/etc/nginx/conf.d')
    
    @property
    def ssl_certs_dir(self) -> Path:
        """Get SSL certificates directory"""
        return Path(self.get('ssl.certs_dir', self.config_dir.parent / 'certs'))
    
    @property
    def logs_dir(self) -> Path:
        """Get logs directory"""
        return Path(self.get('logs.dir', self.config_dir.parent / 'logs'))
    
    @property
    def www_dir(self) -> Path:
        """Get web root directory"""
        return Path(self.get('www.dir', self.config_dir.parent / 'www'))
    
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled"""
        return self.get('environment.debug', False)
    
    @property
    def ssl_email(self) -> str:
        """Get SSL email for certificate registration"""
        return self.get('ssl.email', 'admin@example.com')
    
    @property
    def ssl_ca_server(self) -> str:
        """Get SSL CA server"""
        return self.get('ssl.ca_server', 'letsencrypt')
    
    @property
    def acme_staging(self) -> bool:
        """Check if using ACME staging environment"""
        return self.get('acme.staging', False)


# Global settings instance
settings = Settings() 