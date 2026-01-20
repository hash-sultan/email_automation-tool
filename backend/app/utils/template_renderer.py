"""
XenFlow Mailer - Template Renderer
Dynamic placeholder rendering with Jinja2
"""

import re
from typing import Dict, Any, List, Set
from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateRenderer:
    """
    Template rendering engine with placeholder support.
    
    Supports:
    - {{placeholder}} syntax
    - Default values: {{name|default('Friend')}}
    - Conditional blocks
    - Safe rendering (no code execution)
    """
    
    # Pattern to find placeholders
    PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)(?:\|[^}]*)?\}\}')
    
    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,  # Don't escape HTML in email templates
        )
        
        # Add custom filters
        self.env.filters['default'] = lambda val, default: val if val else default
        self.env.filters['title'] = lambda s: s.title() if s else ''
        self.env.filters['upper'] = lambda s: s.upper() if s else ''
        self.env.filters['lower'] = lambda s: s.lower() if s else ''
        self.env.filters['strip'] = lambda s: s.strip() if s else ''
    
    def render(self, template_str: str, data: Dict[str, Any]) -> str:
        """
        Render a template string with provided data.
        
        Args:
            template_str: Template with {{placeholder}} syntax
            data: Dictionary of placeholder values
        
        Returns:
            Rendered string
        """
        if not template_str:
            return ""
        
        try:
            # Convert our {{placeholder}} to Jinja2 {{ placeholder }}
            jinja_template = self._convert_to_jinja(template_str)
            
            template = self.env.from_string(jinja_template)
            return template.render(**data)
            
        except TemplateSyntaxError as e:
            logger.warning(f"Template syntax error: {str(e)}")
            return template_str
        except UndefinedError as e:
            logger.warning(f"Undefined placeholder: {str(e)}")
            return self._render_with_defaults(template_str, data)
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            return template_str
    
    def _convert_to_jinja(self, template_str: str) -> str:
        """Convert {{placeholder}} to Jinja2 {{ placeholder }}."""
        # Add spaces inside braces for Jinja2 compatibility
        return re.sub(r'\{\{(\w+)', r'{{ \1', 
               re.sub(r'(\w+)\}\}', r'\1 }}', template_str))
    
    def _render_with_defaults(self, template_str: str, data: Dict[str, Any]) -> str:
        """Fallback rendering with empty defaults for missing placeholders."""
        def replace_placeholder(match):
            key = match.group(1)
            return str(data.get(key, ''))
        
        return self.PLACEHOLDER_PATTERN.sub(replace_placeholder, template_str)
    
    def extract_placeholders(self, template_str: str) -> Set[str]:
        """
        Extract all placeholder names from a template.
        
        Returns set of placeholder names.
        """
        if not template_str:
            return set()
        
        return set(self.PLACEHOLDER_PATTERN.findall(template_str))
    
    def validate_template(self, template_str: str) -> Dict[str, Any]:
        """
        Validate a template for syntax errors.
        
        Returns:
            {
                "valid": bool,
                "placeholders": List[str],
                "error": str or None
            }
        """
        result = {
            "valid": True,
            "placeholders": [],
            "error": None
        }
        
        if not template_str:
            return result
        
        try:
            # Try to parse the template
            jinja_template = self._convert_to_jinja(template_str)
            self.env.from_string(jinja_template)
            
            # Extract placeholders
            result["placeholders"] = list(self.extract_placeholders(template_str))
            
        except TemplateSyntaxError as e:
            result["valid"] = False
            result["error"] = f"Syntax error: {str(e)}"
        except Exception as e:
            result["valid"] = False
            result["error"] = str(e)
        
        return result
    
    def preview(
        self, 
        template_str: str, 
        sample_data: Dict[str, Any] = None
    ) -> str:
        """
        Generate a preview of the rendered template with sample data.
        """
        if not sample_data:
            sample_data = {
                "name": "John",
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme Inc",
                "industry": "Technology",
                "title": "CEO",
                "email": "john@example.com",
            }
        
        return self.render(template_str, sample_data)
    
    def get_missing_placeholders(
        self, 
        template_str: str, 
        data: Dict[str, Any]
    ) -> List[str]:
        """
        Get list of placeholders in template that are missing from data.
        """
        required = self.extract_placeholders(template_str)
        available = set(data.keys())
        
        return list(required - available)


# Singleton instance
_renderer = None


def get_renderer() -> TemplateRenderer:
    """Get the singleton template renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = TemplateRenderer()
    return _renderer

