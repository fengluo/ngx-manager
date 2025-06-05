"""
Sample configuration data for testing
"""

# Simple static site configuration
SIMPLE_STATIC_CONFIG = {
    "name": "simple-static",
    "domains": ["simple.example.com"],
    "type": "static",
    "root": "/var/www/html",
    "ssl": False
}

# Simple proxy configuration
SIMPLE_PROXY_CONFIG = {
    "name": "simple-proxy", 
    "domains": ["api.example.com"],
    "type": "proxy",
    "upstream": "http://backend:8080",
    "ssl": True
}

# Complex configuration (includes multiple locations)
COMPLEX_CONFIG = {
    "name": "complex-app",
    "domains": ["app.example.com", "www.app.example.com"],
    "ssl": True,
    "auth_basic": True,
    "auth_basic_user_file": "/etc/nginx/.htpasswd",
    "locations": [
        {
            "path": "/api",
            "type": "proxy",
            "upstream": "http://api-service:8080",
            "proxy_connect_timeout": "10s",
            "proxy_read_timeout": "60s",
            "websocket": True
        },
        {
            "path": "/static",
            "type": "static",
            "root": "/var/www/static",
            "expires": "30d",
            "autoindex": True
        },
        {
            "path": "/uploads",
            "type": "static",
            "root": "/var/www/uploads",
            "client_max_body_size": "100M",
            "auth_basic": True
        },
        {
            "path": "/",
            "type": "static",
            "root": "/var/www/html",
            "try_files": "$uri $uri/ /index.html"
        }
    ],
    "custom_config": """
    # Custom configuration
            add_header X-Custom-Header "ngx-manager";
    error_page 404 /404.html;
    """
}

# Microservices configuration
MICROSERVICES_CONFIG = [
    {
        "name": "user-service",
        "domains": ["users.example.com"],
        "type": "proxy",
        "upstream": "http://user-service:3000",
        "ssl": True,
        "locations": [
            {
                "path": "/health",
                "type": "static",
                "root": "/var/www/health"
            }
        ]
    },
    {
        "name": "order-service",
        "domains": ["orders.example.com"],
        "type": "proxy", 
        "upstream": "http://order-service:3001",
        "ssl": True
    },
    {
        "name": "payment-service",
        "domains": ["payments.example.com"],
        "type": "proxy",
        "upstream": "http://payment-service:3002",
        "ssl": True,
        "auth_basic": True
    }
]

# SSL configuration example
SSL_CONFIG_LETSENCRYPT = {
    "ssl": {
        "email": "admin@example.com",
        "ca_server": "letsencrypt",
        "key_length": 2048,
        "auto_upgrade": True
    },
    "acme": {
        "staging": False,
        "force": False,
        "debug": False
    },
    "advanced": {
        "renewal_check_interval": 24,
        "renewal_days_before_expiry": 30,
        "concurrent_cert_limit": 5,
        "retry_attempts": 3,
        "retry_interval": 300
    }
}

SSL_CONFIG_ZEROSSL = {
    "ssl": {
        "email": "admin@example.com",
        "ca_server": "zerossl",
        "key_length": 4096,
        "auto_upgrade": False
    },
    "acme": {
        "staging": True,
        "force": True,
        "debug": True
    }
}

# Test environment configuration
TEST_VHOSTS_CONFIG = [
    {
        "name": "test-static",
        "domains": ["localhost", "127.0.0.1"],
        "type": "static",
        "root": "/var/www/html",
        "ssl": False
    },
    {
        "name": "test-proxy",
        "domains": ["api.localhost"],
        "type": "proxy",
        "upstream": "http://httpbin.org",
        "ssl": False
    }
]

TEST_SSL_CONFIG = {
    "ssl": {
        "email": "test@example.com",
        "ca_server": "letsencrypt",
        "key_length": 2048
    },
    "acme": {
        "staging": True,
        "force": False
    }
}

# Full format configuration (includes vhosts key)
FULL_FORMAT_CONFIG = {
    "vhosts": [
        SIMPLE_STATIC_CONFIG,
        SIMPLE_PROXY_CONFIG
    ]
}

# Simplified format configuration (direct array)
SIMPLIFIED_FORMAT_CONFIG = [
    SIMPLE_STATIC_CONFIG,
    SIMPLE_PROXY_CONFIG
]

# Invalid configuration examples (for testing error handling)
INVALID_CONFIGS = {
    "missing_name": {
        "domains": ["example.com"],
        "type": "static",
        "root": "/var/www/html"
    },
    "missing_domains": {
        "name": "invalid",
        "type": "static", 
        "root": "/var/www/html"
    },
    "empty_domains": {
        "name": "invalid",
        "domains": [],
        "type": "static",
        "root": "/var/www/html"
    },
    "invalid_type": {
        "name": "invalid",
        "domains": ["example.com"],
        "type": "invalid",
        "root": "/var/www/html"
    },
    "static_missing_root": {
        "name": "invalid",
        "domains": ["example.com"],
        "type": "static"
    },
    "proxy_missing_upstream": {
        "name": "invalid",
        "domains": ["example.com"],
        "type": "proxy"
    }
}

# Large configuration (for performance testing)
def generate_large_config(count=100):
    """Generate a large number of virtual host configurations for performance testing"""
    configs = []
    for i in range(count):
        config = {
            "name": f"site-{i:03d}",
            "domains": [f"site{i:03d}.example.com"],
            "type": "static" if i % 2 == 0 else "proxy",
            "ssl": i % 3 == 0
        }
        
        if config["type"] == "static":
            config["root"] = f"/var/www/site{i:03d}"
        else:
            config["upstream"] = f"http://backend{i:03d}:8080"
        
        # Add locations to some configurations
        if i % 5 == 0:
            config["locations"] = [
                {
                    "path": "/api",
                    "type": "proxy",
                    "upstream": f"http://api{i:03d}:8080"
                },
                {
                    "path": "/static",
                    "type": "static",
                    "root": f"/var/www/site{i:03d}/static"
                }
            ]
        
        configs.append(config)
    
    return configs

# Nginx template test data
NGINX_TEMPLATE_VARS = {
    "generation_time": "2024-12-19 10:00:00",
    "vhost": COMPLEX_CONFIG
}

# Docker test configuration
DOCKER_TEST_CONFIG = {
    "vhosts_config": TEST_VHOSTS_CONFIG,
    "ssl_config": TEST_SSL_CONFIG,
    "environment": {
        "TZ": "Asia/Shanghai",
        "NGINX_RELOAD_SIGNAL": "HUP",
        "ACME_HOME": "/root/.acme.sh",
        "DEBUG": "false"
    }
} 