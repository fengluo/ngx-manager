#!/usr/bin/env python3
"""
Nginx Configuration Generator
Reads vhosts.yml configuration file and uses Jinja2 templates to generate nginx virtual host configurations
"""

import os
import sys
import yaml
import argparse
import logging
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/config-generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NginxConfigGenerator:
    def __init__(self, config_dir='/app/config', template_dir='/app/templates', output_dir='/etc/nginx/conf.d'):
        self.config_dir = Path(config_dir)
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
    def load_vhosts_config(self):
        """Load virtual host configuration"""
        vhosts_file = self.config_dir / 'vhosts.yml'
        
        if not vhosts_file.exists():
            logger.error(f"Configuration file does not exist: {vhosts_file}")
            return []
            
        try:
            with open(vhosts_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Support two formats: with vhosts key and direct array
            if isinstance(config, dict) and 'vhosts' in config:
                vhosts = config['vhosts']
            elif isinstance(config, list):
                vhosts = config
            else:
                logger.error("Configuration file format error, should be an array or object with vhosts key")
                return []
                
            logger.info(f"Successfully loaded {len(vhosts)} virtual host configurations")
            return vhosts
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}")
            return []
    
    def validate_vhost(self, vhost):
        """Validate virtual host configuration"""
        required_fields = ['name', 'domains']
        
        for field in required_fields:
            if field not in vhost:
                logger.error(f"Virtual host configuration missing required field: {field}")
                return False
                
        if not isinstance(vhost['domains'], list) or not vhost['domains']:
            logger.error(f"Virtual host {vhost['name']} domains field must be a non-empty array")
            return False
            
        # Validate simple mode configuration
        if 'type' in vhost:
            if vhost['type'] == 'proxy' and 'upstream' not in vhost:
                logger.error(f"Proxy type virtual host {vhost['name']} missing upstream configuration")
                return False
            elif vhost['type'] == 'static' and 'root' not in vhost:
                logger.error(f"Static file type virtual host {vhost['name']} missing root configuration")
                return False
                
        # Validate locations configuration
        if 'locations' in vhost:
            for i, location in enumerate(vhost['locations']):
                if 'path' not in location or 'type' not in location:
                    logger.error(f"Virtual host {vhost['name']} location[{i}] missing path or type field")
                    return False
                    
                if location['type'] == 'proxy' and 'upstream' not in location:
                    logger.error(f"Virtual host {vhost['name']} location[{i}] proxy configuration missing upstream")
                    return False
                elif location['type'] == 'static' and 'root' not in location:
                    logger.error(f"Virtual host {vhost['name']} location[{i}] static configuration missing root")
                    return False
                    
        return True
    
    def generate_vhost_config(self, vhost):
        """Generate configuration for a single virtual host"""
        if not self.validate_vhost(vhost):
            return None
            
        try:
            template = self.jinja_env.get_template('vhost.conf.j2')
            
            # Prepare template variables
            template_vars = {
                'vhost': vhost,
                'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Render configuration
            config_content = template.render(**template_vars)
            
            # Write configuration file
            config_file = self.output_dir / f"{vhost['name']}.conf"
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
                
            logger.info(f"Generated virtual host configuration: {config_file}")
            return config_file
            
        except Exception as e:
            logger.error(f"Failed to generate virtual host {vhost['name']} configuration: {e}")
            return None
    
    def clean_old_configs(self, current_vhosts):
        """Clean up unused configuration files"""
        current_names = {vhost['name'] for vhost in current_vhosts}
        
        for config_file in self.output_dir.glob('*.conf'):
            # Skip default configuration files
            if config_file.name in ['default.conf', 'ssl.conf']:
                continue
                
            vhost_name = config_file.stem
            if vhost_name not in current_names:
                try:
                    config_file.unlink()
                    logger.info(f"Deleted old configuration file: {config_file}")
                except Exception as e:
                    logger.error(f"Failed to delete configuration file {config_file}: {e}")
    
    def generate_all_configs(self, clean_old=True):
        """Generate all virtual host configurations"""
        vhosts = self.load_vhosts_config()
        if not vhosts:
            logger.warning("No virtual host configurations found")
            return False
            
        success_count = 0
        
        for vhost in vhosts:
            if self.generate_vhost_config(vhost):
                success_count += 1
                
        if clean_old:
            self.clean_old_configs(vhosts)
            
        logger.info(f"Configuration generation completed: {success_count}/{len(vhosts)} virtual hosts")
        return success_count == len(vhosts)
    
    def generate_single_config(self, vhost_name):
        """Generate single virtual host configuration"""
        vhosts = self.load_vhosts_config()
        
        for vhost in vhosts:
            if vhost['name'] == vhost_name:
                result = self.generate_vhost_config(vhost)
                return result is not None
                
        logger.error(f"Virtual host not found: {vhost_name}")
        return False

def reload_nginx():
    """Reload nginx configuration"""
    try:
        import subprocess
        result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Nginx configuration syntax check failed: {result.stderr}")
            return False
            
        result = subprocess.run(['nginx', '-s', 'reload'], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Nginx configuration reloaded successfully")
            return True
        else:
            logger.error(f"Nginx reload failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to reload Nginx: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Nginx Configuration Generator')
    parser.add_argument('--all', action='store_true', help='Generate all virtual host configurations')
    parser.add_argument('--vhost', type=str, help='Generate specified virtual host configuration')
    parser.add_argument('--no-reload', action='store_true', help='Do not reload nginx')
    parser.add_argument('--no-clean', action='store_true', help='Do not clean old configuration files')
    
    args = parser.parse_args()
    
    generator = NginxConfigGenerator()
    success = False
    
    if args.vhost:
        success = generator.generate_single_config(args.vhost)
    else:
        success = generator.generate_all_configs(clean_old=not args.no_clean)
    
    if success and not args.no_reload:
        reload_nginx()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 