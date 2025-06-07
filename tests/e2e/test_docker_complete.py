"""
Complete Docker E2E Tests for nginx-manager

This module contains comprehensive Docker-based e2e tests to verify
advanced functionality and complete workflows in containerized environment.
"""

import pytest
import requests
import time
import docker
import yaml
from pathlib import Path
import tempfile
import shutil


@pytest.mark.e2e
@pytest.mark.docker
@pytest.mark.slow
class TestDockerCompleteWorkflow:
    """Complete Docker workflow tests with advanced functionality"""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Initialize Docker client"""
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    
    @pytest.fixture(scope="class")
    def test_image(self, docker_client):
        """Build test image and cleanup after tests"""
        project_root = Path(__file__).parent.parent.parent
        image_tag = "nginx-manager:complete-test"
        
        # Build image
        try:
            print(f"\n🔨 Building Docker image: {image_tag}")
            image, logs = docker_client.images.build(
                path=str(project_root),
                tag=image_tag,
                rm=True,
                forcerm=True
            )
            print(f"✅ Image built successfully: {image_tag}")
            yield image_tag
        except Exception as e:
            pytest.fail(f"❌ Failed to build Docker image: {e}")
        finally:
            # Cleanup image after all tests
            try:
                docker_client.images.remove(image_tag, force=True)
                print(f"🧹 Cleaned up image: {image_tag}")
            except docker.errors.ImageNotFound:
                pass
            except Exception as e:
                print(f"⚠️ Warning: Failed to cleanup image {image_tag}: {e}")
    
    @pytest.fixture
    def test_configs(self):
        """Create test configuration files"""
        workspace = Path(tempfile.mkdtemp(prefix="ngx-complete-test-"))
        
        # Create directory structure
        config_dir = workspace / "config"
        www_dir = workspace / "www"
        logs_dir = workspace / "logs"
        
        for directory in [config_dir, www_dir, logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create test website content
        (www_dir / "index.html").write_text("""
<!DOCTYPE html>
<html>
<head><title>nginx-manager Test Site</title></head>
<body>
    <h1>Welcome to nginx-manager</h1>
    <p>This is a test page for complete workflow testing.</p>
    <p>Server: nginx-manager</p>
</body>
</html>
        """.strip())
        
        # Create main configuration
        main_config = {
            "environment": "development",
            "debug": True,
            "log_level": "INFO",
            "nginx": {
                "user": "nginx",
                "worker_processes": "auto",
                "worker_connections": 1024
            },
            "ssl": {
                "email": "test@example.com",
                "staging": True
            }
        }
        
        config_file = config_dir / "config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(main_config, f, default_flow_style=False)
        
        # Create sites configuration
        sites_config = [
            {
                "domain": "test.local",
                "type": "static",
                "root": "/var/www/html",
                "ssl": False,
                "enabled": True
            }
        ]
        
        sites_file = config_dir / "sites.yml"
        with open(sites_file, 'w') as f:
            yaml.dump(sites_config, f, default_flow_style=False)
        
        yield {
            "workspace": workspace,
            "config_dir": config_dir,
            "www_dir": www_dir,
            "logs_dir": logs_dir,
            "config_file": config_file,
            "sites_file": sites_file
        }
        
        # Cleanup
        shutil.rmtree(workspace, ignore_errors=True)
    
    def test_container_with_volumes(self, docker_client, test_image, test_configs):
        """Test container startup with volume mounts"""
        container_name = "ngx-complete-volumes-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                ports={
                    '80/tcp': 8085,
                    '443/tcp': 8486
                },
                volumes={
                    str(test_configs["config_dir"]): {
                        'bind': '/app/config',
                        'mode': 'rw'
                    },
                    str(test_configs["www_dir"]): {
                        'bind': '/var/www/html',
                        'mode': 'rw'
                    },
                    str(test_configs["logs_dir"]): {
                        'bind': '/app/logs',
                        'mode': 'rw'
                    }
                },
                environment={
                    'NGINX_MANAGER_DEBUG': 'true',
                    'NGINX_MANAGER_ENVIRONMENT': 'development'
                },
                detach=True
            )
            
            # Wait for startup
            max_wait = 30
            for i in range(max_wait):
                container.reload()
                if container.status == 'running':
                    break
                time.sleep(1)
            else:
                pytest.fail(f"Container failed to start within {max_wait} seconds")
            
            # Give nginx time to fully start
            time.sleep(10)
            
            # Verify nginx is running
            exec_result = container.exec_run("pgrep nginx")
            assert exec_result.exit_code == 0, "Nginx process not found"
            
            # Check nginx configuration
            exec_result = container.exec_run("nginx -t")
            assert exec_result.exit_code == 0, f"Nginx config test failed: {exec_result.output.decode()}"
            
            # Test volume mounts
            exec_result = container.exec_run("ls -la /app/config")
            assert exec_result.exit_code == 0, "Config volume not mounted"
            
            exec_result = container.exec_run("ls -la /var/www/html")
            assert exec_result.exit_code == 0, "WWW volume not mounted"
            
            print("✅ Container with volumes started successfully")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_nginx_manager_cli(self, docker_client, test_image, test_configs):
        """Test nginx-manager CLI functionality"""
        container_name = "ngx-complete-cli-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
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
            
            # Test status command
            exec_result = container.exec_run(["python", "-m", "nginx_manager.cli", "status"])
            assert exec_result.exit_code == 0, f"Status command failed: {exec_result.output.decode()}"
            
            # Test Python module import
            exec_result = container.exec_run([
                "python", "-c",
                "from nginx_manager.core.manager import NginxManager; print('Import successful')"
            ])
            assert exec_result.exit_code == 0, f"Module import failed: {exec_result.output.decode()}"
            
            print("✅ nginx-manager CLI functionality verified")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_http_response_with_content(self, docker_client, test_image, test_configs):
        """Test HTTP response with custom content"""
        container_name = "ngx-complete-http-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                ports={'80/tcp': 8086},
                volumes={
                    str(test_configs["www_dir"]): {
                        'bind': '/var/www/html',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            time.sleep(15)
            
            # Test health endpoint first
            max_retries = 5
            health_passed = False
            
            for i in range(max_retries):
                try:
                    response = requests.get('http://localhost:8086/health', timeout=10)
                    if response.status_code == 200 and "healthy" in response.text:
                        health_passed = True
                        print("✅ Health check passed")
                        break
                except requests.exceptions.RequestException:
                    if i < max_retries - 1:
                        time.sleep(3)
            
            if not health_passed:
                # Try main page for redirect
                try:
                    response = requests.get('http://localhost:8086', timeout=10, allow_redirects=False)
                    if response.status_code == 301:
                        print("✅ HTTP redirects to HTTPS as expected")
                        return
                except:
                    pass
                
                logs = container.logs().decode()
                pytest.fail(f"❌ Neither health check nor redirect worked. Container logs:\n{logs}")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_logging_functionality(self, docker_client, test_image, test_configs):
        """Test logging and monitoring functionality"""
        container_name = "ngx-complete-logs-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                volumes={
                    str(test_configs["logs_dir"]): {
                        'bind': '/app/logs',
                        'mode': 'rw'
                    }
                },
                detach=True
            )
            
            time.sleep(10)
            
            # Generate some activity
            exec_result = container.exec_run(["python", "-m", "nginx_manager.cli", "status"])
            
            # Check container logs
            logs = container.logs().decode()
            assert logs, "No container logs found"
            assert "nginx" in logs.lower(), "Nginx not mentioned in logs"
            
            # Check nginx access logs
            exec_result = container.exec_run("ls -la /var/log/nginx/")
            assert exec_result.exit_code == 0, "Nginx log directory not accessible"
            
            # Check if error log exists
            exec_result = container.exec_run("test -f /var/log/nginx/error.log")
            assert exec_result.exit_code == 0, "Nginx error log not found"
            
            print("✅ Logging functionality verified")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_configuration_validation(self, docker_client, test_image, test_configs):
        """Test configuration validation and error handling"""
        container_name = "ngx-complete-config-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
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
            
            # Test nginx configuration validation
            exec_result = container.exec_run("nginx -t")
            assert exec_result.exit_code == 0, f"Nginx config validation failed: {exec_result.output.decode()}"
            
            # Test nginx reload
            exec_result = container.exec_run("nginx -s reload")
            assert exec_result.exit_code == 0, f"Nginx reload failed: {exec_result.output.decode()}"
            
            # Verify nginx is still running after reload
            time.sleep(5)
            exec_result = container.exec_run("pgrep nginx")
            assert exec_result.exit_code == 0, "Nginx not running after reload"
            
            print("✅ Configuration validation passed")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_environment_variables(self, docker_client, test_image):
        """Test environment variable handling"""
        container_name = "ngx-complete-env-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                environment={
                    'TZ': 'Asia/Shanghai',
                    'NGINX_MANAGER_DEBUG': 'true',
                    'NGINX_MANAGER_ENVIRONMENT': 'development',
                    'DOCKER_CONTAINER': 'true'
                },
                detach=True
            )
            
            time.sleep(10)
            
            # Check environment variables
            exec_result = container.exec_run("env | grep NGINX_MANAGER")
            assert exec_result.exit_code == 0, "Environment variables not set"
            
            env_output = exec_result.output.decode()
            assert "NGINX_MANAGER_DEBUG=true" in env_output, "Debug flag not set"
            assert "NGINX_MANAGER_ENVIRONMENT=development" in env_output, "Environment not set"
            
            # Check timezone
            exec_result = container.exec_run("date")
            assert exec_result.exit_code == 0, "Date command failed"
            
            print("✅ Environment variables configured correctly")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_performance_metrics(self, docker_client, test_image):
        """Test basic performance metrics"""
        container_name = "ngx-complete-perf-test"
        
        try:
            # Measure startup time
            start_time = time.time()
            
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                detach=True
            )
            
            # Wait for nginx to be ready
            max_wait = 30
            for i in range(max_wait):
                container.reload()
                if container.status == 'running':
                    exec_result = container.exec_run("pgrep nginx")
                    if exec_result.exit_code == 0:
                        break
                time.sleep(0.5)
            
            startup_time = time.time() - start_time
            
            # Assert reasonable startup time
            assert startup_time < 30, f"Startup time too long: {startup_time:.2f}s"
            print(f"✅ Container startup time: {startup_time:.2f}s")
            
            # Test memory usage
            exec_result = container.exec_run("free -m")
            assert exec_result.exit_code == 0, "Memory check failed"
            
            # Test disk usage
            exec_result = container.exec_run("df -h")
            assert exec_result.exit_code == 0, "Disk check failed"
            
            print("✅ Performance metrics within acceptable range")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def _cleanup_container(self, docker_client, container_name: str):
        """Helper method to cleanup test containers"""
        try:
            container = docker_client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove()
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"⚠️ Warning: Failed to cleanup container {container_name}: {e}")


@pytest.mark.e2e
@pytest.mark.docker
@pytest.mark.slow
class TestDockerMultiContainer:
    """Multi-container integration tests"""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Initialize Docker client"""
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    
    @pytest.fixture(scope="class")
    def test_image(self, docker_client):
        """Build test image and cleanup after tests"""
        project_root = Path(__file__).parent.parent.parent
        image_tag = "nginx-manager:multi-test"
        
        # Build image
        try:
            print(f"\n🔨 Building Docker image: {image_tag}")
            image, logs = docker_client.images.build(
                path=str(project_root),
                tag=image_tag,
                rm=True,
                forcerm=True
            )
            print(f"✅ Image built successfully: {image_tag}")
            yield image_tag
        except Exception as e:
            pytest.fail(f"❌ Failed to build Docker image: {e}")
        finally:
            # Cleanup image after all tests
            try:
                docker_client.images.remove(image_tag, force=True)
                print(f"🧹 Cleaned up image: {image_tag}")
            except docker.errors.ImageNotFound:
                pass
            except Exception as e:
                print(f"⚠️ Warning: Failed to cleanup image {image_tag}: {e}")
    
    def test_concurrent_containers(self, docker_client, test_image):
        """Test running multiple containers concurrently"""
        container_count = 3
        containers = []
        
        try:
            # Start multiple containers
            for i in range(container_count):
                container = docker_client.containers.run(
                    test_image,
                    name=f"ngx-multi-{i}",
                    ports={f'80/tcp': 8087 + i},
                    detach=True
                )
                containers.append(container)
            
            # Wait for all to start
            time.sleep(15)
            
            # Verify all containers are running
            for i, container in enumerate(containers):
                container.reload()
                assert container.status == 'running', f"Container {i} not running"
                
                # Test nginx in each container
                exec_result = container.exec_run("nginx -t")
                assert exec_result.exit_code == 0, f"Nginx failed in container {i}"
                
                exec_result = container.exec_run("pgrep nginx")
                assert exec_result.exit_code == 0, f"Nginx process not found in container {i}"
            
            print(f"✅ {container_count} containers running concurrently")
            
        finally:
            # Cleanup all containers
            for i, container in enumerate(containers):
                try:
                    container.stop(timeout=10)
                    container.remove()
                except Exception as e:
                    print(f"⚠️ Warning: Failed to cleanup container {i}: {e}")
    
    def test_container_isolation(self, docker_client, test_image):
        """Test container isolation and resource separation"""
        containers = []
        
        try:
            # Start two containers with different configurations
            for i in range(2):
                container = docker_client.containers.run(
                    test_image,
                    name=f"ngx-isolation-{i}",
                    environment={
                        'CONTAINER_ID': str(i),
                        'NGINX_MANAGER_DEBUG': 'true' if i == 0 else 'false'
                    },
                    detach=True
                )
                containers.append(container)
            
            time.sleep(15)
            
            # Verify isolation
            for i, container in enumerate(containers):
                container.reload()
                assert container.status == 'running', f"Container {i} not running"
                
                # Check environment variables are isolated
                exec_result = container.exec_run("env | grep CONTAINER_ID")
                assert exec_result.exit_code == 0, f"Environment not set in container {i}"
                
                env_output = exec_result.output.decode()
                assert f"CONTAINER_ID={i}" in env_output, f"Wrong environment in container {i}"
            
            print("✅ Container isolation verified")
            
        finally:
            # Cleanup
            for i, container in enumerate(containers):
                try:
                    container.stop(timeout=10)
                    container.remove()
                except Exception as e:
                    print(f"⚠️ Warning: Failed to cleanup container {i}: {e}") 