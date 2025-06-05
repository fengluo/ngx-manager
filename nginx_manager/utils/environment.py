"""
Environment management for native installation
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List
from ..config.settings import settings


class EnvironmentManager:
    """Environment setup and management for native installation"""
    
    def __init__(self):
        """Initialize environment manager"""
        self.system = platform.system().lower()
        self.distro = self._detect_distro()
    
    def _detect_distro(self) -> str:
        """Detect Linux distribution"""
        if self.system != 'linux':
            return self.system
        
        try:
            # Try to read /etc/os-release
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                if 'ubuntu' in content.lower():
                    return 'ubuntu'
                elif 'debian' in content.lower():
                    return 'debian'
                elif 'centos' in content.lower():
                    return 'centos'
                elif 'rhel' in content.lower() or 'red hat' in content.lower():
                    return 'rhel'
                elif 'fedora' in content.lower():
                    return 'fedora'
                elif 'arch' in content.lower():
                    return 'arch'
        except FileNotFoundError:
            pass
        
        # Fallback detection methods
        if Path('/etc/debian_version').exists():
            return 'debian'
        elif Path('/etc/redhat-release').exists():
            return 'rhel'
        
        return 'unknown'
    
    def check_environment(self) -> Dict[str, bool]:
        """Check environment status"""
        checks = {}
        
        # Check Python version
        checks['python'] = sys.version_info >= (3, 8)
        
        # Check nginx
        checks['nginx'] = self._check_command_exists('nginx')
        
        # Check openssl
        checks['openssl'] = self._check_command_exists('openssl')
        
        # Check curl
        checks['curl'] = self._check_command_exists('curl')
        
        # Check if we can write to nginx config directory
        try:
            test_file = settings.nginx_config_dir / '.write_test'
            test_file.touch()
            test_file.unlink()
            checks['nginx_config_writable'] = True
        except (PermissionError, OSError):
            checks['nginx_config_writable'] = False
        
        # Check acme.sh
        checks['acme.sh'] = self._check_acme_sh()
        
        return checks
    
    def _check_command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run([command, '--version'], 
                         capture_output=True, 
                         check=False,
                         timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_acme_sh(self) -> bool:
        """Check if acme.sh is installed"""
        acme_paths = [
            Path.home() / '.acme.sh' / 'acme.sh',
            Path('/usr/local/bin/acme.sh'),
            Path('/usr/bin/acme.sh'),
        ]
        
        for path in acme_paths:
            if path.exists() and path.is_file():
                return True
        
        return self._check_command_exists('acme.sh')
    
    def install_dependencies(self) -> Dict[str, Any]:
        """Install system dependencies"""
        try:
            if self.system == 'linux':
                return self._install_linux_dependencies()
            elif self.system == 'darwin':
                return self._install_macos_dependencies()
            else:
                return {
                    'success': False,
                    'error': f'Unsupported operating system: {self.system}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _install_linux_dependencies(self) -> Dict[str, Any]:
        """Install dependencies on Linux"""
        if self.distro in ['ubuntu', 'debian']:
            return self._install_apt_dependencies()
        elif self.distro in ['centos', 'rhel', 'fedora']:
            return self._install_yum_dependencies()
        elif self.distro == 'arch':
            return self._install_pacman_dependencies()
        else:
            return {
                'success': False,
                'error': f'Unsupported Linux distribution: {self.distro}'
            }
    
    def _install_apt_dependencies(self) -> Dict[str, Any]:
        """Install dependencies using apt (Ubuntu/Debian)"""
        packages = ['nginx', 'openssl', 'curl', 'socat', 'cron']
        
        try:
            # Update package list
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            
            # Install packages
            cmd = ['sudo', 'apt', 'install', '-y'] + packages
            subprocess.run(cmd, check=True)
            
            # Enable and start nginx
            subprocess.run(['sudo', 'systemctl', 'enable', 'nginx'], check=False)
            subprocess.run(['sudo', 'systemctl', 'start', 'nginx'], check=False)
            
            return {'success': True}
        
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to install packages: {e}'
            }
    
    def _install_yum_dependencies(self) -> Dict[str, Any]:
        """Install dependencies using yum/dnf (CentOS/RHEL/Fedora)"""
        # Use dnf if available, otherwise yum
        pkg_manager = 'dnf' if self._check_command_exists('dnf') else 'yum'
        packages = ['nginx', 'openssl', 'curl', 'socat', 'cronie']
        
        try:
            # Install packages
            cmd = ['sudo', pkg_manager, 'install', '-y'] + packages
            subprocess.run(cmd, check=True)
            
            # Enable and start nginx
            subprocess.run(['sudo', 'systemctl', 'enable', 'nginx'], check=False)
            subprocess.run(['sudo', 'systemctl', 'start', 'nginx'], check=False)
            
            return {'success': True}
        
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to install packages: {e}'
            }
    
    def _install_pacman_dependencies(self) -> Dict[str, Any]:
        """Install dependencies using pacman (Arch Linux)"""
        packages = ['nginx', 'openssl', 'curl', 'socat', 'cronie']
        
        try:
            # Update package list
            subprocess.run(['sudo', 'pacman', '-Sy'], check=True)
            
            # Install packages
            cmd = ['sudo', 'pacman', '-S', '--noconfirm'] + packages
            subprocess.run(cmd, check=True)
            
            # Enable and start nginx
            subprocess.run(['sudo', 'systemctl', 'enable', 'nginx'], check=False)
            subprocess.run(['sudo', 'systemctl', 'start', 'nginx'], check=False)
            
            return {'success': True}
        
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to install packages: {e}'
            }
    
    def _install_macos_dependencies(self) -> Dict[str, Any]:
        """Install dependencies on macOS"""
        try:
            # Check if Homebrew is installed
            if not self._check_command_exists('brew'):
                return {
                    'success': False,
                    'error': 'Homebrew is required for macOS installation. Please install it first.'
                }
            
            packages = ['nginx', 'openssl', 'curl', 'socat']
            
            # Install packages
            for package in packages:
                subprocess.run(['brew', 'install', package], check=True)
            
            # Start nginx service
            subprocess.run(['brew', 'services', 'start', 'nginx'], check=False)
            
            return {'success': True}
        
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to install packages: {e}'
            }
    
    def setup_nginx(self) -> Dict[str, Any]:
        """Setup nginx configuration"""
        try:
            # Ensure nginx config directory exists
            settings.nginx_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create basic nginx configuration if it doesn't exist
            main_config = self._get_nginx_main_config_path()
            if main_config and not self._nginx_config_includes_our_dir(main_config):
                self._update_nginx_main_config(main_config)
            
            # Test nginx configuration
            result = subprocess.run(['nginx', '-t'], capture_output=True, check=False)
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Nginx configuration test failed: {result.stderr.decode()}'
                }
            
            return {'success': True}
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_nginx_main_config_path(self) -> Path:
        """Get nginx main configuration file path"""
        possible_paths = [
            Path('/etc/nginx/nginx.conf'),
            Path('/usr/local/etc/nginx/nginx.conf'),
            Path('/opt/homebrew/etc/nginx/nginx.conf'),
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def _nginx_config_includes_our_dir(self, config_path: Path) -> bool:
        """Check if nginx config includes our configuration directory"""
        try:
            with open(config_path, 'r') as f:
                content = f.read()
                return str(settings.nginx_config_dir) in content
        except Exception:
            return False
    
    def _update_nginx_main_config(self, config_path: Path) -> None:
        """Update nginx main configuration to include our directory"""
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Add include directive in http block
            include_line = f"    include {settings.nginx_config_dir}/*.conf;"
            
            if 'http {' in content and include_line not in content:
                # Find the http block and add our include
                lines = content.split('\n')
                new_lines = []
                in_http_block = False
                
                for line in lines:
                    new_lines.append(line)
                    
                    if 'http {' in line:
                        in_http_block = True
                    elif in_http_block and '}' in line and line.strip() == '}':
                        # Add our include before the closing brace
                        new_lines.insert(-1, include_line)
                        in_http_block = False
                
                # Write back to file (requires sudo)
                new_content = '\n'.join(new_lines)
                temp_file = Path('/tmp/nginx.conf.tmp')
                with open(temp_file, 'w') as f:
                    f.write(new_content)
                
                subprocess.run(['sudo', 'cp', str(temp_file), str(config_path)], check=True)
                temp_file.unlink()
        
        except Exception as e:
            raise Exception(f"Failed to update nginx configuration: {e}")
    
    def setup_ssl(self) -> Dict[str, Any]:
        """Setup SSL/ACME tools"""
        try:
            if self._check_acme_sh():
                return {'success': True, 'message': 'acme.sh already installed'}
            
            # Install acme.sh
            install_cmd = [
                'curl', 'https://get.acme.sh', '|',
                'sh', '-s', 'email=' + settings.ssl_email
            ]
            
            # Use shell=True for pipe command
            result = subprocess.run(
                ' '.join(install_cmd),
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Create symlink if needed
            acme_path = Path.home() / '.acme.sh' / 'acme.sh'
            if acme_path.exists():
                try:
                    subprocess.run([
                        'sudo', 'ln', '-sf', str(acme_path), '/usr/local/bin/acme.sh'
                    ], check=False)
                except subprocess.CalledProcessError:
                    pass  # Ignore if symlink creation fails
            
            return {'success': True}
        
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to install acme.sh: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 