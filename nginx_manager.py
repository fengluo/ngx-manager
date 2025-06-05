#!/usr/bin/env python3
"""
Ngx Manager - Development Entry Point

This module serves as a standalone entry point for ngx-manager during development.
It allows running the application without requiring pip installation by dynamically
adding the project root to the Python path.

Features:
    - Direct execution support for development workflow
    - Automatic path resolution for uninstalled packages
    - Comprehensive error handling with helpful diagnostics
    - Compatible with both native and Docker deployment modes

Usage:
    python nginx_manager.py [command] [options]

Examples:
    python nginx_manager.py status
    python nginx_manager.py add example.com --ssl
    python nginx_manager.py list
"""

import sys
import os
from pathlib import Path

# Ensure the project root is in Python path for development execution
# This allows importing nginx_manager modules without package installation
current_path = Path(__file__).parent
if current_path.exists():
    sys.path.insert(0, str(current_path))

try:
    # Import the main CLI function from the nginx_manager package
    from nginx_manager.cli import main
    
    if __name__ == '__main__':
        # Execute the main CLI when script is run directly
        main()
        
except ImportError as e:
    # Provide detailed error information and resolution steps
    print(f"Error: Failed to import ngx-manager module: {e}")
    print()
    print("Possible causes and solutions:")
    print("  1. Package not installed:")
    print("     → Run: pip install -e .")
    print()
    print("  2. Development environment not configured:")
    print("     → Create virtual environment: python -m venv venv")
    print("     → Activate: source venv/bin/activate (Linux/macOS) or venv\\Scripts\\activate (Windows)")
    print("     → Install dependencies: pip install -e .[dev]")
    print()
    print("  3. Missing from PyPI installation:")
    print("     → Run: pip install ngx-manager")
    print()
    print("  4. Python path issues:")
    print("     → Ensure you're in the project root directory")
    print("     → Check file permissions and directory structure")
    
    sys.exit(1) 