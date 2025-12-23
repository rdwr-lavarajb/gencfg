"""
Configuration Parser for Alteon/Radware CLI-style configurations.

This module parses hierarchical configuration files into structured module blocks.
Handles multi-line content (certificates, scripts) and normalizes whitespace.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import re


class ModuleType(Enum):
    """Types of configuration modules"""
    STANDARD = "standard"           # Regular config module with sub-lines
    ACTION = "action"               # Command-style (e.g., /c/l2/stg 1/clear)
    MULTILINE_CERT = "multiline_cert"     # Certificate import
    MULTILINE_SCRIPT = "multiline_script"  # Script import
    EMPTY = "empty"                 # Module declaration with no content


@dataclass
class ModuleBlock:
    """Represents a single configuration module block"""
    module_path: str                    # e.g., "/c/l3/if"
    index: Optional[str] = None         # e.g., "1" or "Vision-Analytics"
    raw_lines: List[str] = field(default_factory=list)  # Original lines
    sub_lines: List[str] = field(default_factory=list)  # Normalized sub-lines
    module_type: ModuleType = ModuleType.STANDARD
    start_line: int = 0                 # Line number in source
    end_line: int = 0
    
    # Multi-line content
    multiline_content: Optional[str] = None
    multiline_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Action command parameters (for ACTION type)
    action_params: List[str] = field(default_factory=list)
    
    # Form factor support (VA, SA, VX, vADC)
    form_factor: Optional[str] = None
    
    # Hypervisor support for VA (aws, azure, gcp, or None for all)
    hypervisor_support: Optional[str] = None
    
    def __repr__(self) -> str:
        index_str = f" {self.index}" if self.index else ""
        return f"<ModuleBlock {self.module_path}{index_str} ({self.module_type.value})>"


class ConfigParser:
    """Parser for hierarchical CLI-style configuration files"""
    
    # Patterns for detecting multi-line content triggers
    CERT_IMPORT_PATTERN = re.compile(r'import\s+(cert|request|key)\s+"([^"]+)"\s+text', re.IGNORECASE)
    SCRIPT_IMPORT_PATTERN = re.compile(r'import\s+text', re.IGNORECASE)
    
    # Multi-line content markers
    CERT_BEGIN_MARKERS = ['-----BEGIN CERTIFICATE-----', '-----BEGIN CERTIFICATE REQUEST-----']
    MULTILINE_END_MARKER = '-----END'
    
    # Action command patterns (commands that end in specific keywords)
    ACTION_KEYWORDS = ['clear', 'add', 'delete', 'remove', 'on', 'off']
    
    def __init__(self):
        self.modules: List[ModuleBlock] = []
        self.current_module: Optional[ModuleBlock] = None
        self.in_multiline: bool = False
        self.multiline_buffer: List[str] = []
        self.multiline_type: Optional[ModuleType] = None
        self.line_number: int = 0
        self.detected_form_factor: Optional[str] = None  # Detected device form factor
        self.header_lines: List[str] = []  # Store header lines for parsing
        
    def parse(self, config_text: str) -> List[ModuleBlock]:
        """
        Parse configuration text into module blocks.
        
        Args:
            config_text: Raw configuration file content
            
        Returns:
            List of ModuleBlock objects
        """
        self.modules = []
        self.current_module = None
        self.in_multiline = False
        self.multiline_buffer = []
        self.line_number = 0
        self.detected_form_factor = None
        self.header_lines = []
        
        lines = config_text.split('\n')
        
        # Detect form factor from header (first ~10 lines)
        self._detect_form_factor(lines[:15])
        
        for line in lines:
            self.line_number += 1
            self._process_line(line)
        
        # Save last module if exists
        if self.current_module:
            self._finalize_current_module()
        
        return self.modules
    
    def _process_line(self, line: str):
        """Process a single line of configuration"""
        
        # Handle multi-line content mode
        if self.in_multiline:
            self._process_multiline_content(line)
            return
        
        # Check if line is a module header (starts with '/')
        if line.startswith('/'):
            self._process_module_header(line)
            return
        
        # Check if line is a sub-line (indented)
        if line and (line.startswith('\t') or line.startswith(' ')):
            self._process_subline(line)
            return
        
        # Empty line or unrecognized - skip
        pass
    
    def _process_module_header(self, line: str):
        """Process a module header line starting with '/'"""
        
        # Save previous module
        if self.current_module:
            self._finalize_current_module()
        
        # Create new module
        self.current_module = ModuleBlock(
            module_path="",
            start_line=self.line_number
        )
        self.current_module.raw_lines.append(line)
        
        # Parse the module path and optional index
        self._parse_module_path(line.strip())
        
        # Set form factor for this module
        self.current_module.form_factor = self.detected_form_factor
        
        # Detect hypervisor support for VA modules
        if self.detected_form_factor == 'VA':
            self.current_module.hypervisor_support = self._detect_hypervisor(line.lower())
    
    def _parse_module_path(self, line: str):
        """Extract module path, index, and detect action commands"""
        
        # Split the line into tokens
        tokens = line.split()
        
        if not tokens:
            return
        
        # First token is always the module path
        module_path = tokens[0]
        self.current_module.module_path = module_path
        
        # Check if there are additional tokens
        if len(tokens) > 1:
            # Check if path ends with an action keyword (e.g., /c/l2/stg/clear)
            path_parts = module_path.split('/')
            if path_parts and path_parts[-1].lower() in self.ACTION_KEYWORDS:
                # Action is part of the path itself
                self.current_module.module_type = ModuleType.ACTION
                # All remaining tokens are parameters
                self.current_module.action_params = tokens[1:]
            
            # Check if last token is an action keyword
            elif tokens[-1].lower() in self.ACTION_KEYWORDS:
                # This is an action command
                self.current_module.module_type = ModuleType.ACTION
                
                # Tokens between path and action keyword are parameters
                if len(tokens) > 2:
                    self.current_module.action_params = tokens[1:-1]
                
            else:
                # Remaining tokens form the index (could be multiple words)
                self.current_module.index = ' '.join(tokens[1:])
    
    def _process_subline(self, line: str):
        """Process an indented sub-line belonging to current module"""
        
        if not self.current_module:
            # Orphan sub-line without a module - skip
            return
        
        # Add to raw lines
        self.current_module.raw_lines.append(line)
        
        # Normalize: strip leading whitespace but preserve structure
        normalized = line.strip()
        
        if not normalized:
            return
        
        # Check if this line triggers multi-line content
        if self._check_multiline_trigger(normalized):
            return
        
        # Add to sub-lines
        self.current_module.sub_lines.append(normalized)
    
    def _check_multiline_trigger(self, line: str) -> bool:
        """Check if line triggers multi-line content mode"""
        
        # Check for certificate import
        cert_match = self.CERT_IMPORT_PATTERN.search(line)
        if cert_match:
            self.in_multiline = True
            self.multiline_type = ModuleType.MULTILINE_CERT
            self.multiline_buffer = []
            
            # Extract metadata
            cert_type = cert_match.group(1)  # cert, request, or key
            cert_name = cert_match.group(2)
            self.current_module.multiline_metadata = {
                'cert_type': cert_type,
                'cert_name': cert_name
            }
            self.current_module.module_type = ModuleType.MULTILINE_CERT
            
            # Add this line to sub_lines (it's part of the command)
            self.current_module.sub_lines.append(line)
            return True
        
        # Check for script import
        script_match = self.SCRIPT_IMPORT_PATTERN.search(line)
        if script_match:
            self.in_multiline = True
            self.multiline_type = ModuleType.MULTILINE_SCRIPT
            self.multiline_buffer = []
            
            # Extract script ID from module index
            if self.current_module.index:
                self.current_module.multiline_metadata = {
                    'script_id': self.current_module.index
                }
            self.current_module.module_type = ModuleType.MULTILINE_SCRIPT
            
            # Add this line to sub_lines
            self.current_module.sub_lines.append(line)
            return True
        
        return False
    
    def _process_multiline_content(self, line: str):
        """Process lines while in multi-line content mode"""
        
        # Add to raw lines
        if self.current_module:
            self.current_module.raw_lines.append(line)
        
        # Check for end marker
        if line.strip().startswith(self.MULTILINE_END_MARKER):
            # End of multi-line content
            self.multiline_buffer.append(line)
            
            # Save the multi-line content
            if self.current_module:
                self.current_module.multiline_content = '\n'.join(self.multiline_buffer)
            
            # Exit multi-line mode
            self.in_multiline = False
            self.multiline_buffer = []
            self.multiline_type = None
            return
        
        # Accumulate content
        self.multiline_buffer.append(line)
    
    def _detect_form_factor(self, header_lines: List[str]):
        """
        Detect device form factor from configuration header.
        
        Detection rules:
        - VA: First line contains 'VA' as part of quoted string
        - VX: Comment lines contain 'vADC Id 0'
        - vADC: Comment lines contain 'vADC Id' with value > 0
        - SA: Default if none of the above
        """
        self.header_lines = header_lines
        
        # Check first line for VA - look for "VA" in quotes or " VA" with space before
        if header_lines:
            first_line = header_lines[0]
            # Match patterns like: "Application Switch VA" or "VA ..."
            if re.search(r'\"[^\"]*\sVA\s*\"', first_line) or re.search(r'\"VA\s', first_line):
                self.detected_form_factor = 'VA'
                return
        
        # Check comment lines for vADC Id
        for line in header_lines:
            if line.strip().startswith('/*'):
                # Look for vADC Id pattern
                vadc_match = re.search(r'vADC\s+Id\s+(\d+)', line, re.IGNORECASE)
                if vadc_match:
                    vadc_id = int(vadc_match.group(1))
                    if vadc_id == 0:
                        self.detected_form_factor = 'VX'
                    else:
                        self.detected_form_factor = 'vADC'
                    return
        
        # Default to SA
        self.detected_form_factor = 'SA'
    
    def _detect_hypervisor(self, module_path_lower: str) -> Optional[str]:
        """
        Detect hypervisor support for VA modules based on module path.
        
        Args:
            module_path_lower: Lowercase module path string
            
        Returns:
            'aws', 'azure', 'gcp', or None (supports all)
        """
        if 'aws' in module_path_lower:
            return 'aws'
        elif 'azure' in module_path_lower:
            return 'azure'
        elif 'gcp' in module_path_lower:
            return 'gcp'
        return None
    
    def _finalize_current_module(self):
        """Finalize and save the current module"""
        
        if not self.current_module:
            return
        
        self.current_module.end_line = self.line_number
        
        # Determine final module type if not already set
        if self.current_module.module_type == ModuleType.STANDARD:
            if not self.current_module.sub_lines and not self.current_module.multiline_content:
                self.current_module.module_type = ModuleType.EMPTY
        
        self.modules.append(self.current_module)
        self.current_module = None
    
    def get_modules_by_path(self, path: str) -> List[ModuleBlock]:
        """Get all modules matching a specific path"""
        return [m for m in self.modules if m.module_path == path]
    
    def get_modules_by_type(self, module_type: ModuleType) -> List[ModuleBlock]:
        """Get all modules of a specific type"""
        return [m for m in self.modules if m.module_type == module_type]
    
    def get_module_stats(self) -> Dict[str, Any]:
        """Get statistics about parsed modules"""
        stats = {
            'total_modules': len(self.modules),
            'by_type': {},
            'unique_paths': len(set(m.module_path for m in self.modules)),
            'indexed_modules': len([m for m in self.modules if m.index]),
        }
        
        for module_type in ModuleType:
            count = len(self.get_modules_by_type(module_type))
            if count > 0:
                stats['by_type'][module_type.value] = count
        
        return stats


def parse_config_file(file_path: str) -> List[ModuleBlock]:
    """
    Convenience function to parse a configuration file.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        List of ModuleBlock objects
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parser = ConfigParser()
    return parser.parse(content)
