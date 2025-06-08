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
@click.option("--enable", is_flag=True, help="Enable automatic certificate renewal")
@click.option("--disable", is_flag=True, help="Disable automatic certificate renewal")
@click.option("--status", is_flag=True, help="Show auto-renewal status")
@click.option("--interval", default="daily", type=click.Choice(['daily', 'weekly', 'monthly']), 
              help="Renewal check interval (default: daily)")
@click.pass_context
def auto_renew(ctx, enable: bool, disable: bool, status: bool, interval: str):
    """Manage automatic SSL certificate renewal"""
    manager = ctx.obj["manager"]
    
    if status or (not enable and not disable):
        # Show current status
        cron_status = manager.check_auto_renewal_status()
        if cron_status['enabled']:
            click.echo("✓ Automatic certificate renewal is ENABLED")
            click.echo(f"  Schedule: {cron_status['schedule']}")
            click.echo(f"  Next run: {cron_status.get('next_run', 'Unknown')}")
        else:
            click.echo("✗ Automatic certificate renewal is DISABLED")
        return
    
    if enable and disable:
        click.echo("✗ Cannot enable and disable at the same time")
        sys.exit(1)
    
    if enable:
        result = manager.setup_auto_renewal(interval)
        if result['success']:
            click.echo("✓ Automatic certificate renewal enabled")
            click.echo(f"  Schedule: {result['schedule']}")
            click.echo(f"  Command: {result['command']}")
        else:
            click.echo(f"✗ Failed to enable auto-renewal: {result['error']}")
            sys.exit(1)
    
    elif disable:
        result = manager.disable_auto_renewal()
        if result['success']:
            click.echo("✓ Automatic certificate renewal disabled")
        else:
            click.echo(f"✗ Failed to disable auto-renewal: {result['error']}")
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


@cli.command()
@click.pass_context
def templates(ctx):
    """List available nginx configuration templates"""
    from .templates.generator import ConfigGenerator
    
    generator = ConfigGenerator()
    templates_dir = generator.templates_dir
    
    click.echo("=== Available Templates ===")
    if templates_dir.exists():
        for template_file in templates_dir.glob("*.j2"):
            click.echo(f"• {template_file.name}")
        else:
        click.echo("No custom templates found.")
        click.echo(f"Templates directory: {templates_dir}")


def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main() 