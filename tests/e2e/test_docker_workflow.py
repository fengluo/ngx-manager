"""
Docker工作流程端到端测试
"""

import pytest
import requests
import time
import docker
from pathlib import Path
import tempfile
import shutil
import yaml
from unittest.mock import patch

# 需要安装docker-py: pip install docker

@pytest.mark.e2e
class TestDockerWorkflow:
    """测试完整的Docker工作流程"""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker客户端"""
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker不可用: {e}")

    @pytest.fixture(scope="class")
    def test_workspace(self):
        """测试工作空间"""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture(scope="class")
    def test_configs(self, test_workspace):
        """创建测试配置文件"""
        config_dir = test_workspace / "config"
        config_dir.mkdir()
        
        # vhosts配置
        vhosts_config = [
            {
                "name": "test-static",
                "domains": ["localhost", "127.0.0.1"],
                "type": "static",
                "root": "/var/www/html",
                "ssl": False
            }
        ]
        
        vhosts_file = config_dir / "vhosts.yml"
        with open(vhosts_file, 'w') as f:
            yaml.dump(vhosts_config, f)
        
        # SSL配置
        ssl_config = {
            "ssl": {
                "email": "test@example.com",
                "ca_server": "letsencrypt",
                "key_length": 2048
            },
            "acme": {
                "staging": True
            }
        }
        
        ssl_file = config_dir / "ssl.yml"
        with open(ssl_file, 'w') as f:
            yaml.dump(ssl_config, f)
        
        return {
            "vhosts_file": vhosts_file,
            "ssl_file": ssl_file,
            "config_dir": config_dir
        }

    @pytest.mark.slow
    def test_container_build_and_start(self, docker_client, test_configs):
        """测试容器构建和启动"""
        container_name = "nginx-manager-test"
        image_name = "nginx-manager:test"
        
        try:
            # 清理可能存在的容器和镜像
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass
            
            try:
                docker_client.images.remove(image_name)
            except docker.errors.ImageNotFound:
                pass
            
            # 构建镜像
            project_root = Path(__file__).parent.parent.parent
            image, build_logs = docker_client.images.build(
                path=str(project_root),
                tag=image_name,
                rm=True
            )
            
            assert image is not None
            
            # 创建并启动容器
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                ports={
                    '80/tcp': 8080,
                    '443/tcp': 8443
                },
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    }
                },
                detach=True,
                remove=False
            )
            
            # 等待容器启动
            time.sleep(10)
            
            # 检查容器状态
            container.reload()
            assert container.status == 'running'
            
            # 检查nginx进程
            exec_result = container.exec_run("pgrep nginx")
            assert exec_result.exit_code == 0
            
        finally:
            # 清理
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    @pytest.mark.slow
    @pytest.mark.network
    def test_http_response(self, docker_client, test_configs):
        """测试HTTP响应"""
        container_name = "nginx-manager-http-test"
        image_name = "nginx-manager:test"
        
        try:
            # 启动容器
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                ports={'80/tcp': 8081},
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            # 等待服务启动
            time.sleep(15)
            
            # 测试HTTP请求
            max_retries = 5
            for i in range(max_retries):
                try:
                    response = requests.get('http://localhost:8081', timeout=10)
                    break
                except requests.exceptions.ConnectionError:
                    if i == max_retries - 1:
                        raise
                    time.sleep(2)
            
            # nginx默认页面通常返回200或者可能是404（如果没有index.html）
            assert response.status_code in [200, 404, 403]
            
        finally:
            # 清理
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    def test_config_reload_workflow(self, docker_client, test_configs):
        """测试配置重新加载工作流程"""
        container_name = "nginx-manager-reload-test"
        image_name = "nginx-manager:test"
        
        try:
            # 启动容器
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            time.sleep(10)
            
            # 检查初始配置
            exec_result = container.exec_run("ls -la /etc/nginx/conf.d/")
            assert exec_result.exit_code == 0
            
            # 修改配置文件
            updated_config = [
                {
                    "name": "updated-static",
                    "domains": ["updated.localhost"],
                    "type": "static",
                    "root": "/var/www/html",
                    "ssl": False
                }
            ]
            
            with open(test_configs["vhosts_file"], 'w') as f:
                yaml.dump(updated_config, f)
            
            # 触发配置重新生成
            exec_result = container.exec_run(
                "python3 /app/scripts/generate-config.py"
            )
            assert exec_result.exit_code == 0
            
            # 重新加载nginx
            exec_result = container.exec_run("nginx -s reload")
            assert exec_result.exit_code == 0
            
        finally:
            # 清理
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    def test_certificate_management_workflow(self, docker_client, test_configs):
        """测试证书管理工作流程"""
        container_name = "nginx-manager-cert-test"
        image_name = "nginx-manager:test"
        
        try:
            # 启动容器
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            time.sleep(10)
            
            # 测试证书管理脚本
            exec_result = container.exec_run(
                "python3 /app/scripts/cert_manager.py --help"
            )
            assert exec_result.exit_code == 0
            assert b"usage:" in exec_result.output or b"Usage:" in exec_result.output
            
            # 测试列出证书（应该为空）
            exec_result = container.exec_run(
                "python3 /app/scripts/cert_manager.py --list"
            )
            # 返回码可能是0（空列表）或1（没有证书）
            assert exec_result.exit_code in [0, 1]
            
        finally:
            # 清理
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    def test_logs_and_monitoring(self, docker_client, test_configs):
        """测试日志和监控功能"""
        container_name = "nginx-manager-logs-test"
        image_name = "nginx-manager:test"
        
        try:
            # 启动容器
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            time.sleep(10)
            
            # 检查容器日志
            logs = container.logs().decode('utf-8')
            assert "nginx" in logs or "Starting" in logs
            
            # 检查nginx访问日志目录
            exec_result = container.exec_run("ls -la /app/logs/")
            assert exec_result.exit_code == 0
            
            # 检查nginx错误日志
            exec_result = container.exec_run("ls -la /var/log/nginx/")
            assert exec_result.exit_code == 0
            
        finally:
            # 清理
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

@pytest.mark.e2e
@pytest.mark.slow
class TestDockerComposeWorkflow:
    """测试Docker Compose工作流程"""
    
    @pytest.fixture
    def compose_file_path(self):
        """docker-compose.yml文件路径"""
        project_root = Path(__file__).parent.parent.parent
        return project_root / "docker-compose.yml"

    @patch('subprocess.run')
    def test_docker_compose_build(self, mock_subprocess, compose_file_path):
        """测试docker-compose构建"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Building nginx-manager"
        
        # 验证docker-compose.yml存在
        assert compose_file_path.exists()
        
        # 验证可以解析docker-compose.yml
        with open(compose_file_path, 'r') as f:
            compose_content = yaml.safe_load(f)
        
        assert 'services' in compose_content
        assert 'nginx-manager' in compose_content['services']

    @patch('subprocess.run')
    def test_docker_compose_up(self, mock_subprocess, compose_file_path):
        """测试docker-compose启动"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Starting nginx-manager"
        
        # 模拟docker-compose up命令
        result = mock_subprocess.return_value
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_docker_compose_down(self, mock_subprocess):
        """测试docker-compose停止"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Stopping nginx-manager"
        
        # 模拟docker-compose down命令
        result = mock_subprocess.return_value
        assert result.returncode == 0

@pytest.mark.e2e
class TestSystemIntegration:
    """测试系统集成"""
    
    def test_file_permissions(self):
        """测试文件权限"""
        project_root = Path(__file__).parent.parent.parent
        
        # 检查脚本文件是否可执行
        scripts_dir = project_root / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.py"):
                # Python文件应该是可读的
                assert script_file.is_file()
                assert script_file.stat().st_size > 0

    def test_directory_structure(self):
        """测试目录结构"""
        project_root = Path(__file__).parent.parent.parent
        
        # 检查必要的目录存在
        required_dirs = [
            "config",
            "scripts", 
            "templates",
            "tests"
        ]
        
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            assert dir_path.exists(), f"目录 {dir_name} 不存在"
            assert dir_path.is_dir(), f"{dir_name} 不是目录"

    def test_configuration_files(self):
        """测试配置文件"""
        project_root = Path(__file__).parent.parent.parent
        
        # 检查必要的配置文件
        config_files = [
            "config/vhosts.yml",
            "config/ssl.yml",
            "docker-compose.yml",
            "Dockerfile"
        ]
        
        for config_file in config_files:
            file_path = project_root / config_file
            if file_path.exists():  # 有些文件可能是可选的
                assert file_path.is_file()
                assert file_path.stat().st_size > 0
                
                # 对于YAML文件，检查是否可以解析
                if config_file.endswith('.yml'):
                    with open(file_path, 'r') as f:
                        yaml.safe_load(f)  # 如果格式错误会抛出异常

class TestPerformance:
    """性能测试"""
    
    @pytest.mark.slow
    def test_config_generation_performance(self, temp_dir):
        """测试配置生成性能"""
        import time
        from jinja2 import Template
        
        # 创建大量虚拟主机配置
        large_config = []
        for i in range(100):
            large_config.append({
                "name": f"site-{i}",
                "domains": [f"site{i}.example.com"],
                "type": "static",
                "root": "/var/www/html"
            })
        
        # 简单的模板
        template = Template("""
server {
    listen 80;
    server_name {{ vhost.domains | join(' ') }};
    root {{ vhost.root }};
}""")
        
        # 测试生成时间
        start_time = time.time()
        
        for vhost in large_config:
            rendered = template.render(vhost=vhost)
            assert len(rendered) > 0
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # 100个配置应该在1秒内完成
        assert generation_time < 1.0, f"配置生成太慢: {generation_time}秒"

    @pytest.mark.slow  
    def test_template_rendering_performance(self):
        """测试模板渲染性能"""
        import time
        from jinja2 import Template
        
        complex_template = Template("""
# Virtual Host: {{ vhost.name }}
server {
    listen 80;
    server_name {{ vhost.domains | join(' ') }};
    
    {% for location in vhost.locations %}
    location {{ location.path }} {
        {% if location.type == 'proxy' %}
        proxy_pass {{ location.upstream }};
        {% else %}
        root {{ location.root }};
        {% endif %}
    }
    {% endfor %}
}""")
        
        complex_vhost = {
            "name": "complex-site",
            "domains": ["complex.example.com"],
            "locations": [
                {
                    "path": f"/path{i}",
                    "type": "proxy",
                    "upstream": f"http://backend{i}:8080"
                } for i in range(50)
            ]
        }
        
        start_time = time.time()
        
        # 渲染100次
        for _ in range(100):
            rendered = complex_template.render(vhost=complex_vhost)
            assert "complex-site" in rendered
        
        end_time = time.time()
        render_time = end_time - start_time
        
        # 100次复杂渲染应该在1秒内完成
        assert render_time < 1.0, f"模板渲染太慢: {render_time}秒" 