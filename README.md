# Nginx Manager

[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)](run_tests.py)

A Nginx automation management and configuration tool that supports virtual host configuration, automatic SSL certificate application and management.

[🇨🇳 中文文档](README_zh.md)

## 🚀 Features

### 🌐 Simplified Virtual Host Configuration
- Simple configuration files for describing virtual host proxy services
- Support for domain configuration, API proxy forwarding, and static file access paths
- Path-based proxy forwarding and static file path configuration
- Automatic generation of standard Nginx configuration files

### ⚙️ Automated Configuration Generation
- Read configuration files and extract virtual host descriptions
- Template-based automatic generation of Nginx virtual host configurations
- Support for multiple proxy modes and static resource services

### 🔒 Automatic SSL Certificate Management
- Integrated [acme.sh](https://github.com/acmesh-official/acme.sh) for automatic SSL certificate application
- Automatic detection and application of missing certificates on container startup
- Automatic certificate renewal without manual intervention
- Support for multiple certificate authorities

### 🛠️ Flexible Manual Operations
- Manual triggering of virtual host configuration regeneration
- Manual application or update of SSL certificates for specified domains
- Support for modifying acme.sh email and certificate provider configuration
- User-friendly command-line interface

### 📋 Comprehensive Logging
- Detailed operation log recording
- Clear error message prompts
- Real-time certificate application and configuration generation status

## 📋 System Requirements

- Docker 20.10+
- Docker Compose 2.0+
- Domain name resolution to server IP (for SSL certificate application)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ngx-manager
```

### 2. Start Services

```bash
# Using Python startup script
python3 start.py

# Or using Docker Compose
python3 start.py compose-up
```

### 3. Access Services
- HTTP: http://localhost
- HTTPS: https://localhost (if SSL is configured)

### 4. View Logs

```bash
# View container logs
python3 start.py logs --follow

# Or use Docker command
docker logs -f ngx-manager
```

### 5. Stop Services

```bash
python3 start.py stop
```

## 📁 Project Structure

```
ngx-manager/
├── Dockerfile                 # Docker image build file
├── docker-compose.yml         # Docker Compose configuration
├── start.py                   # Python startup script
├── README.md                  # Project documentation (English)
├── README_zh.md              # Project documentation (Chinese)
├── LICENSE                    # License
├── .gitignore                 # Git ignore file
├── config/                    # Configuration files directory
│   ├── nginx.conf            # Nginx main configuration
│   ├── vhosts.yml            # Virtual hosts configuration
│   └── ssl.yml               # SSL certificate configuration
├── templates/                 # Configuration templates directory
│   └── vhost.conf.j2         # Virtual host template
├── scripts/                   # Scripts directory
│   ├── generate-config.py    # Configuration generation script (Python)
│   ├── cert_manager.py       # Certificate management script (Python)
│   └── entrypoint.py         # Container startup script (Python)
├── examples/                  # Example files
├── logs/                      # Logs directory (auto-created)
├── certs/                     # Certificates directory (auto-created)
├── nginx-conf/                # Generated nginx configs (auto-created)
└── tests/                     # Test suites
    ├── unit/                  # Unit tests
    ├── integration/           # Integration tests
    └── e2e/                   # End-to-end tests
```

**Important Directory Explanation**:
- `nginx-conf/` - **Core functionality directory** containing all generated Nginx virtual host configuration files
  - Each virtual host generates a corresponding `.conf` file
  - File naming format: `{vhost-name}.conf`
  - Mapped to container's `/etc/nginx/conf.d/` directory
  - Supports real-time viewing, editing, and debugging configurations

## 🔧 Configuration Guide

### Environment-Specific Setup

The project automatically detects your operating system and uses appropriate nginx configuration paths:

- **Linux/Docker**: `/etc/nginx/conf.d`
- **macOS (Homebrew)**: `/usr/local/etc/nginx/servers`

You can override the auto-detected path by either:
1. Setting it in `config/config.yml`:
   ```yaml
   nginx:
     config_dir: "/custom/nginx/path"
   ```
2. Using environment variable: `export NGINX_MANAGER_NGINX_CONFIG_DIR="/custom/nginx/path"`

### Virtual Host Configuration (vhosts.yml)

Supports two configuration formats:

**Format 1: Complete Format**
```yaml
- name: "service-name"
  domains:
    - "domain1.com"
    - "domain2.com"
  ssl: true|false         # Enable SSL
  
  # Simple mode configuration (backward compatible)
  type: "proxy|static"     # Proxy mode or static file mode
  upstream: "backend-url"  # Required for proxy mode only
  root: "static-root-dir"  # Required for static mode only
  auth_basic: true|false   # Enable basic authentication
  
  # Advanced path configuration mode
  locations:
    - path: "/path"        # Matching path, supports regex
      type: "proxy|static" # Processing type for this path
      
      # Proxy configuration (when type: proxy)
      upstream: "backend-service-url"
      proxy_pass_path: "/rewrite-path"    # Optional: rewrite path
      proxy_read_timeout: "30s"          # Optional: read timeout
      proxy_connect_timeout: "5s"        # Optional: connect timeout
      proxy_send_timeout: "30s"          # Optional: send timeout
      websocket: true|false               # Optional: WebSocket support
      
      # Static file configuration (when type: static)
      root: "file-root-directory"
      try_files: "$uri $uri/ /index.html" # Optional: try_files directive
      expires: "30d"                      # Optional: cache expiration
      autoindex: true|false               # Optional: directory browsing
      
      # Common configuration
      auth_basic: true|false              # Optional: basic authentication
      auth_basic_user_file: "auth-file"   # Optional: authentication file
      custom_config: |                    # Optional: custom Nginx config
        # Additional location configuration directives
        add_header X-Custom-Header "value";
  
  # Global custom configuration
  custom_config: |        # Optional: server-level custom config
    # Additional server configuration directives
```

**Format 2: Simplified Format (Recommended)**
```yaml
# Direct array usage, omitting vhosts key
- name: "service-name"
  domains:
    - "domain1.com"
    - "domain2.com"
  ssl: true|false
  # ... other configuration items same as complete format
```

### SSL Configuration (ssl.yml)

```yaml
ssl:
  email: "certificate-email@example.com"
  ca_server: "letsencrypt"  # letsencrypt, zerossl, buypass
  key_length: 2048          # Key length
  auto_upgrade: true        # Auto upgrade acme.sh

acme:
  staging: false            # Use staging environment
  force: false             # Force certificate reapplication
  debug: false             # Debug mode
```

### Path Matching Rules

Supports the following path matching patterns:

```yaml
locations:
  # Exact match
  - path: "= /exact"
    type: "proxy"
    upstream: "http://service:8080"
  
  # Prefix match (default)
  - path: "/api"
    type: "proxy"
    upstream: "http://api:8080"
  
  # Regex match
  - path: "~ ^/files/(.+)\\.(jpg|jpeg|png|gif)$"
    type: "static"
    root: "/var/www/images"
  
  # Case-insensitive regex match
  - path: "~* \\.(css|js)$"
    type: "static"
    root: "/var/www/assets"
    expires: "1y"
  
  # Priority prefix match
  - path: "^~ /static"
    type: "static"
    root: "/var/www"
```

## 🎯 Usage Examples

### Docker Deployment

#### Using Makefile (Recommended)

```bash
# Build Docker image
make docker-build

# Start container in background
make docker-start

# View logs
make docker-logs

# Stop container
make docker-stop

# Restart container
make docker-restart
```

#### Manual Docker Commands

```bash
# Build Docker image
docker build -t ngx-manager .

# Run container
docker run -d --name ngx-manager \
  -p 80:80 -p 443:443 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/certs:/app/certs \
  -v $(pwd)/nginx-conf:/etc/nginx/conf.d \
  ngx-manager

# View logs
docker logs ngx-manager

# Follow logs
docker logs -f ngx-manager

# Stop container
docker stop ngx-manager

# Remove container
docker rm ngx-manager
```

#### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  ngx-manager:
    build: .
    container_name: ngx-manager
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./certs:/app/certs
      - ./nginx-conf:/etc/nginx/conf.d
    restart: unless-stopped
```

Then run:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Container Management

```bash
# Enter container
docker exec -it ngx-manager bash

# Manual configuration generation
docker exec ngx-manager ngx-manager list

# Manual certificate renewal
docker exec ngx-manager ngx-manager renew

# Reload nginx configuration
docker exec ngx-manager ngx-manager reload
```

### Native Installation

For native installation (without Docker), see the [Installation Guide](#-installation).

## 🧪 Testing

The project includes a comprehensive test suite with unit tests, integration tests, and end-to-end tests.

### Quick Setup

```bash
# Setup development environment
make setup-dev

# Activate virtual environment
source .venv/bin/activate

# Run tests
make test
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-e2e          # End-to-end tests (requires Docker)

# Run tests with coverage
make test-coverage

# Manual pytest usage
pytest tests/                    # All tests
pytest tests/unit/              # Unit tests only
pytest tests/ -m "not slow"    # Skip slow tests
pytest tests/ -v               # Verbose output
```

### Using Standard Virtual Environment

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

### Test Structure
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions  
- **E2E Tests**: Test complete workflows with Docker
- **Coverage Reports**: Generate detailed coverage reports

### Dependencies

The project uses unified requirements management:
- **requirements.txt**: Production dependencies
- **requirements-dev.txt**: Development dependencies (includes testing tools)

All test dependencies are included in `requirements-dev.txt` - no separate test requirements file is needed.

## 🔍 Troubleshooting

### Common Issues

1. **Certificate Application Failure**
   - Check if domain DNS resolution is correct
   - Ensure port 80 is accessible
   - View certificate application logs: `docker exec ngx-manager cat /app/logs/cert.log`

2. **Configuration Generation Failure**
   - Check configuration file syntax
   - Ensure template files exist
   - View configuration generation logs

3. **Nginx Startup Failure**
   - Check generated configuration file syntax
   - Confirm upstream service accessibility
   - View Nginx error logs

### Debug Mode

Enable debug mode for more detailed logs:

```bash
# Modify debug setting in ssl.yml
acme:
  debug: true

# Restart container
docker-compose restart
```

## 🏗️ Architecture

### Core Components
- **Nginx**: High-performance web server and reverse proxy
- **Python**: Unified scripting language for configuration generation and certificate management
- **acme.sh**: SSL certificate automatic application and management
- **Jinja2**: Powerful template engine
- **Docker**: Containerized deployment

### Design Advantages
1. **Unified Language**: All components use Python for consistency and maintainability
2. **Modular Design**: Independent functional modules, easy to extend and maintain
3. **Configuration-Driven**: Based on YAML configuration files for simplified management
4. **Automation**: Supports configuration monitoring and automatic certificate renewal
5. **Containerization**: Docker deployment ensures environment consistency

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow Python PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for any user-facing changes
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Nginx](https://nginx.org/) - High-performance web server
- [acme.sh](https://github.com/acmesh-official/acme.sh) - ACME protocol client
- [Let's Encrypt](https://letsencrypt.org/) - Free SSL certificate service
- [Python](https://www.python.org/) - Programming language
- [Docker](https://www.docker.com/) - Containerization platform

## 📞 Support

If you encounter issues or have suggestions:

1. Check the [Issues](https://github.com/fengluo/ngx-manager/issues) page
2. Create a new Issue describing the problem
3. Contact maintainer: your-email@example.com

## 📈 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and improvements.

---

**Note**: Please thoroughly test configurations before using in production environments and regularly backup important data. 