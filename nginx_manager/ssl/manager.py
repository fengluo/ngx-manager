"""
SSL certificate management using acme.sh
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from ..config.settings import settings


class SSLManager:
    """SSL certificate manager using acme.sh"""
    
    def __init__(self):
        """Initialize SSL manager"""
        self.acme_sh_path = self._find_acme_sh()
        self.certs_dir = settings.ssl_certs_dir
        
        # Ensure certificates directory exists
        self.certs_dir.mkdir(parents=True, exist_ok=True)
    
    def _find_acme_sh(self) -> Optional[Path]:
        """Find acme.sh executable"""
        possible_paths = [
            Path.home() / '.acme.sh' / 'acme.sh',
            Path('/usr/local/bin/acme.sh'),
            Path('/usr/bin/acme.sh'),
            Path('/root/.acme.sh/acme.sh'),  # Common Docker path
            Path('/app/.acme.sh/acme.sh'),   # Alternative Docker path
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_file():
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'acme.sh'], capture_output=True, text=True)
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            pass
        except FileNotFoundError:
            pass
        
        return None
    
    def _run_acme_command(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run acme.sh command"""
        if not self.acme_sh_path:
            # Provide detailed error information
            searched_paths = [
                str(Path.home() / '.acme.sh' / 'acme.sh'),
                '/usr/local/bin/acme.sh',
                '/usr/bin/acme.sh',
                '/root/.acme.sh/acme.sh',
                '/app/.acme.sh/acme.sh',
            ]
            error_msg = f"acme.sh not found. Searched paths:\n" + "\n".join(f"  - {path}" for path in searched_paths)
            error_msg += "\n\nPlease install acme.sh using: curl https://get.acme.sh | sh"
            raise RuntimeError(error_msg)
        
        cmd = [str(self.acme_sh_path)] + args
        
        # Set environment variables for acme.sh
        env = os.environ.copy()
        env.update({
            'ACME_HOME': str(Path.home() / '.acme.sh'),
            'LE_WORKING_DIR': str(Path.home() / '.acme.sh'),
        })
        
        return subprocess.run(cmd, capture_output=True, text=True, check=check, env=env)
    
    def obtain_certificate(self, domain: str, challenge_method: str = 'http') -> Dict[str, Any]:
        """Obtain SSL certificate for domain"""
        try:
            # Check if certificate already exists and is valid
            if self._certificate_exists(domain) and not self._certificate_needs_renewal(domain):
                return {
                    'success': True,
                    'message': f'Certificate for {domain} already exists and is valid',
                    'domain': domain
                }
            
            # Use webroot method with nginx document root
            if challenge_method == 'http':
                return self._obtain_with_webroot(domain)
            elif challenge_method == 'dns':
                # DNS challenge - would need DNS provider specific setup
                return {
                    'success': False,
                    'error': 'DNS challenge not implemented yet'
                }
            else:
                return {
                    'success': False,
                    'error': f'Unsupported challenge method: {challenge_method}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'domain': domain
            }
    
    def _obtain_with_webroot(self, domain: str) -> Dict[str, Any]:
        """Obtain certificate using webroot method"""
        # Ensure nginx webroot directory exists and is accessible
        webroot = Path('/var/www/html')
        try:
            webroot.mkdir(parents=True, exist_ok=True)
            # Create .well-known/acme-challenge directory
            acme_challenge_dir = webroot / '.well-known' / 'acme-challenge'
            acme_challenge_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = acme_challenge_dir / 'test'
            test_file.write_text('test')
            test_file.unlink()
            
        except (PermissionError, OSError) as e:
            # If we can't write to /var/www/html, try alternative approach
            return self._obtain_with_nginx_reload(domain)
        
        # Prepare acme.sh command for webroot mode
        args = [
            '--issue',
            '-d', domain,
            '--webroot', str(webroot),
            '--server', settings.ssl_ca_server,
            '--email', settings.ssl_email
        ]
        
        # Add staging flag if configured
        if settings.acme_staging:
            args.append('--staging')
        
        # Run acme.sh
        result = self._run_acme_command(args, check=False)
        
        if result.returncode != 0:
            # If webroot failed, try with nginx reload method
            return self._obtain_with_nginx_reload(domain)
        
        # Install certificate to our directory
        install_result = self._install_certificate(domain)
        if not install_result['success']:
            return install_result
        
        return {
            'success': True,
            'domain': domain,
            'certificate_path': str(self.certs_dir / domain)
        }
    
    def _obtain_with_nginx_reload(self, domain: str) -> Dict[str, Any]:
        """Obtain certificate by temporarily stopping nginx"""
        try:
            # Check if nginx is running
            nginx_was_running = self._is_nginx_running()
            
            if nginx_was_running:
                # Stop nginx temporarily
                stop_result = subprocess.run(['nginx', '-s', 'quit'], capture_output=True, text=True)
                if stop_result.returncode != 0:
                    # Try kill if graceful stop failed
                    subprocess.run(['pkill', '-f', 'nginx'], capture_output=True, text=True)
                
                # Wait a moment for nginx to stop
                import time
                time.sleep(2)
            
            # Use standalone mode
            args = [
                '--issue',
                '-d', domain,
                '--standalone',
                '--httpport', '80',
                '--server', settings.ssl_ca_server,
                '--email', settings.ssl_email
            ]
            
            if settings.acme_staging:
                args.append('--staging')
            
            result = self._run_acme_command(args, check=False)
            
            # Restart nginx if it was running
            if nginx_was_running:
                subprocess.run(['nginx'], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Failed to obtain certificate: {result.stderr}',
                    'domain': domain
                }
            
            # Install certificate to our directory
            install_result = self._install_certificate(domain)
            if not install_result['success']:
                return install_result
            
            return {
                'success': True,
                'domain': domain,
                'certificate_path': str(self.certs_dir / domain)
            }
        
        except Exception as e:
            # Make sure nginx is restarted even if something goes wrong
            if nginx_was_running:
                subprocess.run(['nginx'], capture_output=True, text=True)
            return {
                'success': False,
                'error': f'Failed to obtain certificate with nginx reload: {str(e)}',
                'domain': domain
            }
    
    def _is_nginx_running(self) -> bool:
        """Check if nginx is currently running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'nginx'], capture_output=True, text=True)
            return result.returncode == 0 and result.stdout.strip()
        except subprocess.CalledProcessError:
            return False
    
    def _install_certificate(self, domain: str) -> Dict[str, Any]:
        """Install certificate to our certificates directory"""
        try:
            cert_dir = self.certs_dir / domain
            cert_dir.mkdir(parents=True, exist_ok=True)
            
            args = [
                '--install-cert',
                '-d', domain,
                '--cert-file', str(cert_dir / 'cert.pem'),
                '--key-file', str(cert_dir / 'privkey.pem'),
                '--fullchain-file', str(cert_dir / 'fullchain.pem'),
                '--ca-file', str(cert_dir / 'chain.pem'),
            ]
            
            result = self._run_acme_command(args)
            
            return {
                'success': True,
                'domain': domain,
                'certificate_dir': str(cert_dir)
            }
        
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to install certificate: {e.stderr}',
                'domain': domain
            }
    
    def renew_certificate(self, domain: str, force: bool = False) -> Dict[str, Any]:
        """Renew SSL certificate"""
        try:
            if not force and not self._certificate_needs_renewal(domain):
                return {
                    'success': True,
                    'renewed': False,
                    'message': f'Certificate for {domain} does not need renewal',
                    'domain': domain
                }
            
            args = [
                '--renew',
                '-d', domain,
            ]
            
            if force:
                args.append('--force')
            
            result = self._run_acme_command(args, check=False)
            
            if result.returncode != 0:
                if 'Skip' in result.stdout or 'skipped' in result.stdout:
                    return {
                        'success': True,
                        'renewed': False,
                        'message': f'Certificate for {domain} does not need renewal',
                        'domain': domain
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Failed to renew certificate: {result.stderr}',
                        'domain': domain
                    }
            
            # Reinstall certificate
            install_result = self._install_certificate(domain)
            if not install_result['success']:
                return install_result
            
            return {
                'success': True,
                'renewed': True,
                'domain': domain
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'domain': domain
            }
    
    def remove_certificate(self, domain: str) -> Dict[str, Any]:
        """Remove SSL certificate"""
        try:
            # Remove from acme.sh
            try:
                args = ['--remove', '-d', domain]
                self._run_acme_command(args, check=False)
            except subprocess.CalledProcessError:
                pass  # Ignore errors when removing from acme.sh
            
            # Remove certificate files
            cert_dir = self.certs_dir / domain
            if cert_dir.exists():
                import shutil
                shutil.rmtree(cert_dir)
            
            return {
                'success': True,
                'domain': domain
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'domain': domain
            }
    
    def _certificate_exists(self, domain: str) -> bool:
        """Check if certificate exists"""
        cert_file = self.certs_dir / domain / 'fullchain.pem'
        return cert_file.exists()
    
    def _certificate_needs_renewal(self, domain: str, days_threshold: int = 30) -> bool:
        """Check if certificate needs renewal"""
        cert_file = self.certs_dir / domain / 'fullchain.pem'
        
        if not cert_file.exists():
            return True
        
        try:
            # Check certificate expiry using openssl
            result = subprocess.run([
                'openssl', 'x509', '-in', str(cert_file), '-noout', '-enddate'
            ], capture_output=True, text=True, check=True)
            
            # Parse expiry date
            expiry_line = result.stdout.strip()
            if 'notAfter=' in expiry_line:
                expiry_str = expiry_line.split('notAfter=')[1]
                
                # Parse date (format: MMM DD HH:MM:SS YYYY GMT)
                import datetime
                try:
                    expiry_date = datetime.datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
                    
                    # Calculate days until expiry
                    days_until_expiry = (expiry_date - datetime.datetime.utcnow()).days
                    
                    return days_until_expiry <= days_threshold
                except ValueError:
                    # If we can't parse the date, assume it needs renewal
                    return True
        
        except subprocess.CalledProcessError:
            # If we can't check the certificate, assume it needs renewal
            return True
        
        return False
    
    def list_certificates(self) -> List[Dict[str, Any]]:
        """List all managed certificates"""
        certificates = []
        
        try:
            for cert_dir in self.certs_dir.iterdir():
                if cert_dir.is_dir():
                    domain = cert_dir.name
                    cert_info = {
                        'domain': domain,
                        'path': str(cert_dir),
                        'exists': self._certificate_exists(domain),
                        'needs_renewal': self._certificate_needs_renewal(domain)
                    }
                    
                    # Get certificate details
                    cert_file = cert_dir / 'fullchain.pem'
                    if cert_file.exists():
                        try:
                            result = subprocess.run([
                                'openssl', 'x509', '-in', str(cert_file), '-noout', '-enddate', '-subject'
                            ], capture_output=True, text=True, check=True)
                            
                            for line in result.stdout.split('\n'):
                                if 'notAfter=' in line:
                                    cert_info['expiry'] = line.split('notAfter=')[1].strip()
                                elif 'subject=' in line:
                                    cert_info['subject'] = line.split('subject=')[1].strip()
                        except subprocess.CalledProcessError:
                            pass
                    
                    certificates.append(cert_info)
        
        except Exception:
            pass
        
        return certificates 