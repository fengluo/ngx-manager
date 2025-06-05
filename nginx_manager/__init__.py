"""
Nginx Manager - A modern nginx configuration and SSL certificate management tool

This package provides tools for managing nginx configurations and SSL certificates
in both native and Docker environments.
"""

__version__ = "2.0.0"
__author__ = "Nginx Manager Team"
__email__ = "admin@example.com"

from .core.manager import NginxManager
from .config.settings import Settings

__all__ = [
    "NginxManager",
    "Settings",
] 