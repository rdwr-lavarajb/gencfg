"""
Phase 5: Config Generator
Generates final configuration files from assembled modules.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path


@dataclass
class GeneratedConfig:
    """A complete generated configuration."""
    modules: List[Any]  # AssembledModule objects
    header: str
    footer: str
    timestamp: str
    requirements_summary: str
    warnings: List[str]
    metadata: Dict[str, Any]


class ConfigGenerator:
    """Generates final configuration files."""
    
    def __init__(self):
        """Initialize config generator."""
        self.default_header = "# Generated Configuration\n# Timestamp: {timestamp}\n"
        self.default_footer = "\napply\nsave\n"
    
    def generate(
        self,
        modules: List[Any],  # Ordered AssembledModule objects
        requirement: str = "",
        include_header: bool = True,
        include_footer: bool = True,
        add_comments: bool = True
    ) -> GeneratedConfig:
        """
        Generate complete configuration.
        
        Args:
            modules: Ordered list of AssembledModule objects
            requirement: Original user requirement
            include_header: Whether to include header
            include_footer: Whether to include apply/save commands
            add_comments: Whether to add explanatory comments
            
        Returns:
            GeneratedConfig object
        """
        timestamp = datetime.now().isoformat()
        
        # Build header
        header = ""
        if include_header:
            header = self.default_header.format(timestamp=timestamp)
            if requirement:
                header += f"# Requirement: {requirement}\n"
            header += "#\n"
        
        # Build footer
        footer = ""
        if include_footer:
            footer = self.default_footer
        
        # Collect warnings
        all_warnings = []
        for module in modules:
            all_warnings.extend(module.warnings)
            if module.missing_required:
                all_warnings.append(
                    f"{module.module_path}: Missing required parameters: {', '.join(module.missing_required)}"
                )
        
        return GeneratedConfig(
            modules=modules,
            header=header,
            footer=footer,
            timestamp=timestamp,
            requirements_summary=requirement,
            warnings=all_warnings,
            metadata={
                'total_modules': len(modules),
                'total_lines': sum(len(m.config_lines) for m in modules),
                'valid': len(all_warnings) == 0
            }
        )
    
    def to_string(
        self,
        config: GeneratedConfig,
        format_style: str = "cli"
    ) -> str:
        """
        Convert GeneratedConfig to string.
        
        Args:
            config: GeneratedConfig object
            format_style: 'cli' or 'compact'
            
        Returns:
            String representation
        """
        lines = []
        
        # Header
        if config.header:
            lines.append(config.header)
        
        # Modules
        for module in config.modules:
            # Add blank line before each module
            if format_style == "cli":
                lines.append("")
            
            # Add module lines
            for line in module.config_lines:
                lines.append(line)
        
        # Footer
        if config.footer:
            lines.append("")
            lines.append(config.footer)
        
        return '\n'.join(lines)
    
    def to_dict(self, config: GeneratedConfig) -> Dict[str, Any]:
        """
        Convert GeneratedConfig to dictionary (for JSON export).
        
        Args:
            config: GeneratedConfig object
            
        Returns:
            Dict representation
        """
        return {
            'timestamp': config.timestamp,
            'requirement': config.requirements_summary,
            'metadata': config.metadata,
            'warnings': config.warnings,
            'modules': [
                {
                    'module_path': m.module_path,
                    'config_lines': m.config_lines,
                    'category': m.metadata.get('category'),
                    'parameter_count': len(m.parameter_assignments),
                    'parameters': [
                        {
                            'name': a.parameter_name,
                            'value': a.value,
                            'source': a.source,
                            'confidence': a.confidence
                        }
                        for a in m.parameter_assignments
                    ]
                }
                for m in config.modules
            ]
        }
    
    def save_to_file(
        self,
        config: GeneratedConfig,
        file_path: Path,
        format_style: str = "cli"
    ):
        """
        Save configuration to file.
        
        Args:
            config: GeneratedConfig object
            file_path: Path to save file
            format_style: Output format
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.to_string(config, format_style)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def print_summary(self, config: GeneratedConfig):
        """Print configuration summary."""
        print("\n" + "=" * 60)
        print("📄 GENERATED CONFIGURATION")
        print("=" * 60)
        
        print(f"\n📊 Summary:")
        print(f"   Total modules: {config.metadata['total_modules']}")
        print(f"   Total lines: {config.metadata['total_lines']}")
        print(f"   Timestamp: {config.timestamp}")
        
        if config.requirements_summary:
            print(f"\n📝 Requirement:")
            print(f"   {config.requirements_summary}")
        
        if config.warnings:
            print(f"\n⚠️  Warnings ({len(config.warnings)}):")
            for warning in config.warnings[:5]:  # Show first 5
                print(f"   - {warning}")
            if len(config.warnings) > 5:
                print(f"   ... and {len(config.warnings) - 5} more")
        else:
            print("\n✅ No warnings - configuration is valid")
        
        print(f"\n📦 Modules:")
        for i, module in enumerate(config.modules, 1):
            param_count = len(module.parameter_assignments)
            user_params = sum(1 for a in module.parameter_assignments if a.source == 'user')
            default_params = param_count - user_params
            
            print(f"\n{i}. {module.module_path}")
            print(f"   Category: {module.metadata.get('category', 'unknown')}")
            print(f"   Parameters: {param_count} ({user_params} user, {default_params} default)")
            print(f"   Lines: {len(module.config_lines)}")
            
            # Show parameter assignments
            if module.parameter_assignments:
                print(f"   Values:")
                for a in module.parameter_assignments[:3]:  # Show first 3
                    source_icon = "👤" if a.source == "user" else "⚙️"
                    print(f"     {source_icon} {a.original_param_key}: {a.value}")
                if len(module.parameter_assignments) > 3:
                    print(f"     ... and {len(module.parameter_assignments) - 3} more")
    
    def print_preview(self, config: GeneratedConfig, max_lines: int = 30):
        """Print preview of generated configuration."""
        print("\n" + "=" * 60)
        print("👁️  CONFIGURATION PREVIEW")
        print("=" * 60)
        
        config_str = self.to_string(config)
        lines = config_str.split('\n')
        
        # Print first max_lines
        for line in lines[:max_lines]:
            print(line)
        
        if len(lines) > max_lines:
            print(f"\n... ({len(lines) - max_lines} more lines)")
