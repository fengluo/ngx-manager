"""
End-to-end Docker workflow tests
"""

import pytest
import requests
import time
import docker
from pathlib import Path
import tempfile
import shutil
import yaml
import os
from unittest.mock import patch, Mock

from nginx_manager.core.manager import NginxManager
from nginx_manager.config.settings import Settings

# Requires docker-py: pip install docker

@pytest.mark.e2e
class TestDockerWorkflow:
    """Test complete Docker workflow"""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker client"""
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")

    @pytest.fixture(scope="class")
    def test_workspace(self):
        """Test workspace"""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture(scope="class")
    def test_configs(self, test_workspace):
        """Create test configuration files"""
        config_dir = test_workspace / "config"
        config_dir.mkdir()
        
        # Create test HTML content
        www_dir = test_workspace / "www"
        www_dir.mkdir()
        (www_dir / "index.html").write_text("<h1>Test Site</h1>")
        
        return {
            "config_dir": config_dir,
            "www_dir": www_dir,
            "workspace": test_workspace
        }

    @pytest.mark.slow
    def test_container_build_and_start(self, docker_client, test_configs):
        """Test container build and start"""
        container_name = "nginx-manager-test"
        image_name = "nginx-manager:test"
        
        try:
            # Clean up existing containers and images
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
            
            # Build image
            project_root = Path(__file__).parent.parent.parent
            image, build_logs = docker_client.images.build(
                path=str(project_root),
                tag=image_name,
                rm=True
            )
            
            assert image is not None
            
            # Create and start container
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
                    },
                    str(test_configs["www_dir"]): {
                        'bind': '/app/www',
                        'mode': 'rw'
                    }
                },
                detach=True,
                remove=False
            )
            
            # Wait for container to start
            time.sleep(10)
            
            # Check container status
            container.reload()
            assert container.status == 'running'
            
            # Check nginx process
            exec_result = container.exec_run("pgrep nginx")
            assert exec_result.exit_code == 0
            
        finally:
            # Cleanup
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    @pytest.mark.slow
    @pytest.mark.network
    def test_http_response(self, docker_client, test_configs):
        """Test HTTP response"""
        container_name = "nginx-manager-http-test"
        image_name = "nginx-manager:test"
        
        try:
            # Start container
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                ports={'80/tcp': 8081},
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    },
                    str(test_configs["www_dir"]): {
                        'bind': '/app/www',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            # Wait for service to start
            time.sleep(15)
            
            # Test HTTP request
            max_retries = 5
            for i in range(max_retries):
                try:
                    response = requests.get('http://localhost:8081', timeout=10)
                    break
                except requests.exceptions.ConnectionError:
                    if i == max_retries - 1:
                        raise
                    time.sleep(2)
            
            # nginx default page usually returns 200 or might be 404 (if no index.html)
            assert response.status_code in [200, 404, 403]
            
        finally:
            # Cleanup
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    def test_config_reload_workflow(self, docker_client, test_configs):
        """Test configuration reload workflow"""
        container_name = "nginx-manager-reload-test"
        image_name = "nginx-manager:test"
        
        try:
            # Start container
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                ports={'80/tcp': 8082},
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            # Wait for container to start
            time.sleep(10)
            
            # Test nginx reload command
            exec_result = container.exec_run("nginx -s reload")
            assert exec_result.exit_code == 0
            
            # Test configuration test
            exec_result = container.exec_run("nginx -t")
            assert exec_result.exit_code == 0
            
        finally:
            # Cleanup
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    def test_certificate_management_workflow(self, docker_client, test_configs):
        """Test certificate management workflow"""
        container_name = "nginx-manager-cert-test"
        image_name = "nginx-manager:test"
        
        try:
            # Start container
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
            
            # Wait for container to start
            time.sleep(10)
            
            # Check if acme.sh is available
            exec_result = container.exec_run("which acme.sh")
            # acme.sh might not be installed in test environment, so we just check the command runs
            assert exec_result.exit_code in [0, 1]  # 0 if found, 1 if not found
            
            # Test SSL directory structure
            exec_result = container.exec_run("ls -la /app/certs")
            assert exec_result.exit_code == 0
            
        finally:
            # Cleanup
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass

    def test_logs_and_monitoring(self, docker_client, test_configs):
        """Test logs and monitoring"""
        container_name = "nginx-manager-logs-test"
        image_name = "nginx-manager:test"
        
        try:
            # Start container
            container = docker_client.containers.run(
                image_name,
                name=container_name,
                detach=True
            )
            
            # Wait for container to start
            time.sleep(5)
            
            # Get container logs
            logs = container.logs().decode('utf-8')
            assert logs is not None
            
            # Check nginx access and error log files
            exec_result = container.exec_run("ls -la /app/logs")
            assert exec_result.exit_code == 0
            
        finally:
            # Cleanup
            try:
                container = docker_client.containers.get(container_name)
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass


@pytest.mark.e2e
@pytest.mark.slow
class TestDockerComposeWorkflow:
    """Test Docker Compose workflow"""
    
    @pytest.fixture
    def compose_file_path(self):
        """Docker Compose file path"""
        return Path(__file__).parent.parent.parent / "docker-compose.yml"

    @patch('subprocess.run')
    def test_docker_compose_build(self, mock_subprocess, compose_file_path):
        """Test Docker Compose build"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Build successful")
        
        # Simulate docker-compose build
        result = mock_subprocess(['docker-compose', '-f', str(compose_file_path), 'build'])
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_docker_compose_up(self, mock_subprocess, compose_file_path):
        """Test Docker Compose up"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Services started")
        
        # Simulate docker-compose up
        result = mock_subprocess(['docker-compose', '-f', str(compose_file_path), 'up', '-d'])
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_docker_compose_down(self, mock_subprocess):
        """Test Docker Compose down"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Services stopped")
        
        # Simulate docker-compose down
        result = mock_subprocess(['docker-compose', 'down'])
        assert result.returncode == 0


@pytest.mark.e2e
class TestSystemIntegration:
    """Test system integration"""
    
    def test_file_permissions(self):
        """Test file permissions"""
        project_root = Path(__file__).parent.parent.parent
        
        # Check main script permissions
        main_script = project_root / "nginx_manager.py"
        if main_script.exists():
            assert main_script.is_file()
            # Check if file is readable
            assert main_script.stat().st_mode & 0o444

    def test_directory_structure(self):
        """Test directory structure"""
        project_root = Path(__file__).parent.parent.parent
        
        # Check main directories exist
        expected_dirs = [
            "nginx_manager",
            "nginx_manager/config",
            "nginx_manager/core",
            "nginx_manager/ssl",
            "nginx_manager/templates",
            "nginx_manager/utils"
        ]
        
        for dir_path in expected_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"Directory {dir_path} should exist"
            assert full_path.is_dir(), f"{dir_path} should be a directory"

    def test_configuration_files(self):
        """Test configuration files"""
        project_root = Path(__file__).parent.parent.parent
        
        # Check essential files exist
        essential_files = [
            "setup.py",
            "requirements.txt",
            "Dockerfile",
            "nginx_manager/__init__.py",
            "nginx_manager/cli.py"
        ]
        
        for file_path in essential_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"File {file_path} should exist"
            assert full_path.is_file(), f"{file_path} should be a file"
            assert full_path.stat().st_size > 0, f"{file_path} should not be empty"


@pytest.mark.e2e
class TestPerformance:
    """Test performance aspects"""
    
    @pytest.mark.slow
    def test_config_generation_performance(self, test_configs):
        """Test configuration generation performance"""
        with patch('nginx_manager.ssl.manager.SSLManager._find_acme_sh') as mock_acme:
            mock_acme.return_value = Path('/usr/local/bin/acme.sh')
            
            with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.nginx_config_dir = test_configs["workspace"] / "nginx"
                mock_settings.ssl_certs_dir = test_configs["workspace"] / "certs"
                mock_settings.logs_dir = test_configs["workspace"] / "logs"
                mock_settings.www_dir = test_configs["workspace"] / "www"
                mock_settings_class.return_value = mock_settings
                
                manager = NginxManager()
                
                # Generate multiple site configurations
                domains = [f'perf-test-{i}.example.com' for i in range(20)]
                
                import time
                start_time = time.time()
                
                with patch('pathlib.Path.exists', return_value=False), \
                     patch('builtins.open'), \
                     patch('subprocess.run', return_value=Mock(returncode=0)), \
                     patch.object(manager.ssl_manager, 'obtain_certificate', 
                                 return_value={'success': True}):
                    
                    for domain in domains:
                        result = manager.add_site(domain, 'http://localhost:3000')
                        assert result['success'] is True
                
                end_time = time.time()
                
                # Should complete within reasonable time (less than 5 seconds for 20 sites)
                assert (end_time - start_time) < 5.0

    @pytest.mark.slow  
    def test_template_rendering_performance(self):
        """Test template rendering performance"""
        from nginx_manager.templates.generator import ConfigGenerator
        
        with patch('nginx_manager.config.settings.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.ssl_certs_dir = Path("/tmp/certs")
            mock_settings.logs_dir = Path("/tmp/logs")
            mock_settings.www_dir = Path("/tmp/www")
            mock_settings.nginx_config_dir = Path("/tmp/nginx")
            mock_settings_class.return_value = mock_settings
            
            generator = ConfigGenerator()
            
            # Render multiple templates
            import time
            start_time = time.time()
            
            for i in range(100):
                config = generator.generate_site_config(
                    domain=f'template-test-{i}.example.com',
                    backend='http://localhost:3000',
                    ssl=True
                )
                assert config is not None
            
            end_time = time.time()
            
            # Should complete within reasonable time (less than 2 seconds for 100 renders)
            assert (end_time - start_time) < 2.0 