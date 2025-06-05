#!/usr/bin/env python3
"""
Nginx Manager - A modern nginx configuration and SSL certificate management tool
"""

from setuptools import setup, find_packages
import os

def read_requirements():
    """Read requirements from requirements.txt"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def read_long_description():
    """Read long description from README"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "A modern nginx configuration and SSL certificate management tool"

setup(
    name="ngx-manager",
    version="2.0.0",
    description="A modern nginx configuration and SSL certificate management tool",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    author="Nginx Manager Team",
    author_email="admin@example.com",
    url="https://github.com/yourusername/ngx-manager",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "nginx_manager": [
            "templates/*.conf",
            "templates/*.j2",
            "config/*.yml",
            "config/*.yaml",
        ],
    },
    install_requires=read_requirements(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "ngx-manager=nginx_manager.cli:main",
            "nginx-mgr=nginx_manager.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: System :: Systems Administration",
    ],
    keywords="nginx ssl certificate management acme letsencrypt",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/ngx-manager/issues",
        "Source": "https://github.com/yourusername/ngx-manager",
        "Documentation": "https://github.com/yourusername/ngx-manager/docs",
    },
) 