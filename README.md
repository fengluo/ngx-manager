# Nginx Manager

[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Docker-based Nginx automation management tool that simplifies virtual host configuration and SSL certificate management.

[🇨🇳 中文文档](README_zh.md)

## Features

- **Virtual Host Management**: Configure multiple domains and services with simple YAML files
- **SSL Certificate Automation**: Automatic certificate application and renewal using acme.sh
- **Flexible Deployment**: Support for pip installation, Docker, and source code deployment
- **Multiple Proxy Modes**: Support for reverse proxy, static files, and mixed configurations

## Quick Start

Choose one of the following deployment methods:

### 1. Install via pip (Recommended)

```bash
# Install from PyPI
pip install ngx-manager

# Create configuration directory
mkdir -p ~/ngx-manager/{config,logs,certs}
```

### 2. Docker Deployment

```bash
# Pull and run
docker run -d --name ngx-manager \
  -p 80:80 -p 443:443 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/certs:/app/certs \
  ngx-manager:latest
```

### 3. Install from Source

```bash
# Clone repository
git clone https://github.com/fengluo/ngx-manager.git
cd ngx-manager

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### Virtual Hosts Configuration (`config/vhosts.yml`)

```yaml
# Simple proxy configuration
- name: "api-service"
  domains:
    - "api.example.com"
  ssl: true
  type: "proxy"
  upstream: "http://backend:8080"

# Static file configuration
- name: "static-site"
  domains:
    - "static.example.com"
  ssl: true
  type: "static"
  root: "/var/www/html"

# Advanced path-based configuration
- name: "mixed-service"
  domains:
    - "app.example.com"
  ssl: true
  locations:
    - path: "/api"
      type: "proxy"
      upstream: "http://api-server:8080"
    - path: "/static"
      type: "static"
      root: "/var/www/static"
    - path: "/"
      type: "static"
      root: "/var/www/html"
      try_files: "$uri $uri/ /index.html"
```

### Main Configuration (`config/config.yml`)

```yaml
# Nginx configuration
nginx:
  log_dir: "/var/log/nginx"

# SSL certificate configuration
ssl:
  certs_dir: "/tmp/certs"
  email: "your-email@example.com"           # Required: valid email address
  ca_server: "letsencrypt"                  # letsencrypt, zerossl, buypass
  key_length: 2048
  auto_upgrade: true
  staging: false                            # Use true for testing
  force: false                              # Force certificate reapplication
  debug: false                              # Enable debug mode
  renewal_check_interval: 24                # Hours
  renewal_days_before_expiry: 30
  concurrent_cert_limit: 3
  retry_attempts: 3
  retry_interval: 300                       # Seconds

# Logging configuration  
logs:
  dir: "/tmp/logs"
  level: "info"                             # debug, info, warning, error

# Service configuration
service:
  auto_reload: true                         # Auto reload nginx
  backup_configs: true                      # Backup config files

# Advanced configuration
advanced:
  www_dir: "/var/www/html"                  # Web root directory
```

### Nginx Configuration (`config/nginx.conf`)

The main nginx configuration file will be automatically generated, but you can customize it if needed.

## Usage

### Command Line Interface

```bash

# Generate configurations
ngx-manager generate

# Apply SSL certificates
ngx-manager cert --domain example.com

# Renew all certificates
ngx-manager renew

# Show status
ngx-manager status

# View logs
ngx-manager logs
```

### Docker Commands

```bash
# View logs
docker logs ngx-manager

# Execute commands inside container
docker exec ngx-manager ngx-manager status

# Restart container
docker restart ngx-manager
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-repo/ngx-manager.git
cd ngx-manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=nginx_manager

# Run specific test file
python -m pytest tests/test_config.py

# Run integration tests (requires Docker)
python -m pytest tests/integration/
```

### Project Structure

```
ngx-manager/
├── nginx_manager/          # Main package
│   ├── __init__.py
│   ├── main.py            # CLI entry point
│   ├── config.py          # Configuration management
│   ├── generator.py       # Config generation
│   ├── cert_manager.py    # SSL certificate management
│   └── templates/         # Jinja2 templates
├── tests/                 # Test suite
├── config/                # Configuration files
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── setup.py              # Package setup
└── Dockerfile            # Docker build file
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the user has write permissions to config and log directories
2. **Port Conflicts**: Check if ports 80/443 are already in use
3. **SSL Certificate Issues**: Verify domain DNS resolution and port 80 accessibility
4. **Configuration Errors**: Validate YAML syntax and required fields

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export NGINX_MANAGER_DEBUG=1

# Or modify config.yml
ssl:
  debug: true
logs:
  level: "debug"
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation for user-facing changes
- Ensure all tests pass before submitting

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 Documentation: [GitHub Wiki](https://github.com/your-repo/ngx-manager/wiki)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/ngx-manager/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-repo/ngx-manager/discussions)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates. 