"""
Core nginx management functionality
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..config.settings import settings
from ..ssl.manager import SSLManager
from ..templates.generator import ConfigGenerator


class NginxManager:
    """Main nginx management class"""
    
    def __init__(self):
        """Initialize nginx manager"""
        self.ssl_manager = SSLManager()
        self.config_generator = ConfigGenerator()
        
        # Ensure necessary directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            settings.nginx_config_dir,
            settings.ssl_certs_dir,
            settings.logs_dir,
            settings.www_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_nginx_status(self) -> Dict[str, Any]:
        """Get nginx status information"""
        status = {
            'status': 'unknown',
            'config_test': False,
            'version': None,
            'pid': None
        }
        
        try:
            # Check if nginx is running
            methods = [
                (['pgrep', '-f', 'nginx'], 'pgrep'),
                (['pidof', 'nginx'], 'pidof'),
                (['systemctl', 'is-active', 'nginx'], 'systemctl')
            ]
            
            for cmd, method in methods:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    if result.returncode == 0:
                        status['status'] = 'running'
                        if method == 'pgrep' and result.stdout.strip():
                            status['pid'] = result.stdout.strip().split('\n')[0]
                        break
                except FileNotFoundError:
                    continue
            
            if status['status'] == 'unknown':
                status['status'] = 'stopped'
            
            # Test nginx configuration
            result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                text=True,
                check=False
            )
            status['config_test'] = result.returncode == 0
            
            # Get nginx version
            result = subprocess.run(
                ['nginx', '-v'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                # nginx outputs version to stderr
                version_line = result.stderr.strip()
                if 'nginx/' in version_line:
                    status['version'] = version_line.split('nginx/')[1].split(' ')[0]
        
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def add_site(self, domain: str, backend: Optional[str] = None, 
                 ssl: bool = True, force: bool = False) -> Dict[str, Any]:
        """Add a new site configuration"""
        try:
            # Check if site already exists
            config_file = settings.nginx_config_dir / f"{domain}.conf"
            if config_file.exists() and not force:
                return {
                    'success': False,
                    'error': f"Site {domain} already exists. Use --force to overwrite."
                }
            
            # Generate nginx configuration
            config_content = self.config_generator.generate_site_config(
                domain=domain,
                backend=backend,
                ssl=ssl
            )
            
            # Write configuration file
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # If SSL is enabled, obtain certificate
            if ssl:
                ssl_result = self.ssl_manager.obtain_certificate(domain)
                if not ssl_result['success']:
                    # Remove the config file if SSL setup failed
                    config_file.unlink(missing_ok=True)
                    return {
                        'success': False,
                        'error': f"Failed to obtain SSL certificate: {ssl_result['error']}"
                    }
            
            # Test nginx configuration
            if not self._test_nginx_config():
                config_file.unlink(missing_ok=True)
                return {
                    'success': False,
                    'error': "Generated nginx configuration is invalid"
                }
            
            # Reload nginx
            reload_result = self.reload_nginx()
            if not reload_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to reload nginx: {reload_result['error']}"
                }
            
            return {
                'success': True,
                'domain': domain,
                'ssl': ssl,
                'config_file': str(config_file)
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def remove_site(self, domain: str) -> Dict[str, Any]:
        """Remove a site configuration"""
        try:
            config_file = settings.nginx_config_dir / f"{domain}.conf"
            
            if not config_file.exists():
                return {
                    'success': False,
                    'error': f"Site {domain} does not exist"
                }
            
            # Remove configuration file
            config_file.unlink()
            
            # Remove SSL certificate
            self.ssl_manager.remove_certificate(domain)
            
            # Reload nginx
            reload_result = self.reload_nginx()
            if not reload_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to reload nginx: {reload_result['error']}"
                }
            
            return {
                'success': True,
                'domain': domain
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_sites(self) -> List[Dict[str, Any]]:
        """List all configured sites"""
        sites = []
        
        try:
            # Scan nginx config directory for .conf files
            for config_file in settings.nginx_config_dir.glob("*.conf"):
                if config_file.name == "default.conf":
                    continue
                
                domain = config_file.stem
                site_info = {
                    'domain': domain,
                    'config_file': str(config_file),
                    'active': True,  # Assume active if config exists
                }
                
                # Check if SSL certificate exists
                cert_path = settings.ssl_certs_dir / domain / "fullchain.pem"
                site_info['ssl'] = cert_path.exists()
                
                # Try to extract backend from config file
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Simple regex to extract proxy_pass
                        import re
                        match = re.search(r'proxy_pass\s+([^;]+);', content)
                        if match:
                            site_info['backend'] = match.group(1).strip()
                except Exception:
                    pass
                
                sites.append(site_info)
        
        except Exception as e:
            # Return empty list on error, caller can handle
            pass
        
        return sites
    
    def renew_certificates(self, domain: Optional[str] = None, 
                          force: bool = False) -> Dict[str, Any]:
        """Renew SSL certificates"""
        try:
            if domain:
                # Renew specific domain
                result = self.ssl_manager.renew_certificate(domain, force=force)
                if result['success']:
                    renewed = [domain] if result.get('renewed') else []
                    
                    # Reload nginx if certificate was renewed
                    if result.get('renewed'):
                        reload_result = self.reload_nginx()
                        if not reload_result['success']:
                            return {
                                'success': False,
                                'error': f'Certificate renewed but nginx reload failed: {reload_result["error"]}'
                            }
                    
                    return {
                        'success': True,
                        'renewed': renewed,
                        'nginx_reloaded': result.get('renewed', False)
                    }
                else:
                    return result
            else:
                # Renew all certificates
                sites = self.list_sites()
                ssl_sites = [site['domain'] for site in sites if site.get('ssl')]
                
                renewed = []
                errors = []
                
                for site_domain in ssl_sites:
                    result = self.ssl_manager.renew_certificate(site_domain, force=force)
                    if result['success'] and result.get('renewed'):
                        renewed.append(site_domain)
                    elif not result['success']:
                        errors.append(f"{site_domain}: {result['error']}")
                
                # Reload nginx if any certificates were renewed
                nginx_reloaded = False
                if renewed:
                    reload_result = self.reload_nginx()
                    if reload_result['success']:
                        nginx_reloaded = True
                    else:
                        # Add reload error but don't fail the entire operation
                        errors.append(f"nginx reload failed: {reload_result['error']}")
                
                if errors and not renewed:
                    return {
                        'success': False,
                        'error': '; '.join(errors)
                    }
                
                return {
                    'success': True,
                    'renewed': renewed,
                    'errors': errors if errors else None,
                    'nginx_reloaded': nginx_reloaded
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def reload_nginx(self) -> Dict[str, Any]:
        """Reload nginx configuration"""
        try:
            # Try different nginx reload methods in order of preference
            commands = [
                ['nginx', '-s', 'reload'],           # Direct nginx command
                ['systemctl', 'reload', 'nginx'],    # systemd
                ['service', 'nginx', 'reload']       # sysv
            ]
            
            success = False
            last_error = None
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    success = True
                    break
                except subprocess.CalledProcessError as e:
                    last_error = f"{' '.join(cmd)}: {e.stderr if e.stderr else str(e)}"
                    continue
                except FileNotFoundError:
                    last_error = f"{' '.join(cmd)}: command not found"
                    continue
            
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to reload nginx. Last error: {last_error}'
                }
            
            return {'success': True}
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_nginx_config(self) -> bool:
        """Test nginx configuration"""
        try:
            result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False 
    
    def check_auto_renewal_status(self) -> Dict[str, Any]:
        """Check if automatic renewal is enabled"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                return {'enabled': False}
            
            crontab_content = result.stdout
            nginx_manager_entries = [line for line in crontab_content.split('\n') 
                                   if '# nginx-manager auto-renewal' in line]
            
            if nginx_manager_entries:
                entry = nginx_manager_entries[0].strip()
                # Parse cron schedule
                parts = entry.split()
                if len(parts) >= 5:
                    schedule_part = ' '.join(parts[:5])
                    
                    # Determine interval from schedule
                    if schedule_part == '0 2 * * *':
                        interval = 'daily at 2:00 AM'
                    elif schedule_part == '0 2 * * 0':
                        interval = 'weekly on Sunday at 2:00 AM'
                    elif schedule_part == '0 2 1 * *':
                        interval = 'monthly on 1st at 2:00 AM'
                    else:
                        interval = f'custom: {schedule_part}'
                    
                    return {
                        'enabled': True,
                        'schedule': interval,
                        'cron_entry': entry
                    }
            
            return {'enabled': False}
            
        except Exception as e:
            return {
                'enabled': False,
                'error': str(e)
            }
    
    def disable_auto_renewal(self) -> Dict[str, Any]:
        """Disable automatic certificate renewal"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                return {'success': True, 'message': 'No crontab entries found'}
            
            current_crontab = result.stdout
            
            # Remove nginx-manager entries
            lines = [line for line in current_crontab.split('\n') 
                    if line.strip() and '# nginx-manager auto-renewal' not in line]
            
            new_crontab = '\n'.join(lines)
            if new_crontab.strip():
                new_crontab += '\n'
            
            # Update crontab
            proc = subprocess.run(['crontab', '-'], input=new_crontab, text=True, 
                                capture_output=True, check=True)
            
            return {'success': True}
            
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to update crontab: {e.stderr or str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 