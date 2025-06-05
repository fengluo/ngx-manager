"""
Command line interface for ngx-manager
"""

import os
import sys
import click
from pathlib import Path
from typing import Optional

from .config.settings import settings
from .core.manager import NginxManager
from .utils.environment import EnvironmentManager


@click.group()
@click.option('--config-dir', '-c', 
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help='Configuration directory path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, config_dir: Optional[str], verbose: bool):
    """Nginx Manager - Modern nginx configuration and SSL certificate management tool"""
    ctx.ensure_object(dict)
    
    # Set up configuration
    if config_dir:
        os.environ['NGINX_MANAGER_CONFIG_DIR'] = config_dir
    
    # Set up verbose mode
    if verbose:
        os.environ['NGINX_MANAGER_LOG_LEVEL'] = 'DEBUG'
    
    # Initialize manager
    ctx.obj['manager'] = NginxManager()
    ctx.obj['env_manager'] = EnvironmentManager()


@cli.command()
@click.pass_context
def status(ctx):
    """Show current status and configuration"""
    manager = ctx.obj['manager']
    env_manager = ctx.obj['env_manager']
    
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
        status_icon = "✓" if status else "✗"
        click.echo(f"{status_icon} {service}")
    
    # Check nginx status
    click.echo()
    click.echo("=== Nginx Status ===")
    nginx_status = manager.get_nginx_status()
    click.echo(f"Status: {nginx_status['status']}")
    if nginx_status.get('config_test'):
        click.echo(f"Config test: {'✓ Pass' if nginx_status['config_test'] else '✗ Fail'}")


@cli.command()
@click.option('--domain', '-d', required=True, help='Domain name')
@click.option('--backend', '-b', help='Backend server (e.g., http://localhost:3000)')
@click.option('--ssl/--no-ssl', default=True, help='Enable SSL certificate')
@click.option('--force', '-f', is_flag=True, help='Force overwrite existing configuration')
@click.pass_context
def add(ctx, domain: str, backend: Optional[str], ssl: bool, force: bool):
    """Add a new site configuration"""
    manager = ctx.obj['manager']
    
    try:
        result = manager.add_site(
            domain=domain,
            backend=backend,
            ssl=ssl,
            force=force
        )
        
        if result['success']:
            click.echo(f"✓ Successfully added site: {domain}")
            if ssl:
                click.echo(f"✓ SSL certificate will be automatically managed")
        else:
            click.echo(f"✗ Failed to add site: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--domain', '-d', required=True, help='Domain name')
@click.option('--force', '-f', is_flag=True, help='Force removal without confirmation')
@click.pass_context
def remove(ctx, domain: str, force: bool):
    """Remove a site configuration"""
    manager = ctx.obj['manager']
    
    if not force:
        if not click.confirm(f"Are you sure you want to remove site '{domain}'?"):
            click.echo("Operation cancelled.")
            return
    
    try:
        result = manager.remove_site(domain=domain)
        
        if result['success']:
            click.echo(f"✓ Successfully removed site: {domain}")
        else:
            click.echo(f"✗ Failed to remove site: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Error: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def list(ctx):
    """List all configured sites"""
    manager = ctx.obj['manager']
    
    try:
        sites = manager.list_sites()
        
        if not sites:
            click.echo("No sites configured.")
            return
        
        click.echo("=== Configured Sites ===")
        for site in sites:
            ssl_icon = "🔒" if site.get('ssl') else "🔓"
            status_icon = "✓" if site.get('active') else "✗"
            click.echo(f"{status_icon} {ssl_icon} {site['domain']} -> {site.get('backend', 'N/A')}")
            
    except Exception as e:
        click.echo(f"✗ Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--domain', '-d', help='Specific domain to renew certificate for')
@click.option('--force', '-f', is_flag=True, help='Force renewal even if not needed')
@click.pass_context
def renew(ctx, domain: Optional[str], force: bool):
    """Renew SSL certificates"""
    manager = ctx.obj['manager']
    
    try:
        result = manager.renew_certificates(domain=domain, force=force)
        
        if result['success']:
            renewed = result.get('renewed', [])
            if renewed:
                click.echo(f"✓ Successfully renewed certificates for: {', '.join(renewed)}")
            else:
                click.echo("✓ All certificates are up to date.")
        else:
            click.echo(f"✗ Failed to renew certificates: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Error: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def reload(ctx):
    """Reload nginx configuration"""
    manager = ctx.obj['manager']
    
    try:
        result = manager.reload_nginx()
        
        if result['success']:
            click.echo("✓ Nginx configuration reloaded successfully")
        else:
            click.echo(f"✗ Failed to reload nginx: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--install-deps', is_flag=True, help='Install system dependencies')
@click.option('--setup-nginx', is_flag=True, help='Setup nginx configuration')
@click.option('--setup-ssl', is_flag=True, help='Setup SSL/ACME tools')
@click.pass_context
def setup(ctx, install_deps: bool, setup_nginx: bool, setup_ssl: bool):
    """Setup ngx-manager for native environment"""
    env_manager = ctx.obj['env_manager']
    
    if not any([install_deps, setup_nginx, setup_ssl]):
        # Run all setup steps if none specified
        install_deps = setup_nginx = setup_ssl = True
    
    try:
        if install_deps:
            click.echo("Installing system dependencies...")
            result = env_manager.install_dependencies()
            if result['success']:
                click.echo("✓ Dependencies installed successfully")
            else:
                click.echo(f"✗ Failed to install dependencies: {result['error']}")
                sys.exit(1)
        
        if setup_nginx:
            click.echo("Setting up nginx configuration...")
            result = env_manager.setup_nginx()
            if result['success']:
                click.echo("✓ Nginx setup completed")
            else:
                click.echo(f"✗ Failed to setup nginx: {result['error']}")
                sys.exit(1)
        
        if setup_ssl:
            click.echo("Setting up SSL/ACME tools...")
            result = env_manager.setup_ssl()
            if result['success']:
                click.echo("✓ SSL tools setup completed")
            else:
                click.echo(f"✗ Failed to setup SSL tools: {result['error']}")
                sys.exit(1)
        
        click.echo("✓ Setup completed successfully!")
        
    except Exception as e:
        click.echo(f"✗ Setup failed: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main() 