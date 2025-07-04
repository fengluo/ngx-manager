"""
Command-line interface for nginx-manager
"""

import sys
import click
from pathlib import Path
from typing import Optional

from .config.settings import settings, Settings
from .core.manager import NginxManager
from .utils.environment import EnvironmentManager


@click.group()
@click.option("--config-dir", "-c", 
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help="Configuration directory path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, config_dir: Optional[str], verbose: bool):
    """Nginx Manager - Simplified nginx configuration management"""
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    # Initialize settings with custom config directory if provided
    if config_dir:
        ctx.obj['settings'] = Settings(config_dir=config_dir)
    else:
        ctx.obj['settings'] = settings
    
    # Initialize managers
    ctx.obj['manager'] = NginxManager()
    ctx.obj['env_manager'] = EnvironmentManager()


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
def status(ctx, verbose: bool):
    """Show current status and configuration"""
    manager = ctx.obj["manager"]
    env_manager = ctx.obj["env_manager"]
    
    click.echo("=== Nginx Manager Status ===")
    click.echo(f"Config directory: {settings.config_dir}")
    click.echo(f"Nginx config directory: {settings.nginx_config_dir}")
    click.echo(f"SSL certificates directory: {settings.ssl_certs_dir}")
    click.echo(f"Logs directory: {settings.logs_dir}")
    click.echo()
    
    # Check environment status
    click.echo("=== Environment Status ===")
    env_status = env_manager.check_environment()
    for service, status in env_status.items():
        if isinstance(status, dict):
            available = status.get("available", False)
        else:
            available = bool(status)
        status_icon = "✓" if available else "✗"
        click.echo(f"{status_icon} {service}")
    
    # Check nginx status
    click.echo()
    click.echo("=== Nginx Status ===")
    try:
        nginx_status = manager.get_nginx_status()
        click.echo(f"Status: {nginx_status['status']}")
        if nginx_status.get("config_test"):
            click.echo(f"Config test: {'✓ Pass' if nginx_status['config_test'] else '✗ Fail'}")
                
            # Show verbose information if requested
            if verbose:
                if nginx_status.get("version"):
                    click.echo(f"Version: {nginx_status['version']}")
                if nginx_status.get("pid"):
                    click.echo(f"PID: {nginx_status['pid']}")
    except Exception as e:
        click.echo(f"✗ Error getting nginx status: {e}")
        sys.exit(1)


@cli.command(name='init')
@click.option("--email", "-e", help="Email address for SSL certificates")
@click.option("--ca-server", default="letsencrypt", 
              type=click.Choice(['letsencrypt', 'zerossl', 'buypass']),
              help="SSL certificate authority (default: letsencrypt)")
@click.option("--staging", is_flag=True, help="Use staging environment for SSL certificates")
@click.option("--certs-dir", help="SSL certificates directory path")
@click.option("--logs-dir", help="Logs directory path")
@click.option("--www-dir", help="Web root directory path")
@click.option("--force", is_flag=True, help="Force overwrite existing config file")
@click.pass_context
def init(ctx, email: Optional[str], ca_server: str, staging: bool, 
         certs_dir: Optional[str], logs_dir: Optional[str], www_dir: Optional[str], force: bool):
    """Initialize configuration files"""
    
    config_dir = Path(ctx.obj['settings'].config_dir)
    config_file = config_dir / "config.yml"
    vhosts_file = config_dir / "vhosts.yml"
    
    # Check if config files already exist
    if config_file.exists() and not force:
        click.echo(f"✗ Configuration file already exists: {config_file}")
        click.echo("  Use --force to overwrite existing configuration")
        sys.exit(1)
    
    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Get email address if not provided
    if not email:
        email = click.prompt("Enter email address for SSL certificates", 
                           default="admin@example.com")
    
    # Generate configuration files using templates
    try:
        from .templates.generator import ConfigGenerator
        generator = ConfigGenerator()
        
        # Generate config.yml content using template
        config_content = generator.generate_config_file(
            ssl_certs_dir=ctx.obj['settings'].ssl_certs_dir,
            ssl_email=email,
            ssl_ca_server=ca_server,
            ssl_staging=staging,
            nginx_logs_level="info",
            nginx_log_dir=ctx.obj['settings'].nginx_log_dir,
            advanced_www_dir=ctx.obj['settings'].nginx_www_dir,
        )
        
        # Generate vhosts.yml content using template
        vhosts_content = generator.generate_vhosts_file(
            default_ssl=not staging,  # If staging, default SSL to false for examples
            www_dir=ctx.obj['settings'].nginx_www_dir,
        )
        
    except Exception as e:
        click.echo(f"✗ Failed to generate configuration templates: {e}")
        sys.exit(1)

    try:
        # Write config.yml
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        click.echo(f"✓ Generated configuration file: {config_file}")
        
        # Write vhosts.yml if it doesn't exist
        if not vhosts_file.exists():
            with open(vhosts_file, 'w', encoding='utf-8') as f:
                f.write(vhosts_content)
            click.echo(f"✓ Generated vhosts template: {vhosts_file}")
        else:
            click.echo(f"• Vhosts file already exists: {vhosts_file}")
        
        # Create required directories
        for dir_path in [ctx.obj['settings'].ssl_certs_dir, ctx.obj['settings'].nginx_log_dir]:
            dir_obj = Path(dir_path)
            if not dir_obj.exists():
                try:
                    dir_obj.mkdir(parents=True, exist_ok=True)
                    click.echo(f"✓ Created directory: {dir_path}")
                except PermissionError:
                    click.echo(f"⚠ Cannot create directory (permission denied): {dir_path}")
                except Exception as e:
                    click.echo(f"⚠ Failed to create directory {dir_path}: {e}")
        
        click.echo()
        click.echo("=== Initialization Complete ===")
        click.echo(f"Configuration directory: {config_dir}")
        click.echo(f"Email for SSL certificates: {email}")
        click.echo(f"CA Server: {ca_server}")
        click.echo(f"Staging mode: {'Enabled' if staging else 'Disabled'}")
        click.echo()
        click.echo("Next steps:")
        click.echo("1. Edit vhosts.yml to configure your domains")
        click.echo("2. Run 'nginx-manager generate' to create nginx configurations")
        click.echo("3. Run 'nginx-manager status' to check system status")
        
    except Exception as e:
        click.echo(f"✗ Failed to initialize configuration: {e}")
        sys.exit(1)


@cli.command(name='list')
@click.pass_context
def list_sites(ctx):
    """List all configured sites"""
    manager = ctx.obj["manager"]
    
    sites = manager.list_sites()
    
    if not sites:
        click.echo("No sites configured.")
        return
    
    click.echo("=== Configured Sites ===")
    for site in sites:
        ssl_status = "✓ SSL" if site.get('ssl') else "✗ No SSL"
        backend = site.get('backend', 'Static')
        click.echo(f"• {site['domain']} - {ssl_status} - Backend: {backend}")
        if ctx.obj.get('verbose'):
            click.echo(f"  Config: {site['config_file']}")


@cli.command()
@click.argument("domain")
@click.option("--backend", "-b", help="Backend server URL (for proxy mode)")
@click.option("--no-ssl", is_flag=True, help="Disable SSL certificate")
@click.option("--force", is_flag=True, help="Force overwrite existing configuration")
@click.pass_context
def add(ctx, domain: str, backend: Optional[str], no_ssl: bool, force: bool):
    """Add a new site configuration"""
    manager = ctx.obj["manager"]
    
    ssl = not no_ssl
    
    click.echo(f"Adding site: {domain}")
    if backend:
        click.echo(f"Backend: {backend}")
    if ssl:
        click.echo("SSL: Enabled")
    else:
        click.echo("SSL: Disabled")
    
    result = manager.add_site(domain=domain, backend=backend, ssl=ssl, force=force)
        
    if result['success']:
        click.echo("✓ Site added successfully")
        if ssl:
            click.echo("✓ SSL certificate obtained")
        click.echo("✓ Nginx configuration reloaded")
    else:
        click.echo(f"✗ Failed to add site: {result['error']}")
        sys.exit(1)


@cli.command()
@click.argument("domain")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
@click.pass_context
def remove(ctx, domain: str, force: bool):
    """Remove a site configuration"""
    manager = ctx.obj["manager"]
    
    if not force:
        if not click.confirm(f"Are you sure you want to remove site '{domain}'?"):
            click.echo("Operation cancelled.")
            return
    
    click.echo(f"Removing site: {domain}")
    result = manager.remove_site(domain)
        
    if result['success']:
        click.echo("✓ Site removed successfully")
        click.echo("✓ SSL certificate removed")
        click.echo("✓ Nginx configuration reloaded")
    else:
        click.echo(f"✗ Failed to remove site: {result['error']}")
        sys.exit(1)


@cli.command()
@click.option("--domain", "-d", help="Renew certificate for specific domain")
@click.option("--force", is_flag=True, help="Force renewal even if not expired")
@click.pass_context
def renew(ctx, domain: Optional[str], force: bool):
    """Renew SSL certificates"""
    manager = ctx.obj["manager"]
    
    if domain:
        click.echo(f"Renewing certificate for: {domain}")
    else:
        click.echo("Renewing all certificates...")
    
        result = manager.renew_certificates(domain=domain, force=force)
        
        if result['success']:
            renewed = result.get('renewed', [])
            if renewed:
                click.echo(f"✓ Renewed certificates for: {', '.join(renewed)}")
                if result.get('nginx_reloaded'):
                    click.echo("✓ Nginx configuration reloaded")
            else:
                click.echo("✓ No certificates needed renewal")
        
        if result.get('errors'):
            click.echo("⚠ Some certificates had errors:")
            for error in result['errors']:
                click.echo(f"  • {error}")
        else:
            click.echo(f"✗ Failed to renew certificates: {result['error']}")
            sys.exit(1)


@cli.command()
@click.pass_context
def reload(ctx):
    """Reload nginx configuration"""
    manager = ctx.obj["manager"]
    
    click.echo("Reloading nginx configuration...")
    result = manager.reload_nginx()
    
    if result['success']:
        click.echo("✓ Nginx configuration reloaded successfully")
    else:
        click.echo(f"✗ Failed to reload nginx: {result['error']}")
        sys.exit(1)
            

@cli.command()
@click.pass_context
def test(ctx):
    """Test nginx configuration"""
    manager = ctx.obj["manager"]
    
    click.echo("Testing nginx configuration...")
    status = manager.get_nginx_status()
    
    if status.get('config_test'):
        click.echo("✓ Nginx configuration is valid")
    else:
        click.echo("✗ Nginx configuration has errors")
        sys.exit(1)


@cli.command()
@click.option("--no-ssl", is_flag=True, help="Skip SSL certificate generation")
@click.option("--auto-confirm", is_flag=True, help="Auto-confirm prompts (non-interactive mode)")
@click.pass_context
def generate(ctx, no_ssl: bool, auto_confirm: bool):
    """Generate nginx configuration from vhosts.yml"""
    manager = ctx.obj["manager"]
    
    try:
        # Import the configuration generator functionality
        from .templates.generator import ConfigGenerator
        generator = ConfigGenerator()
        
        # Load vhosts configuration
        vhosts_file = settings.config_dir / "vhosts.yml"
        if not vhosts_file.exists():
            click.echo(f"✗ Configuration file not found: {vhosts_file}")
            sys.exit(1)
        
        import yaml
        with open(vhosts_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Handle both formats (with and without 'vhosts' key)
        vhosts = config.get('vhosts', config) if isinstance(config, dict) and 'vhosts' in config else config
        
        if not isinstance(vhosts, list):
            click.echo("✗ Invalid vhosts configuration format")
            sys.exit(1)
        
        click.echo("Analyzing vhost configurations...")
        
        # First pass: collect all SSL domains that need certificates
        ssl_domains = []
        vhost_configs = []
        
        for vhost in vhosts:
            if not isinstance(vhost, dict) or 'name' not in vhost:
                click.echo(f"⚠ Skipping invalid vhost configuration: {vhost}")
                continue
            
            name = vhost['name']
            domains = vhost.get('domains', [])
            ssl = vhost.get('ssl', False)
            
            # Simple proxy configuration
            if vhost.get('type') == 'proxy' and vhost.get('upstream'):
                backend = vhost['upstream']
            else:
                backend = None
            
            if domains:
                primary_domain = domains[0]
                vhost_configs.append({
                    'name': name,
                    'domain': primary_domain,
                    'backend': backend,
                    'ssl': ssl
                })
                
                # Collect SSL domains for certificate generation
                if ssl:
                    ssl_domains.append(primary_domain)
        
        # Step 1: Generate SSL certificates first (if needed and not skipped)
        if ssl_domains and not no_ssl:
            click.echo("Obtaining SSL certificates...")
            ssl_success = 0
            ssl_errors = []
            
            for domain in ssl_domains:
                click.echo(f"  Obtaining certificate for {domain}...")
                ssl_result = manager.ssl_manager.obtain_certificate(domain)
                if ssl_result['success']:
                    click.echo(f"  ✓ Certificate obtained for {domain}")
                    ssl_success += 1
                else:
                    error_msg = f"{domain}: {ssl_result['error']}"
                    click.echo(f"  ✗ Failed to obtain certificate for {domain}: {ssl_result['error']}")
                    ssl_errors.append(error_msg)
            
            if ssl_success > 0:
                click.echo(f"✓ Obtained {ssl_success} SSL certificates")
            
            if ssl_errors:
                click.echo("⚠ Some SSL certificates failed:")
                for error in ssl_errors:
                    click.echo(f"  • {error}")
                
                # Check if running in interactive mode
                if not auto_confirm and sys.stdin.isatty():
                    # Interactive mode - ask user
                    if not click.confirm("Continue generating configurations without SSL certificates?"):
                        click.echo("Operation cancelled.")
                        sys.exit(1)
            else:
                # Non-interactive mode or auto-confirm - auto-continue with warning
                click.echo("⚠ Continuing without SSL certificates (non-interactive mode)")
                
            # Disable SSL for failed domains
            failed_domains = [error.split(':')[0] for error in ssl_errors]
            for config in vhost_configs:
                if config['domain'] in failed_domains:
                    config['ssl'] = False
                    click.echo(f"  Disabled SSL for {config['domain']}")
        
        elif ssl_domains and no_ssl:
            click.echo(f"⚠ {len(ssl_domains)} domains require SSL certificates but --no-ssl was specified")
            click.echo("  SSL will be disabled for these domains")
            # Disable SSL for all configs when --no-ssl is specified
            for config in vhost_configs:
                if config['ssl']:
                    config['ssl'] = False
        
        # Step 2: Generate nginx configurations with certificates ready
        click.echo("Generating nginx configurations...")
        generated = 0
        
        for config in vhost_configs:
            try:
                config_content = generator.generate_site_config(
                    domain=config['domain'],
                    backend=config['backend'],
                    ssl=config['ssl']
                )
                
                # Write configuration file
                config_file = settings.nginx_config_dir / f"{config['name']}.conf"
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(config_content)
        
                click.echo(f"✓ Generated: {config_file}")
                generated += 1
                
            except Exception as e:
                click.echo(f"✗ Failed to generate config for {config['name']}: {e}")
        
        click.echo(f"✓ Generated {generated} configuration files")
        
        # Test configuration
        click.echo("Testing generated configurations...")
        if manager._test_nginx_config():
            click.echo("✓ All configurations are valid")
        else:
            click.echo("✗ Some configurations have errors")
            sys.exit(1)
            
        # Setup automatic certificate renewal (if SSL certificates were generated)
        if ssl_domains and not no_ssl:
            click.echo("Setting up automatic certificate renewal...")
            renewal_result = manager.setup_auto_renewal('daily')
            if renewal_result['success']:
                click.echo("✓ Automatic certificate renewal enabled (daily at 2:00 AM)")
            else:
                click.echo(f"⚠ Failed to setup auto-renewal: {renewal_result['error']}")
                click.echo("  You can set it up manually using: nginx_manager.py auto-renew --enable")
            
    except Exception as e:
        click.echo(f"✗ Failed to generate configurations: {e}")
        sys.exit(1)

def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main() 