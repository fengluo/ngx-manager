"""
测试配置生成完整流程的集成测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
import os
from unittest.mock import patch

class TestConfigGenerationWorkflow:
    """测试配置生成工作流程"""
    
    @pytest.fixture
    def test_workspace(self):
        """创建测试工作空间"""
        workspace = Path(tempfile.mkdtemp())
        
        # 创建目录结构
        (workspace / "config").mkdir()
        (workspace / "templates").mkdir()
        (workspace / "output").mkdir()
        (workspace / "logs").mkdir()
        
        yield workspace
        
        # 清理
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def vhosts_config_file(self, test_workspace):
        """创建虚拟主机配置文件"""
        vhosts_config = [
            {
                "name": "static-site",
                "domains": ["www.example.com", "example.com"],
                "type": "static",
                "root": "/var/www/html",
                "ssl": True
            },
            {
                "name": "api-service",
                "domains": ["api.example.com"],
                "type": "proxy",
                "upstream": "http://backend:8080",
                "ssl": True,
                "locations": [
                    {
                        "path": "/health",
                        "type": "static",
                        "root": "/var/www/health"
                    },
                    {
                        "path": "/api/v1",
                        "type": "proxy",
                        "upstream": "http://backend-v1:8080"
                    }
                ]
            }
        ]
        
        config_file = test_workspace / "config" / "vhosts.yml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(vhosts_config, f, default_flow_style=False, allow_unicode=True)
        
        return config_file

    @pytest.fixture
    def ssl_config_file(self, test_workspace):
        """创建SSL配置文件"""
        ssl_config = {
            "ssl": {
                "email": "admin@example.com",
                "ca_server": "letsencrypt",
                "key_length": 2048
            },
            "acme": {
                "staging": True,
                "force": False
            }
        }
        
        config_file = test_workspace / "config" / "ssl.yml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(ssl_config, f, default_flow_style=False, allow_unicode=True)
        
        return config_file

    @pytest.fixture
    def nginx_template_file(self, test_workspace):
        """创建nginx配置模板文件"""
        template_content = """# Virtual Host: {{ vhost.name }}
# Generated at: {{ generation_time }}
# Domains: {{ vhost.domains | join(', ') }}

{% if vhost.ssl %}
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name {{ vhost.domains | join(' ') }};
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl;
    server_name {{ vhost.domains | join(' ') }};
    
    ssl_certificate /app/certs/{{ vhost.domains[0] }}/fullchain.cer;
    ssl_certificate_key /app/certs/{{ vhost.domains[0] }}/{{ vhost.domains[0] }}.key;
{% else %}
# HTTP server
server {
    listen 80;
    server_name {{ vhost.domains | join(' ') }};
{% endif %}
    
    access_log /app/logs/{{ vhost.name }}-access.log;
    error_log /app/logs/{{ vhost.name }}-error.log;
    
{% if vhost.locations %}
    # Location-based configuration
{% for location in vhost.locations %}
    location {{ location.path }} {
{% if location.type == 'proxy' %}
        proxy_pass {{ location.upstream }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
{% elif location.type == 'static' %}
        root {{ location.root }};
        try_files $uri $uri/ =404;
{% endif %}
    }
{% endfor %}
{% else %}
    # Simple configuration
{% if vhost.type == 'proxy' %}
    location / {
        proxy_pass {{ vhost.upstream }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
{% elif vhost.type == 'static' %}
    location / {
        root {{ vhost.root }};
        index index.html index.htm;
        try_files $uri $uri/ =404;
    }
{% endif %}
{% endif %}
}"""
        
        template_file = test_workspace / "templates" / "vhost.conf.j2"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        return template_file

    def test_complete_config_generation_workflow(self, test_workspace, vhosts_config_file, 
                                                ssl_config_file, nginx_template_file):
        """测试完整的配置生成工作流程"""
        # 模拟配置生成过程
        from jinja2 import Template
        
        # 加载配置
        with open(vhosts_config_file, 'r', encoding='utf-8') as f:
            vhosts_data = yaml.safe_load(f)
        
        with open(ssl_config_file, 'r', encoding='utf-8') as f:
            ssl_data = yaml.safe_load(f)
        
        with open(nginx_template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 验证配置加载成功
        assert isinstance(vhosts_data, list)
        assert len(vhosts_data) == 2
        assert isinstance(ssl_data, dict)
        assert "ssl" in ssl_data
        
        # 生成nginx配置
        template = Template(template_content)
        output_dir = test_workspace / "output"
        
        for vhost in vhosts_data:
            # 渲染配置
            rendered_config = template.render(
                vhost=vhost,
                generation_time="2024-12-19 10:00:00"
            )
            
            # 保存配置文件
            config_file = output_dir / f"{vhost['name']}.conf"
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(rendered_config)
            
            # 验证配置文件生成
            assert config_file.exists()
            assert config_file.stat().st_size > 0
            
            # 验证配置内容
            config_content = config_file.read_text(encoding='utf-8')
            assert vhost['name'] in config_content
            for domain in vhost['domains']:
                assert domain in config_content
            
            if vhost.get('ssl'):
                assert 'ssl_certificate' in config_content
                assert '443 ssl' in config_content
            
            if vhost.get('type') == 'proxy':
                assert 'proxy_pass' in config_content
                assert vhost['upstream'] in config_content
            elif vhost.get('type') == 'static':
                assert 'root' in config_content
                assert vhost['root'] in config_content

    def test_config_validation_workflow(self, vhosts_config_file, ssl_config_file):
        """测试配置验证工作流程"""
        # 加载并验证vhosts配置
        with open(vhosts_config_file, 'r', encoding='utf-8') as f:
            vhosts_data = yaml.safe_load(f)
        
        for vhost in vhosts_data:
            # 验证必要字段
            assert 'name' in vhost
            assert 'domains' in vhost
            assert isinstance(vhost['domains'], list)
            assert len(vhost['domains']) > 0
            
            # 验证类型特定字段
            if vhost.get('type') == 'static':
                assert 'root' in vhost
            elif vhost.get('type') == 'proxy':
                assert 'upstream' in vhost
            
            # 验证locations配置
            if 'locations' in vhost:
                for location in vhost['locations']:
                    assert 'path' in location
                    assert 'type' in location
                    
                    if location['type'] == 'proxy':
                        assert 'upstream' in location
                    elif location['type'] == 'static':
                        assert 'root' in location
        
        # 验证SSL配置
        with open(ssl_config_file, 'r', encoding='utf-8') as f:
            ssl_data = yaml.safe_load(f)
        
        assert 'ssl' in ssl_data
        assert 'email' in ssl_data['ssl']
        assert 'ca_server' in ssl_data['ssl']

    def test_error_handling_in_workflow(self, test_workspace):
        """测试工作流程中的错误处理"""
        # 测试缺少配置文件的情况
        nonexistent_config = test_workspace / "config" / "nonexistent.yml"
        
        try:
            with open(nonexistent_config, 'r') as f:
                yaml.safe_load(f)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass  # 预期的异常
        
        # 测试无效YAML格式
        invalid_yaml_file = test_workspace / "config" / "invalid.yml"
        with open(invalid_yaml_file, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        try:
            with open(invalid_yaml_file, 'r') as f:
                yaml.safe_load(f)
            assert False, "Should have raised YAML parsing error"
        except yaml.YAMLError:
            pass  # 预期的异常

    def test_simplified_config_format(self, test_workspace):
        """测试简化配置格式的处理"""
        # 创建简化格式的配置（直接数组，不包含vhosts键）
        simplified_config = [
            {
                "name": "simple-site",
                "domains": ["simple.example.com"],
                "type": "static",
                "root": "/var/www/simple"
            }
        ]
        
        config_file = test_workspace / "config" / "simplified.yml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(simplified_config, f, default_flow_style=False)
        
        # 加载并验证简化格式配置
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['name'] == 'simple-site'

    def test_full_format_config(self, test_workspace):
        """测试完整格式配置的处理"""
        # 创建完整格式的配置（包含vhosts键）
        full_config = {
            "vhosts": [
                {
                    "name": "full-site",
                    "domains": ["full.example.com"],
                    "type": "static",
                    "root": "/var/www/full"
                }
            ]
        }
        
        config_file = test_workspace / "config" / "full.yml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(full_config, f, default_flow_style=False)
        
        # 加载并验证完整格式配置
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        assert isinstance(data, dict)
        assert 'vhosts' in data
        assert isinstance(data['vhosts'], list)
        assert len(data['vhosts']) == 1
        assert data['vhosts'][0]['name'] == 'full-site'

class TestConfigReloading:
    """测试配置重新加载功能"""
    
    @pytest.fixture
    def config_workspace(self):
        """配置工作空间"""
        workspace = Path(tempfile.mkdtemp())
        (workspace / "config").mkdir()
        (workspace / "output").mkdir()
        
        yield workspace
        
        shutil.rmtree(workspace, ignore_errors=True)

    def test_config_file_change_detection(self, config_workspace):
        """测试配置文件变更检测"""
        config_file = config_workspace / "config" / "vhosts.yml"
        
        # 创建初始配置
        initial_config = [{"name": "initial", "domains": ["initial.com"], "type": "static", "root": "/var/www"}]
        with open(config_file, 'w') as f:
            yaml.dump(initial_config, f)
        
        initial_mtime = config_file.stat().st_mtime
        
        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.1)
        
        # 修改配置文件
        updated_config = [{"name": "updated", "domains": ["updated.com"], "type": "static", "root": "/var/www"}]
        with open(config_file, 'w') as f:
            yaml.dump(updated_config, f)
        
        updated_mtime = config_file.stat().st_mtime
        
        # 验证时间戳变更
        assert updated_mtime > initial_mtime
        
        # 验证配置内容变更
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        assert data[0]['name'] == 'updated'
        assert data[0]['domains'] == ['updated.com']

    @patch('time.sleep')  # 加速测试
    def test_config_monitoring_simulation(self, mock_sleep, config_workspace):
        """模拟配置文件监控"""
        config_file = config_workspace / "config" / "vhosts.yml"
        
        # 创建配置文件
        config_data = [{"name": "monitored", "domains": ["monitored.com"], "type": "static", "root": "/var/www"}]
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # 模拟监控逻辑
        last_mtime = config_file.stat().st_mtime
        
        # 模拟配置文件被修改
        updated_config = [{"name": "modified", "domains": ["modified.com"], "type": "static", "root": "/var/www"}]
        with open(config_file, 'w') as f:
            yaml.dump(updated_config, f)
        
        current_mtime = config_file.stat().st_mtime
        
        # 检测到变更
        if current_mtime > last_mtime:
            # 重新加载配置
            with open(config_file, 'r') as f:
                new_config = yaml.safe_load(f)
            
            assert new_config[0]['name'] == 'modified'
            last_mtime = current_mtime

class TestTemplateRendering:
    """测试模板渲染功能"""
    
    def test_jinja2_template_rendering(self):
        """测试Jinja2模板渲染"""
        from jinja2 import Template
        
        template_content = """
server {
    listen {{ port | default(80) }};
    server_name {{ domains | join(' ') }};
    
    {% if ssl %}
    ssl_certificate {{ ssl_cert_path }};
    ssl_certificate_key {{ ssl_key_path }};
    {% endif %}
    
    {% for location in locations %}
    location {{ location.path }} {
        {{ location.config | indent(8) }}
    }
    {% endfor %}
}
"""
        
        template = Template(template_content)
        
        # 测试数据
        test_data = {
            "port": 443,
            "domains": ["test.example.com", "www.test.example.com"],
            "ssl": True,
            "ssl_cert_path": "/app/certs/test.example.com/fullchain.cer",
            "ssl_key_path": "/app/certs/test.example.com/test.example.com.key",
            "locations": [
                {
                    "path": "/api",
                    "config": "proxy_pass http://backend:8080;\nproxy_set_header Host $host;"
                },
                {
                    "path": "/",
                    "config": "root /var/www/html;\ntry_files $uri $uri/ =404;"
                }
            ]
        }
        
        rendered = template.render(**test_data)
        
        # 验证渲染结果
        assert "listen 443;" in rendered
        assert "test.example.com www.test.example.com" in rendered
        assert "ssl_certificate" in rendered
        assert "location /api" in rendered
        assert "location /" in rendered
        assert "proxy_pass http://backend:8080;" in rendered

    def test_template_error_handling(self):
        """测试模板错误处理"""
        from jinja2 import Template, UndefinedError
        
        template_content = "server_name {{ undefined_variable }};"
        template = Template(template_content)
        
        # 测试未定义变量
        try:
            template.render()
            assert False, "Should raise UndefinedError"
        except UndefinedError:
            pass  # 预期的异常

    def test_template_with_filters(self):
        """测试模板过滤器"""
        from jinja2 import Template
        
        template_content = """
# Domains: {{ domains | join(', ') | upper }}
# Root: {{ root | default('/var/www/html') }}
# SSL: {{ ssl | default(false) | string | lower }}
"""
        
        template = Template(template_content)
        
        test_data = {
            "domains": ["example.com", "www.example.com"],
            "ssl": True
        }
        
        rendered = template.render(**test_data)
        
        assert "EXAMPLE.COM, WWW.EXAMPLE.COM" in rendered
        assert "Root: /var/www/html" in rendered
        assert "SSL: true" in rendered 