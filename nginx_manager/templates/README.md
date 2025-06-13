# Nginx Configuration Templates

This module provides Jinja2 templates for generating nginx configuration files and initialization templates for the nginx-manager project.

## Available Templates

### Nginx Site Configuration Templates
- `proxy_ssl.conf.j2` - SSL-enabled reverse proxy configuration
- `proxy_http.conf.j2` - HTTP-only reverse proxy configuration  
- `static_ssl.conf.j2` - SSL-enabled static file serving configuration
- `static_http.conf.j2` - HTTP-only static file serving configuration

### Configuration File Templates
- `config.yml.j2` - Main configuration file template for nginx-manager
- `vhosts.yml.j2` - Virtual hosts configuration template with examples

## Usage

### ConfigGenerator Class

The `ConfigGenerator` class provides methods to generate various types of configurations:

```python
from nginx_manager.templates import ConfigGenerator

generator = ConfigGenerator()

# Generate nginx site configuration
config_content = generator.generate_site_config(
    domain="example.com",
    backend="http://localhost:8080",
    ssl=True
)

# Generate main config.yml file
config_content = generator.generate_config_file(
    ssl_email="admin@example.com",
    ssl_ca_server="letsencrypt",
    ssl_staging=False,
    ssl_certs_dir="/app/certs"
)

# Generate vhosts.yml template file
vhosts_content = generator.generate_vhosts_file(
    default_ssl=True,
    www_dir="/var/www/html"
)
```

### Template Variables

#### config.yml.j2 Variables
- `nginx_log_dir` - Nginx log directory path
- `ssl_certs_dir` - SSL certificates storage directory
- `ssl_email` - Email address for SSL certificate registration
- `ssl_ca_server` - Certificate authority server (letsencrypt, zerossl, buypass)
- `ssl_staging` - Whether to use staging environment
- `logs_dir` - Application logs directory
- `advanced_www_dir` - Web root directory
- Plus many other SSL and service configuration options

#### vhosts.yml.j2 Variables
- `default_ssl` - Default SSL setting for example configurations
- `www_dir` - Web root directory for static file examples

#### Site Configuration Templates Variables
- `domain` - Primary domain name
- `backend` - Backend server URL (for proxy configurations)
- `ssl` - Whether SSL is enabled
- `ssl_cert_path` - SSL certificate file path
- `ssl_key_path` - SSL private key file path
- `access_log` - Access log file path
- `error_log` - Error log file path

## Template Directory Structure

```
templates/
├── __init__.py
├── generator.py          # ConfigGenerator class
├── README.md            # This file
└── templates/           # Jinja2 template files
    ├── config.yml.j2        # Main config template
    ├── vhosts.yml.j2        # Vhosts config template
    ├── proxy_ssl.conf.j2    # SSL proxy site template
    ├── proxy_http.conf.j2   # HTTP proxy site template
    ├── static_ssl.conf.j2   # SSL static site template
    └── static_http.conf.j2  # HTTP static site template
```

## Adding Custom Templates

To add custom templates:

1. Create new `.j2` files in the `templates/` directory
2. Use Jinja2 syntax for variable substitution
3. Add corresponding generation methods to `ConfigGenerator` class if needed
4. Update this README with template variable documentation

## Template Inheritance

Templates can use Jinja2 inheritance features. Common configuration blocks can be extracted to base templates and extended by specific configuration templates.

## Error Handling

The `ConfigGenerator` includes proper error handling for missing templates and provides helpful error messages when templates cannot be found or rendered. 