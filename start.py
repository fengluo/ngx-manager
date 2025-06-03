#!/usr/bin/env python3
"""
Nginx Manager startup script (Python version)
Used to build and start Docker containers
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Optional

class DockerManager:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.image_name = 'nginx-manager'
        self.container_name = 'nginx-manager'
        
    def run_command(self, cmd: List[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
        """Execute command"""
        try:
            print(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Command execution failed: {e}")
            if capture_output and e.stderr:
                print(f"Error output: {e.stderr}")
            raise
    
    def check_docker(self) -> bool:
        """Check if Docker is available"""
        print("Checking Docker environment...")
        
        try:
            result = self.run_command(['docker', '--version'], capture_output=True)
            print(f"Docker version: {result.stdout.strip()}")
            
            # Check Docker daemon
            self.run_command(['docker', 'info'], capture_output=True)
            print("Docker environment check passed")
            return True
            
        except subprocess.CalledProcessError:
            print("Error: Docker is not installed or not running")
            print("Please ensure Docker is installed and running")
            return False
    
    def check_docker_compose(self) -> bool:
        """Check if Docker Compose is available"""
        try:
            result = self.run_command(['docker-compose', '--version'], capture_output=True)
            print(f"Docker Compose version: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError:
            try:
                result = self.run_command(['docker', 'compose', 'version'], capture_output=True)
                print(f"Docker Compose version: {result.stdout.strip()}")
                return True
            except subprocess.CalledProcessError:
                print("Warning: Docker Compose not found, will use docker command")
                return False
    
    def build_image(self, no_cache: bool = False) -> bool:
        """Build Docker image"""
        print(f"Building Docker image: {self.image_name}")
        
        cmd = ['docker', 'build', '-t', self.image_name, '.']
        if no_cache:
            cmd.append('--no-cache')
            
        try:
            self.run_command(cmd)
            print("Image build successful")
            return True
        except subprocess.CalledProcessError:
            print("Image build failed")
            return False
    
    def stop_container(self) -> bool:
        """Stop container"""
        print(f"Stopping container: {self.container_name}")
        
        try:
            # Check if container exists
            result = self.run_command([
                'docker', 'ps', '-a', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'
            ], capture_output=True, check=False)
            
            if self.container_name in result.stdout:
                # Stop container
                self.run_command(['docker', 'stop', self.container_name], check=False)
                print("Container stopped")
                
                # Remove container
                self.run_command(['docker', 'rm', self.container_name], check=False)
                print("Container removed")
                
            return True
            
        except Exception as e:
            print(f"Failed to stop container: {e}")
            return False
    
    def start_container(self, detach: bool = True, ports: Optional[List[str]] = None) -> bool:
        """Start container"""
        print(f"Starting container: {self.container_name}")
        
        # Default port mapping
        if ports is None:
            ports = ['80:80', '443:443']
            
        # Build docker run command
        cmd = ['docker', 'run']
        
        if detach:
            cmd.append('-d')
            
        cmd.extend(['--name', self.container_name])
        
        # Add port mapping
        for port in ports:
            cmd.extend(['-p', port])
            
        # Add volume mapping
        volumes = [
            f'{self.project_dir}/config:/app/config',
            f'{self.project_dir}/logs:/app/logs',
            f'{self.project_dir}/certs:/app/certs',
            f'{self.project_dir}/nginx-conf:/etc/nginx/conf.d'
        ]
        
        for volume in volumes:
            cmd.extend(['-v', volume])
            
        # Add environment variables
        env_vars = [
            'TZ=Asia/Shanghai'
        ]
        
        for env in env_vars:
            cmd.extend(['-e', env])
            
        # Add restart policy
        cmd.extend(['--restart', 'unless-stopped'])
        
        # Add image name
        cmd.append(self.image_name)
        
        try:
            self.run_command(cmd)
            print("Container started successfully")
            
            if detach:
                print(f"Container is running in background, name: {self.container_name}")
                print("Use the following command to view logs:")
                print(f"  docker logs -f {self.container_name}")
                print("Use the following command to stop container:")
                print(f"  docker stop {self.container_name}")
                
            return True
            
        except subprocess.CalledProcessError:
            print("Container start failed")
            return False
    
    def start_with_compose(self, detach: bool = True) -> bool:
        """Start with Docker Compose"""
        print("Starting services with Docker Compose...")
        
        compose_file = self.project_dir / 'docker-compose.yml'
        if not compose_file.exists():
            print("Error: docker-compose.yml file does not exist")
            return False
            
        try:
            cmd = ['docker-compose', 'up']
            if detach:
                cmd.append('-d')
                
            self.run_command(cmd)
            print("Services started successfully")
            
            if detach:
                print("Services are running in background")
                print("Use the following command to view logs:")
                print("  docker-compose logs -f")
                print("Use the following command to stop services:")
                print("  docker-compose down")
                
            return True
            
        except subprocess.CalledProcessError:
            print("Service start failed")
            return False
    
    def stop_with_compose(self) -> bool:
        """Stop with Docker Compose"""
        print("Stopping services with Docker Compose...")
        
        try:
            self.run_command(['docker-compose', 'down'])
            print("Services stopped")
            return True
        except subprocess.CalledProcessError:
            print("Failed to stop services")
            return False
    
    def show_logs(self, follow: bool = False) -> bool:
        """Show container logs"""
        print(f"Showing container logs: {self.container_name}")
        
        try:
            cmd = ['docker', 'logs']
            if follow:
                cmd.append('-f')
            cmd.append(self.container_name)
            
            self.run_command(cmd)
            return True
            
        except subprocess.CalledProcessError:
            print("Failed to show logs")
            return False
    
    def show_status(self) -> bool:
        """Show container status"""
        print("Container status:")
        
        try:
            # Show container status
            self.run_command([
                'docker', 'ps', '-a', '--filter', f'name={self.container_name}',
                '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
            ])
            
            # Show image information
            print("\nImage information:")
            self.run_command([
                'docker', 'images', self.image_name,
                '--format', 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'
            ])
            
            return True
            
        except subprocess.CalledProcessError:
            print("Failed to get status")
            return False
    
    def create_directories(self):
        """Create necessary directories"""
        directories = ['config', 'logs', 'certs', 'nginx-conf']
        
        for dir_name in directories:
            dir_path = self.project_dir / dir_name
            dir_path.mkdir(exist_ok=True)
            print(f"Created directory: {dir_path}")
    
    def show_help(self):
        """Show help information"""
        help_text = """
Nginx Manager startup script

Usage:
  python3 start.py [options] [command]

Commands:
  build       Build Docker image
  start       Start container (default)
  stop        Stop container
  restart     Restart container
  logs        Show logs
  status      Show status
  compose-up  Start with Docker Compose
  compose-down Stop with Docker Compose

Options:
  --no-cache  Do not use cache when building
  --no-detach Run container in foreground
  --follow    Follow log output
  --help      Show this help information

Examples:
  python3 start.py                    # Build and start container
  python3 start.py build --no-cache   # Rebuild image
  python3 start.py logs --follow      # Follow logs
  python3 start.py compose-up         # Start with Docker Compose
"""
        print(help_text)

def main():
    parser = argparse.ArgumentParser(description='Nginx Manager startup script', add_help=False)
    parser.add_argument('command', nargs='?', default='start',
                       choices=['build', 'start', 'stop', 'restart', 'logs', 'status', 
                               'compose-up', 'compose-down'],
                       help='Command to execute')
    parser.add_argument('--no-cache', action='store_true', help='Do not use cache when building')
    parser.add_argument('--no-detach', action='store_true', help='Run container in foreground')
    parser.add_argument('--follow', action='store_true', help='Follow log output')
    parser.add_argument('--help', action='store_true', help='Show help information')
    
    args = parser.parse_args()
    
    manager = DockerManager()
    
    if args.help:
        manager.show_help()
        return
    
    print("=== Nginx Manager Startup Script ===")
    print(f"Project directory: {manager.project_dir}")
    print(f"Image name: {manager.image_name}")
    print(f"Container name: {manager.container_name}")
    print()
    
    # Check Docker environment
    if not manager.check_docker():
        sys.exit(1)
    
    # Create necessary directories
    manager.create_directories()
    
    try:
        if args.command == 'build':
            success = manager.build_image(no_cache=args.no_cache)
            
        elif args.command == 'start':
            # Build image first
            if not manager.build_image(no_cache=args.no_cache):
                sys.exit(1)
                
            # Stop existing container
            manager.stop_container()
            
            # Start new container
            success = manager.start_container(detach=not args.no_detach)
            
        elif args.command == 'stop':
            success = manager.stop_container()
            
        elif args.command == 'restart':
            # Stop container
            manager.stop_container()
            
            # Rebuild image
            if not manager.build_image():
                sys.exit(1)
                
            # Start container
            success = manager.start_container(detach=not args.no_detach)
            
        elif args.command == 'logs':
            success = manager.show_logs(follow=args.follow)
            
        elif args.command == 'status':
            success = manager.show_status()
            
        elif args.command == 'compose-up':
            if manager.check_docker_compose():
                success = manager.start_with_compose(detach=not args.no_detach)
            else:
                print("Docker Compose is not available, starting with docker command...")
                if not manager.build_image():
                    sys.exit(1)
                manager.stop_container()
                success = manager.start_container(detach=not args.no_detach)
                
        elif args.command == 'compose-down':
            if manager.check_docker_compose():
                success = manager.stop_with_compose()
            else:
                success = manager.stop_container()
                
        else:
            print(f"Unknown command: {args.command}")
            manager.show_help()
            sys.exit(1)
            
        if success:
            print(f"\n✅ Command '{args.command}' executed successfully")
        else:
            print(f"\n❌ Command '{args.command}' execution failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nExecution failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 