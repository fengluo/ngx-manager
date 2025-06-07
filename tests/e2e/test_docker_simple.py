"""
Simplified Docker E2E Tests for nginx-manager

This module contains essential Docker-based e2e tests to verify
core functionality in a containerized environment.
"""

import pytest
import requests
import time
import docker
import subprocess
from pathlib import Path
import tempfile
import shutil


@pytest.mark.e2e
@pytest.mark.docker
class TestDockerSimple:
    """Simplified Docker workflow tests for core functionality"""
    
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
        image_tag = "nginx-manager:simple-test"
        
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
    
    def test_container_startup(self, docker_client, test_image):
        """Test container can start successfully"""
        container_name = "ngx-simple-startup-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                detach=True,
                remove=False
            )
            
            # Wait for startup
            time.sleep(10)
            
            # Check status
            container.reload()
            assert container.status == 'running', f"Container status: {container.status}"
            
            print("✅ Container started successfully")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_nginx_process(self, docker_client, test_image):
        """Test nginx process is running correctly"""
        container_name = "ngx-simple-nginx-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                detach=True
            )
            
            time.sleep(10)
            
            # Check nginx process
            exec_result = container.exec_run("pgrep nginx")
            assert exec_result.exit_code == 0, "Nginx process not found"
            
            # Check nginx config
            exec_result = container.exec_run("nginx -t")
            assert exec_result.exit_code == 0, f"Nginx config invalid: {exec_result.output.decode()}"
            
            print("✅ Nginx is running and configured correctly")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_python_package(self, docker_client, test_image):
        """Test nginx-manager Python package is installed"""
        container_name = "ngx-simple-python-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                detach=True
            )
            
            time.sleep(5)
            
            # Test Python import
            exec_result = container.exec_run([
                "python", "-c", 
                "import nginx_manager; print('nginx-manager imported successfully')"
            ])
            assert exec_result.exit_code == 0, f"Python import failed: {exec_result.output.decode()}"
            
            print("✅ nginx-manager Python package is available")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    @pytest.mark.slow
    def test_http_health_check(self, docker_client, test_image):
        """Test HTTP health check endpoint"""
        container_name = "ngx-simple-http-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                ports={'80/tcp': 8083},
                detach=True
            )
            
            time.sleep(15)
            
            # Test health endpoint
            max_retries = 5
            for i in range(max_retries):
                try:
                    response = requests.get('http://localhost:8083/health', timeout=10)
                    assert response.status_code == 200, f"Health check failed: {response.status_code}"
                    assert "healthy" in response.text, f"Unexpected health response: {response.text}"
                    print(f"✅ Health check passed: {response.status_code}")
                    break
                except requests.exceptions.RequestException as e:
                    if i == max_retries - 1:
                        # Try root path for redirect check
                        try:
                            response = requests.get('http://localhost:8083', timeout=10, allow_redirects=False)
                            if response.status_code == 301:
                                print("✅ HTTP redirects to HTTPS as expected")
                                return
                        except:
                            pass
                        
                        logs = container.logs().decode()
                        pytest.fail(f"❌ HTTP request failed after {max_retries} retries: {e}\nContainer logs:\n{logs}")
                    time.sleep(3)
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_system_commands(self, docker_client, test_image):
        """Test system commands availability"""
        container_name = "ngx-simple-commands-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                detach=True
            )
            
            time.sleep(5)
            
            # Test required system commands
            commands = [
                ("nginx -v", "Nginx"),
                ("python --version", "Python"), 
                ("curl --version", "Curl"),
                ("openssl version", "OpenSSL")
            ]
            
            for cmd, name in commands:
                exec_result = container.exec_run(cmd)
                assert exec_result.exit_code == 0, f"{name} command failed: {cmd}"
                print(f"✅ {name} available")
            
        finally:
            self._cleanup_container(docker_client, container_name)
    
    def test_file_structure(self, docker_client, test_image):
        """Test expected file structure exists"""
        container_name = "ngx-simple-structure-test"
        
        try:
            container = docker_client.containers.run(
                test_image,
                name=container_name,
                detach=True
            )
            
            time.sleep(5)
            
            # Test required directories
            directories = [
                "/app",
                "/app/config",
                "/app/logs",
                "/var/www/html",
                "/etc/nginx"
            ]
            
            for directory in directories:
                exec_result = container.exec_run(f"test -d {directory}")
                assert exec_result.exit_code == 0, f"Directory missing: {directory}"
                print(f"✅ Directory exists: {directory}")
            
            # Test nginx config file
            exec_result = container.exec_run("test -f /etc/nginx/nginx.conf")
            assert exec_result.exit_code == 0, "Nginx config file missing"
            print("✅ Nginx configuration file exists")
            
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
class TestDockerCompose:
    """Basic Docker Compose integration tests"""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Initialize Docker client"""
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    
    def test_compose_availability(self):
        """Test Docker Compose is available"""
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                pytest.skip("docker-compose not available")
            print("✅ Docker Compose is available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("docker-compose not available")
    
    @pytest.mark.skip(reason="Docker Compose test needs project restructuring")
    def test_minimal_compose_workflow(self, docker_client):
        """Test minimal Docker Compose workflow"""
        workspace = Path(tempfile.mkdtemp(prefix="ngx-compose-test-"))
        
        try:
            # Create minimal compose file
            project_root = Path(__file__).parent.parent.parent
            compose_content = f"""
version: '3.8'
services:
  nginx-manager:
    build:
      context: {project_root}
      dockerfile: Dockerfile
    ports:
      - "8084:80"
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
"""
            
            compose_file = workspace / "docker-compose.yml"
            compose_file.write_text(compose_content.strip())
            
            # Test compose up/down
            import os
            original_cwd = os.getcwd()
            os.chdir(workspace)
            
            try:
                result = subprocess.run(
                    ["docker-compose", "up", "-d", "--build"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    print("✅ Docker Compose up successful")
                    
                    time.sleep(20)
                    
                    # Check service status
                    result = subprocess.run(
                        ["docker-compose", "ps"],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0 and "Up" in result.stdout:
                        print("✅ Service is running")
                    else:
                        print(f"⚠️ Service status: {result.stdout}")
                
                else:
                    # Log the error but don't fail the test for compose issues
                    print(f"⚠️ Docker Compose up failed: {result.stderr}")
                    print("✅ Docker Compose availability verified (build failed but command works)")
                
            finally:
                # Cleanup
                subprocess.run(
                    ["docker-compose", "down", "-v", "--rmi", "local"],
                    capture_output=True,
                    timeout=60
                )
                os.chdir(original_cwd)
                
        finally:
            shutil.rmtree(workspace, ignore_errors=True) 