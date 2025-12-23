"""
Test script to verify form factor detection.
"""

from utils.parser import ConfigParser
import os

def test_form_factor_detection():
    """Test form factor detection with all sample configs"""
    
    config_dir = "configs"
    config_files = ["va.txt", "sa.txt", "sa2.txt", "adm.txt", "vad.txt"]
    
    print("Testing Form Factor Detection (Based on Headers Only)")
    print("=" * 80)
    print("Detection Rules:")
    print("  VA:   First line has 'VA' in quoted string (e.g., \"Application Switch VA\")")
    print("  VX:   Comment lines contain 'vADC Id 0'")
    print("  vADC: Comment lines contain 'vADC Id' with value > 0")
    print("  SA:   Default if none of the above")
    print("=" * 80)
    
    for filename in config_files:
        filepath = os.path.join(config_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"\n❌ {filename}: File not found")
            continue
        
        # Parse config
        parser = ConfigParser()
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modules = parser.parse(content)
        
        # Show detected form factor
        detected = parser.detected_form_factor
        
        print(f"\n✅ {filename}")
        print(f"   Detected Form Factor: {detected}")
        print(f"   Modules parsed: {len(modules)}")
        
        # Show header lines that matter for detection
        print(f"   Header (first 6 lines):")
        for i, line in enumerate(parser.header_lines[:6]):
            marker = ""
            if i == 0 and '"' in line and 'VA' in line:
                marker = " ← VA detected here"
            elif 'vADC Id' in line:
                marker = " ← vADC Id detected here"
            print(f"     {i+1}: {line[:70]}...{marker}")
        
        # Check if modules have form_factor set
        if modules:
            # Get first few actual config modules (skip comment lines)
            config_modules = [m for m in modules if not m.module_path.startswith('/*')][:3]
            if config_modules:
                print(f"   Sample config modules with form_factor:")
                for mod in config_modules:
                    hypervisor = f", hypervisor={mod.hypervisor_support}" if mod.hypervisor_support else ""
                    print(f"     - {mod.module_path} (ff={mod.form_factor}{hypervisor})")
    
    print("\n" + "=" * 80)
    print("Testing Hypervisor Detection for VA")
    print("=" * 80)
    
    # Test hypervisor detection with mock module paths
    test_cases = [
        ("/c/slb/aws/settings", "aws"),
        ("/c/slb/azure/config", "azure"),
        ("/c/slb/gcp/instance", "gcp"),
        ("/c/slb/real 1", None),
        ("/c/AWS/integration", "aws"),  # Case insensitive
        ("/c/Azure/VM", "azure"),
    ]
    
    parser = ConfigParser()
    
    for path, expected_hypervisor in test_cases:
        detected = parser._detect_hypervisor(path.lower())
        status = "✅" if detected == expected_hypervisor else "❌"
        print(f"{status} {path:30s} -> {detected or 'None':10s} (expected: {expected_hypervisor or 'None'})")

if __name__ == "__main__":
    test_form_factor_detection()
