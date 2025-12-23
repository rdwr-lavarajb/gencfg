"""
Phase 6: Configuration Validator
Main orchestrator for all validation steps.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from .syntax_validator import SyntaxValidator, ValidationError
from .type_checker import TypeChecker
from .cross_reference_validator import CrossReferenceValidator
from .dependency_validator import DependencyValidator


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    info: List[ValidationError]
    summary: str
    
    @property
    def total_issues(self) -> int:
        """Total number of issues."""
        return len(self.errors) + len(self.warnings) + len(self.info)


class ConfigValidator:
    """Orchestrates all validation steps."""
    
    def __init__(self):
        """Initialize config validator."""
        self.syntax_validator = SyntaxValidator()
        self.type_checker = TypeChecker()
        self.cross_ref_validator = CrossReferenceValidator()
        self.dependency_validator = DependencyValidator()
    
    def validate(
        self,
        config: Any,  # GeneratedConfig object
        check_syntax: bool = True,
        check_types: bool = True,
        check_references: bool = True,
        check_dependencies: bool = True
    ) -> ValidationResult:
        """
        Perform complete validation.
        
        Args:
            config: GeneratedConfig object
            check_syntax: Enable syntax validation
            check_types: Enable type checking
            check_references: Enable cross-reference validation
            check_dependencies: Enable dependency validation
            
        Returns:
            ValidationResult with all issues found
        """
        all_errors = []
        
        # 1. Syntax validation
        if check_syntax:
            config_lines = self._get_config_lines(config)
            is_valid, syntax_errors = self.syntax_validator.validate(config_lines)
            all_errors.extend(syntax_errors)
        
        # 2. Type checking
        if check_types:
            for module in config.modules:
                params = {
                    a.parameter_name: a.value
                    for a in module.parameter_assignments
                }
                type_errors = self.type_checker.validate_types(
                    module.module_path,
                    params
                )
                all_errors.extend(type_errors)
        
        # 3. Cross-reference validation
        if check_references:
            ref_errors = self.cross_ref_validator.validate_references(config.modules)
            all_errors.extend(ref_errors)
        
        # 4. Dependency validation
        if check_dependencies:
            dep_errors = self.dependency_validator.validate_dependencies(config.modules)
            all_errors.extend(dep_errors)
        
        # Categorize by severity
        errors = [e for e in all_errors if e.severity == 'error']
        warnings = [e for e in all_errors if e.severity == 'warning']
        info = [e for e in all_errors if e.severity == 'info']
        
        # Determine overall validity
        is_valid = len(errors) == 0
        
        # Generate summary
        summary = self._generate_summary(errors, warnings, info)
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info,
            summary=summary
        )
    
    def _get_config_lines(self, config: Any) -> List[str]:
        """Extract all configuration lines."""
        lines = []
        
        # Add header
        if config.header:
            lines.extend(config.header.split('\n'))
        
        # Add module lines
        for module in config.modules:
            lines.extend(module.config_lines)
            lines.append("")  # Blank line between modules
        
        # Add footer
        if config.footer:
            lines.extend(config.footer.split('\n'))
        
        return lines
    
    def _generate_summary(
        self,
        errors: List[ValidationError],
        warnings: List[ValidationError],
        info: List[ValidationError]
    ) -> str:
        """Generate validation summary."""
        lines = []
        
        if not errors and not warnings:
            lines.append("✅ Configuration validation passed!")
            lines.append(f"   No errors or warnings found.")
            if info:
                lines.append(f"   {len(info)} informational message(s)")
        else:
            if errors:
                lines.append(f"❌ Found {len(errors)} error(s)")
                for error in errors[:5]:  # Show first 5
                    lines.append(f"   • {error.message}")
                if len(errors) > 5:
                    lines.append(f"   ... and {len(errors) - 5} more errors")
            
            if warnings:
                lines.append(f"⚠️  Found {len(warnings)} warning(s)")
                for warning in warnings[:3]:  # Show first 3
                    lines.append(f"   • {warning.message}")
                if len(warnings) > 3:
                    lines.append(f"   ... and {len(warnings) - 3} more warnings")
        
        return "\n".join(lines)
    
    def print_detailed_report(self, result: ValidationResult) -> None:
        """Print detailed validation report."""
        print("\n" + "=" * 60)
        print("📋 VALIDATION REPORT")
        print("=" * 60)
        print()
        
        print(result.summary)
        print()
        
        if result.errors:
            print("❌ ERRORS:")
            for error in result.errors:
                print(f"\n  Line {error.line_number}: {error.message}")
                if error.module_path:
                    print(f"    Module: {error.module_path}")
                if error.suggestion:
                    print(f"    💡 {error.suggestion}")
        
        if result.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in result.warnings:
                print(f"\n  Line {warning.line_number}: {warning.message}")
                if warning.module_path:
                    print(f"    Module: {warning.module_path}")
                if warning.suggestion:
                    print(f"    💡 {warning.suggestion}")
        
        if result.info:
            print("\nℹ️  INFO:")
            for info_item in result.info:
                print(f"  • {info_item.message}")
        
        print("\n" + "=" * 60)
