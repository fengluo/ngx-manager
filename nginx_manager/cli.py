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
@click.pass_context
def generate(ctx):
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
        
        click.echo("Generating nginx configurations...")
        
        generated = 0
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
            
            # Generate configuration for primary domain
            if domains:
                primary_domain = domains[0]
                try:
                    config_content = generator.generate_site_config(
                        domain=primary_domain,
                        backend=backend,
                        ssl=ssl
                    )
                    
                    # Write configuration file
                    config_file = settings.nginx_config_dir / f"{name}.conf"
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(config_content)
        
                    click.echo(f"✓ Generated: {config_file}")
                    generated += 1
                except Exception as e:
                    click.echo(f"✗ Failed to generate config for {name}: {e}")
        
        click.echo(f"✓ Generated {generated} configuration files")
        
        # Test configuration
        click.echo("Testing generated configurations...")
        if manager._test_nginx_config():
            click.echo("✓ All configurations are valid")
        else:
            click.echo("✗ Some configurations have errors")
            sys.exit(1)
            
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