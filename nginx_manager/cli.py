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
@click.option("--config-dir", "-c", 
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help="Configuration directory path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, config_dir: Optional[str], verbose: bool):
    """Nginx Manager - Modern nginx configuration and SSL certificate management tool"""
    ctx.ensure_object(dict)
    
    # Set up configuration
    if config_dir:
        os.environ["NGINX_MANAGER_CONFIG_DIR"] = config_dir
    
    # Set up verbose mode
    if verbose:
        os.environ["NGINX_MANAGER_LOG_LEVEL"] = "DEBUG"
    
    # Initialize manager
    ctx.obj["manager"] = NginxManager()
    ctx.obj["env_manager"] = EnvironmentManager()


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


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main() 