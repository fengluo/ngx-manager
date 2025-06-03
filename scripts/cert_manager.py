#!/usr/bin/env python3
"""
SSL Certificate Management Script (Python version)
Integrated with acme.sh, supports certificate application, renewal and management
"""

import os
import sys
import yaml
import argparse
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

def setup_logging(logs_dir: str = None):
    """Setup logging configuration"""
    if logs_dir is None:
        logs_dir = os.environ.get('LOGS_DIR', '/app/logs')
    
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_path / 'cert.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler()
        ]
    )

# Delayed log initialization, only when needed
logger = None

def get_logger():
    """Get logger, delayed initialization"""
    global logger
    if logger is None:
        setup_logging()
        logger = logging.getLogger(__name__)
    return logger

class SSLCertificateManager:
    def __init__(self, config_dir=None, certs_dir=None, logs_dir=None):
        # Use environment variables or provided parameters, fallback to defaults
        self.config_dir = Path(config_dir or os.environ.get('CONFIG_DIR', '/app/config'))
        self.certs_dir = Path(certs_dir or os.environ.get('CERTS_DIR', '/app/certs'))
        self.logs_dir = Path(logs_dir or os.environ.get('LOGS_DIR', '/app/logs'))
        self.acme_home = Path(os.environ.get('ACME_HOME', '/root/.acme.sh'))
        self.acme_bin = self.acme_home / 'acme.sh'
        
        # Ensure directories exist
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging (using actual logs_dir)
        setup_logging(str(self.logs_dir))
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.ssl_config = self.load_ssl_config()
        
    def load_ssl_config(self) -> Dict:
        """Load SSL configuration"""
        ssl_config_file = self.config_dir / 'ssl.yml'
        
        if not ssl_config_file.exists():
            self.logger.error(f"SSL configuration file does not exist: {ssl_config_file}")
            return self.get_default_ssl_config()
            
        try:
            with open(ssl_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            self.logger.info("SSL configuration loaded successfully")
            return config
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error: {e}")
            return self.get_default_ssl_config()
        except Exception as e:
            self.logger.error(f"Failed to load SSL configuration: {e}")
            return self.get_default_ssl_config()
    
    def get_default_ssl_config(self) -> Dict:
        """Get default SSL configuration"""
        return {
            'ssl': {
                'email': 'admin@example.com',
                'ca_server': 'letsencrypt',
                'key_length': 2048,
                'auto_upgrade': True
            },
            'acme': {
                'staging': False,
                'force': False,
                'debug': False
            },
            'advanced': {
                'renewal_check_interval': 24,
                'renewal_days_before_expiry': 30,
                'concurrent_cert_limit': 3,
                'retry_attempts': 3,
                'retry_interval': 300
            }
        }
    
    def get_ca_server_url(self) -> str:
        """Get CA server URL"""
        ca_server = self.ssl_config['ssl']['ca_server']
        staging = self.ssl_config['acme']['staging']
        
        ca_servers = {
            'letsencrypt': {
                'production': 'https://acme-v02.api.letsencrypt.org/directory',
                'staging': 'https://acme-staging-v02.api.letsencrypt.org/directory'
            },
            'zerossl': {
                'production': 'https://acme.zerossl.com/v2/DV90',
                'staging': 'https://acme.zerossl.com/v2/DV90'
            },
            'buypass': {
                'production': 'https://api.buypass.com/acme/directory',
                'staging': 'https://api.test4.buypass.no/acme/directory'
            }
        }
        
        if ca_server not in ca_servers:
            raise ValueError(f"Unsupported CA server: {ca_server}")
            
        return ca_servers[ca_server]['staging' if staging else 'production']
    
    def run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Execute command"""
        try:
            self.logger.debug(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            
            if result.stdout:
                self.logger.debug(f"Command output: {result.stdout}")
            if result.stderr:
                self.logger.warning(f"Command error: {result.stderr}")
                
            return result
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command execution failed: {e}")
            self.logger.error(f"Error output: {e.stderr}")
            raise
    
    def init_acme(self) -> bool:
        """Initialize acme.sh"""
        self.logger.info("Initializing acme.sh...")
        
        if not self.acme_bin.exists():
            self.logger.error("acme.sh not installed")
            return False
            
        try:
            # Set default CA server
            ca_server_url = self.get_ca_server_url()
            self.run_command([str(self.acme_bin), '--set-default-ca', '--server', ca_server_url])
            
            # Check if account registration is needed
            ca_dir = self.acme_home / 'ca'
            if not ca_dir.exists():
                self.logger.info("Registering ACME account...")
                email = self.ssl_config['ssl']['email']
                self.run_command([
                    str(self.acme_bin), '--register-account',
                    '-m', email,
                    '--server', ca_server_url
                ])
                
            self.logger.info("acme.sh initialization completed")
            return True
            
        except Exception as e:
            self.logger.error(f"acme.sh initialization failed: {e}")
            return False
    
    def cert_exists(self, domain: str) -> bool:
        """Check if certificate exists"""
        cert_dir = self.certs_dir / domain
        cert_file = cert_dir / 'fullchain.cer'
        key_file = cert_dir / f'{domain}.key'
        
        return cert_file.exists() and key_file.exists()
    
    def cert_needs_renewal(self, domain: str) -> bool:
        """Check if certificate needs renewal"""
        cert_dir = self.certs_dir / domain
        cert_file = cert_dir / 'fullchain.cer'
        
        if not cert_file.exists():
            return True  # Certificate does not exist, needs to be issued
            
        try:
            # Use openssl to check certificate expiration time
            result = self.run_command([
                'openssl', 'x509', '-in', str(cert_file),
                '-noout', '-enddate'
            ])
            
            # Parse expiration date
            enddate_line = result.stdout.strip()
            enddate_str = enddate_line.split('=')[1]
            
            # Convert to datetime object
            expiry_date = datetime.strptime(enddate_str, '%b %d %H:%M:%S %Y %Z')
            current_date = datetime.now()
            
            # Calculate remaining days
            days_until_expiry = (expiry_date - current_date).days
            renewal_days = self.ssl_config['advanced']['renewal_days_before_expiry']
            
            if days_until_expiry <= renewal_days:
                self.logger.info(f"Certificate {domain} will expire in {days_until_expiry} days, needs renewal")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check certificate expiration time: {e}")
            return True  # Assume needs renewal if error occurs
    
    def issue_cert(self, domain: str) -> bool:
        """Issue certificate for a single domain"""
        self.logger.info(f"Starting certificate issuance for: {domain}")
        
        cert_dir = self.certs_dir / domain
        cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Build acme.sh command
        cmd = [
            str(self.acme_bin),
            '--issue',
            '-d', domain,
            '--webroot', '/var/www/html',
            '--cert-file', str(cert_dir / f'{domain}.cer'),
            '--key-file', str(cert_dir / f'{domain}.key'),
            '--fullchain-file', str(cert_dir / 'fullchain.cer'),
            '--ca-file', str(cert_dir / 'ca.cer')
        ]
        
        # Add optional parameters
        if self.ssl_config['acme']['force']:
            cmd.append('--force')
            
        if self.ssl_config['acme']['debug']:
            cmd.append('--debug')
        
        # Execute certificate issuance (with retries)
        retry_attempts = self.ssl_config['advanced']['retry_attempts']
        retry_interval = self.ssl_config['advanced']['retry_interval']
        
        for attempt in range(1, retry_attempts + 1):
            self.logger.info(f"Certificate issuance attempt {attempt}/{retry_attempts}: {domain}")
            
            try:
                self.run_command(cmd)
                self.logger.info(f"Certificate issuance successful: {domain}")
                
                # Set certificate file permissions
                for key_file in cert_dir.glob('*.key'):
                    key_file.chmod(0o600)
                for cert_file in cert_dir.glob('*.cer'):
                    cert_file.chmod(0o644)
                    
                return True
                
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Certificate issuance failed (attempt {attempt}/{retry_attempts}): {domain}")
                
                if attempt < retry_attempts:
                    self.logger.info(f"Waiting {retry_interval} seconds before retrying...")
                    time.sleep(retry_interval)
                    
        self.logger.error(f"Final certificate issuance failed: {domain}")
        return False
    
    def renew_cert(self, domain: str) -> bool:
        """Renew certificate for a single domain"""
        self.logger.info(f"Starting certificate renewal for: {domain}")
        
        try:
            cmd = [str(self.acme_bin), '--renew', '-d', domain, '--force']
            self.run_command(cmd)
            self.logger.info(f"Certificate renewal successful: {domain}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Certificate renewal failed: {domain}")
            return False
    
    def get_ssl_domains(self) -> List[str]:
        """Get all domains needing SSL from vhosts configuration"""
        vhosts_config = self.config_dir / 'vhosts.yml'
        
        if not vhosts_config.exists():
            self.logger.error(f"Virtual host configuration file does not exist: {vhosts_config}")
            return []
            
        try:
            with open(vhosts_config, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Support two formats
            if isinstance(config, dict) and 'vhosts' in config:
                vhosts = config['vhosts']
            elif isinstance(config, list):
                vhosts = config
            else:
                self.logger.error("Virtual host configuration format error")
                return []
                
            ssl_domains = []
            for vhost in vhosts:
                if vhost.get('ssl', False):
                    domains = vhost.get('domains', [])
                    if domains:
                        ssl_domains.append(domains[0])  # Use first domain as certificate main domain
                        
            return ssl_domains
            
        except Exception as e:
            self.logger.error(f"Failed to read virtual host configuration: {e}")
            return []
    
    def check_and_issue_all_certs(self) -> bool:
        """Check and issue all needed certificates"""
        self.logger.info("Checking and issuing all needed SSL certificates...")
        
        domains = self.get_ssl_domains()
        
        if not domains:
            self.logger.info("No domains found needing SSL certificates")
            return True
            
        success_count = 0
        total_count = len(domains)
        
        for domain in domains:
            if self.cert_exists(domain) and not self.cert_needs_renewal(domain):
                self.logger.info(f"Certificate exists and is valid: {domain}")
                success_count += 1
                continue
                
            if self.issue_cert(domain):
                success_count += 1
                
        self.logger.info(f"Certificate check completed: {success_count}/{total_count} domains")
        
        # Reload nginx
        if success_count > 0:
            self.reload_nginx()
            
        return success_count == total_count
    
    def renew_all_certs(self) -> bool:
        """Renew all certificates"""
        self.logger.info("Renewing all certificates...")
        
        try:
            cmd = [str(self.acme_bin), '--renew-all', '--force']
            self.run_command(cmd)
            self.logger.info("All certificates renewed")
            self.reload_nginx()
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error("Certificate renewal failed")
            return False
    
    def list_certs(self):
        """List all certificates"""
        self.logger.info("Certificate list:")
        
        try:
            # List certificates managed by acme.sh
            result = self.run_command([str(self.acme_bin), '--list'], check=False)
            if result.stdout:
                print(result.stdout)
                
        except Exception as e:
            self.logger.error(f"Failed to list certificates: {e}")
            
        # List local certificate files
        self.logger.info("Local certificate files:")
        for cert_file in sorted(self.certs_dir.rglob('*.cer')):
            print(f"  {cert_file}")
        for key_file in sorted(self.certs_dir.rglob('*.key')):
            print(f"  {key_file}")
    
    def update_email(self, new_email: str) -> bool:
        """Update email configuration"""
        self.logger.info(f"Updating ACME email configuration: {new_email}")
        
        try:
            cmd = [str(self.acme_bin), '--update-account', '--accountemail', new_email]
            self.run_command(cmd)
            self.logger.info("Email updated successfully")
            
            # Update configuration file
            self.ssl_config['ssl']['email'] = new_email
            ssl_config_file = self.config_dir / 'ssl.yml'
            
            with open(ssl_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.ssl_config, f, default_flow_style=False, allow_unicode=True)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update email: {e}")
            return False
    
    def reload_nginx(self):
        """Reload nginx configuration"""
        try:
            self.logger.info("Reloading nginx configuration...")
            self.run_command(['nginx', '-s', 'reload'])
            self.logger.info("nginx configuration reloaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to reload nginx: {e}")

def main():
    parser = argparse.ArgumentParser(description='SSL Certificate Management Script')
    parser.add_argument('--init', action='store_true', help='Initialize acme.sh')
    parser.add_argument('--check-all', action='store_true', help='Check and issue all needed certificates')
    parser.add_argument('--renew-all', action='store_true', help='Renew all certificates')
    parser.add_argument('--domain', type=str, help='Issue certificate for specified domain')
    parser.add_argument('--renew', type=str, help='Renew specified domain certificate')
    parser.add_argument('--list', action='store_true', help='List all certificates')
    parser.add_argument('--update-email', type=str, help='Update ACME email configuration')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    manager = SSLCertificateManager()
    
    try:
        if args.init:
            success = manager.init_acme()
        elif args.check_all:
            manager.init_acme()
            success = manager.check_and_issue_all_certs()
        elif args.renew_all:
            success = manager.renew_all_certs()
        elif args.domain:
            manager.init_acme()
            success = manager.issue_cert(args.domain)
        elif args.renew:
            success = manager.renew_cert(args.renew)
        elif args.list:
            manager.list_certs()
            success = True
        elif args.update_email:
            success = manager.update_email(args.update_email)
        else:
            parser.print_help()
            success = True
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        manager.logger.info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        manager.logger.error(f"Operation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 