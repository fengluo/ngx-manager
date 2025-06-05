"""
Nginx configuration template generator
"""

from pathlib import Path
from typing import Optional, Dict, Any
from jinja2 import Template, Environment, FileSystemLoader, TemplateNotFound
from ..config.settings import settings


class ConfigGenerator:
    """Generate nginx configuration files from templates"""
    
    def __init__(self):
        """Initialize configuration generator"""
        self.template_dir = Path(__file__).parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader([
                str(self.template_dir),
                str(Path(__file__).parent.parent.parent.parent / "templates")
            ]),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate_site_config(self, domain: str, backend: Optional[str] = None, 
                           ssl: bool = True, template_name: str = None) -> str:
        """Generate nginx configuration for a site"""
        
        # Determine template name based on configuration type
        if template_name is None:
            template_name = self._get_default_template_name(ssl, bool(backend))
        
        # Try to load template
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound:
            # Fall back to built-in template name
            fallback_template = self._get_default_template_name(ssl, bool(backend))
            try:
                template = self.env.get_template(fallback_template)
            except TemplateNotFound:
                raise FileNotFoundError(f"Template not found: {template_name} or {fallback_template}")
        
        # Template variables
        context = {
            'domain': domain,
            'backend': backend or 'http://localhost:8080',
            'ssl': ssl,
            'ssl_cert_path': settings.ssl_certs_dir / domain / 'fullchain.pem',
            'ssl_key_path': settings.ssl_certs_dir / domain / 'privkey.pem',
            'access_log': settings.logs_dir / f'{domain}.access.log',
            'error_log': settings.logs_dir / f'{domain}.error.log',
        }
        
        return template.render(**context)
    
    def _get_default_template_name(self, ssl: bool, is_proxy: bool) -> str:
        """Get default template name based on configuration type"""
        if ssl and is_proxy:
            return "proxy_ssl.conf.j2"
        elif ssl and not is_proxy:
            return "static_ssl.conf.j2"
        elif not ssl and is_proxy:
            return "proxy_http.conf.j2"
        else:
            return "static_http.conf.j2"
    
    def list_available_templates(self) -> list:
        """List all available template files"""
        templates = []
        for template_file in self.template_dir.glob("*.j2"):
            templates.append(template_file.name)
        return sorted(templates)
    
    def get_template_content(self, template_name: str) -> str:
        """Get the content of a template file for inspection"""
        try:
            template = self.env.get_template(template_name)
            return template.source
        except TemplateNotFound:
            raise FileNotFoundError(f"Template not found: {template_name}") 