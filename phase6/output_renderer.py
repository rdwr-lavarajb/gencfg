"""
Phase 6: Output Renderer
Renders final configuration output in various formats.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json


class OutputRenderer:
    """Renders configuration output in various formats."""
    
    def __init__(self):
        """Initialize output renderer."""
        pass
    
    def render_cli(
        self,
        config: Any,  # GeneratedConfig object
        include_metadata: bool = True
    ) -> str:
        """
        Render configuration in CLI format.
        
        Args:
            config: GeneratedConfig object
            include_metadata: Include metadata comments
            
        Returns:
            Formatted configuration string
        """
        output = []
        
        # Add header with metadata
        if include_metadata and config.header:
            output.append(config.header)
        
        # Add module configurations
        for module in config.modules:
            # Add module lines
            for line in module.config_lines:
                output.append(line)
            
            # Add blank line between modules for readability
            if module != config.modules[-1]:
                output.append("")
        
        # Add footer
        if config.footer:
            output.append(config.footer)
        
        return "\n".join(output)
    
    def render_json(
        self,
        config: Any,  # GeneratedConfig object
        pretty: bool = True
    ) -> str:
        """
        Render configuration in JSON format.
        
        Args:
            config: GeneratedConfig object
            pretty: Pretty print JSON
            
        Returns:
            JSON string
        """
        config_dict = {
            'metadata': {
                'timestamp': config.timestamp,
                'requirement': config.requirements_summary,
                'total_modules': config.metadata.get('total_modules', 0),
                'total_lines': config.metadata.get('total_lines', 0),
                'valid': config.metadata.get('valid', True)
            },
            'warnings': config.warnings,
            'modules': []
        }
        
        for module in config.modules:
            module_dict = {
                'module_path': module.module_path,
                'config_lines': module.config_lines,
                'parameters': [
                    {
                        'name': a.parameter_name,
                        'value': a.value,
                        'source': a.source,
                        'confidence': a.confidence
                    }
                    for a in module.parameter_assignments
                ],
                'missing_required': module.missing_required,
                'warnings': module.warnings,
                'metadata': module.metadata
            }
            config_dict['modules'].append(module_dict)
        
        indent = 2 if pretty else None
        return json.dumps(config_dict, indent=indent, default=str)
    
    def render_yaml(
        self,
        config: Any  # GeneratedConfig object
    ) -> str:
        """
        Render configuration in YAML format.
        
        Args:
            config: GeneratedConfig object
            
        Returns:
            YAML string
        """
        try:
            import yaml
        except ImportError:
            return "# YAML rendering requires PyYAML package\n# Install: pip install pyyaml"
        
        config_dict = {
            'metadata': {
                'timestamp': config.timestamp,
                'requirement': config.requirements_summary,
                'total_modules': config.metadata.get('total_modules', 0),
                'total_lines': config.metadata.get('total_lines', 0),
            },
            'warnings': config.warnings,
            'modules': [
                {
                    'path': module.module_path,
                    'lines': module.config_lines,
                    'parameters': {
                        a.parameter_name: {
                            'value': a.value,
                            'source': a.source,
                            'confidence': a.confidence
                        }
                        for a in module.parameter_assignments
                    }
                }
                for module in config.modules
            ]
        }
        
        return yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
    
    def render_html(
        self,
        config: Any,  # GeneratedConfig object
        title: str = "Generated Configuration"
    ) -> str:
        """
        Render configuration in HTML format.
        
        Args:
            config: GeneratedConfig object
            title: Page title
            
        Returns:
            HTML string
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 15px;
            margin: -20px -20px 20px -20px;
        }}
        .metadata {{
            background-color: #ecf0f1;
            padding: 10px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }}
        .warnings {{
            background-color: #fff3cd;
            padding: 10px;
            margin-bottom: 20px;
            border-left: 4px solid #ffc107;
        }}
        .module {{
            margin-bottom: 30px;
            border: 1px solid #ddd;
            padding: 15px;
        }}
        .module-header {{
            background-color: #34495e;
            color: white;
            padding: 8px;
            margin: -15px -15px 15px -15px;
            font-weight: bold;
        }}
        .config-line {{
            margin: 3px 0;
            padding: 3px;
            background-color: #f8f9fa;
        }}
        .parameter {{
            display: inline-block;
            margin: 3px 5px;
            padding: 2px 8px;
            background-color: #e7f3ff;
            border-radius: 3px;
            font-size: 12px;
        }}
        pre {{
            background-color: #f8f9fa;
            padding: 15px;
            overflow-x: auto;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Generated: {config.timestamp}</p>
        </div>
        
        <div class="metadata">
            <h3>Configuration Metadata</h3>
            <p><strong>Requirement:</strong> {config.requirements_summary}</p>
            <p><strong>Total Modules:</strong> {config.metadata.get('total_modules', 0)}</p>
            <p><strong>Total Lines:</strong> {config.metadata.get('total_lines', 0)}</p>
        </div>
"""
        
        if config.warnings:
            html += """        <div class="warnings">
            <h3>⚠️ Warnings</h3>
            <ul>
"""
            for warning in config.warnings[:10]:  # Show first 10
                html += f"                <li>{warning}</li>\n"
            html += """            </ul>
        </div>
"""
        
        html += """        <h2>Configuration Modules</h2>
"""
        
        for idx, module in enumerate(config.modules, 1):
            html += f"""        <div class="module">
            <div class="module-header">
                {idx}. {module.module_path}
            </div>
            <div>
                <strong>Parameters:</strong>
"""
            for assignment in module.parameter_assignments:
                html += f"""                <span class="parameter">{assignment.parameter_name}={assignment.value}</span>
"""
            
            html += """            </div>
            <h4>Configuration:</h4>
            <pre>"""
            for line in module.config_lines:
                html += f"{line}\n"
            html += """</pre>
        </div>
"""
        
        html += """        <h2>Complete Configuration</h2>
        <pre>"""
        html += self.render_cli(config, include_metadata=True)
        html += """</pre>
    </div>
</body>
</html>"""
        
        return html
    
    def save_to_file(
        self,
        content: str,
        file_path: Path,
        format: str = 'cli'
    ) -> bool:
        """
        Save rendered content to file.
        
        Args:
            content: Rendered content
            file_path: Output file path
            format: Output format ('cli', 'json', 'yaml', 'html')
            
        Returns:
            True if successful
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False
