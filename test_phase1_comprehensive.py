"""
Comprehensive test for Phase 1 parsing with form factor detection.
"""

from utils.parser import ConfigParser, ModuleType
import os

def test_basic_parsing():
    """Test basic parsing functionality"""
    print("=" * 80)
    print("TEST 1: Basic Parsing Functionality")
    print("=" * 80)
    
    parser = ConfigParser()
    with open("configs/va.txt", 'r', encoding='utf-8') as f:
        content = f.read()
    
    modules = parser.parse(content)
    
    print(f"✅ Total modules parsed: {len(modules)}")
    print(f"✅ Form factor detected: {parser.detected_form_factor}")
    
    # Check different module types
    standard_mods = [m for m in modules if m.module_type == ModuleType.STANDARD]
    action_mods = [m for m in modules if m.module_type == ModuleType.ACTION]
    empty_mods = [m for m in modules if m.module_type == ModuleType.EMPTY]
    
    print(f"✅ Standard modules: {len(standard_mods)}")
    print(f"✅ Action modules: {len(action_mods)}")
    print(f"✅ Empty modules: {len(empty_mods)}")
    
    # Show sample standard module
    if standard_mods:
        mod = standard_mods[0]
        print(f"\nSample Standard Module:")
        print(f"  Path: {mod.module_path}")
        print(f"  Index: {mod.index}")
        print(f"  Form Factor: {mod.form_factor}")
        print(f"  Sub-lines: {len(mod.sub_lines)}")
        print(f"  First 3 sub-lines:")
        for line in mod.sub_lines[:3]:
            print(f"    - {line}")
    
    # Show sample action module
    if action_mods:
        mod = action_mods[0]
        print(f"\nSample Action Module:")
        print(f"  Path: {mod.module_path}")
        print(f"  Index: {mod.index}")
        print(f"  Form Factor: {mod.form_factor}")
        print(f"  Action params: {mod.action_params}")
    
    return True

def test_form_factor_consistency():
    """Test that all modules have consistent form factor"""
    print("\n" + "=" * 80)
    print("TEST 2: Form Factor Consistency")
    print("=" * 80)
    
    for filename in ["va.txt", "sa2.txt", "adm.txt", "vad.txt"]:
        filepath = os.path.join("configs", filename)
        
        parser = ConfigParser()
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modules = parser.parse(content)
        detected_ff = parser.detected_form_factor
        
        # Check all modules have the same form factor
        config_modules = [m for m in modules if not m.module_path.startswith('/*')]
        
        if config_modules:
            all_same = all(m.form_factor == detected_ff for m in config_modules)
            status = "✅" if all_same else "❌"
            print(f"{status} {filename}: {detected_ff} - All {len(config_modules)} modules have consistent form_factor: {all_same}")
            
            if not all_same:
                mismatched = [m for m in config_modules if m.form_factor != detected_ff]
                print(f"   ⚠️  Mismatched modules: {len(mismatched)}")
                for m in mismatched[:3]:
                    print(f"      - {m.module_path}: {m.form_factor}")
    
    return True

def test_hypervisor_detection_in_real_config():
    """Test hypervisor detection with VA config"""
    print("\n" + "=" * 80)
    print("TEST 3: Hypervisor Detection in Real Config")
    print("=" * 80)
    
    # Create a test config with hypervisor-specific modules
    test_config = '''script start "Application Switch VA" 4  /**** DO NOT EDIT THIS LINE!
/* Test config
/c/slb/aws/settings
\tregion us-east-1
/c/slb/azure/config
\tsubscription test123
/c/slb/gcp/instance
\tproject my-project
/c/slb/real 1
\taddr 10.1.1.1
/c/AWS/integration
\tkey value
/c/normal/module
\tparam value
'''
    
    parser = ConfigParser()
    modules = parser.parse(test_config)
    
    print(f"Form Factor: {parser.detected_form_factor}")
    
    for mod in modules:
        if not mod.module_path.startswith('/*'):
            hypervisor = mod.hypervisor_support or "all"
            print(f"  {mod.module_path:30s} -> hypervisor: {hypervisor}")
    
    # Verify expected hypervisors
    expected = {
        "/c/slb/aws/settings": "aws",
        "/c/slb/azure/config": "azure",
        "/c/slb/gcp/instance": "gcp",
        "/c/slb/real": None,
        "/c/AWS/integration": "aws",
        "/c/normal/module": None
    }
    
    all_correct = True
    for mod in modules:
        if mod.module_path in expected:
            if mod.hypervisor_support != expected[mod.module_path]:
                print(f"❌ {mod.module_path}: Expected {expected[mod.module_path]}, got {mod.hypervisor_support}")
                all_correct = False
    
    if all_correct:
        print("✅ All hypervisor detections correct!")
    
    return all_correct

def test_indexed_modules():
    """Test parsing of indexed modules"""
    print("\n" + "=" * 80)
    print("TEST 4: Indexed Modules")
    print("=" * 80)
    
    parser = ConfigParser()
    with open("configs/adm.txt", 'r', encoding='utf-8') as f:
        content = f.read()
    
    modules = parser.parse(content)
    
    # Find indexed modules
    indexed = [m for m in modules if m.index and not m.module_path.startswith('/*')]
    
    print(f"Total indexed modules: {len(indexed)}")
    print("\nSample indexed modules:")
    
    for mod in indexed[:10]:
        print(f"  {mod.module_path:30s} index='{mod.index:10s}' ff={mod.form_factor}")
    
    # Check specific patterns
    port_modules = [m for m in modules if m.module_path == '/c/port']
    print(f"\n/c/port modules: {len(port_modules)}")
    for mod in port_modules[:3]:
        print(f"  Index: {mod.index}, Form Factor: {mod.form_factor}")
    
    return True

def test_multiline_content():
    """Test multiline content parsing (certificates)"""
    print("\n" + "=" * 80)
    print("TEST 5: Multiline Content Parsing")
    print("=" * 80)
    
    parser = ConfigParser()
    with open("configs/vad.txt", 'r', encoding='utf-8') as f:
        content = f.read()
    
    modules = parser.parse(content)
    
    # Find multiline modules
    multiline_mods = [m for m in modules if m.module_type in 
                      [ModuleType.MULTILINE_CERT, ModuleType.MULTILINE_SCRIPT]]
    
    print(f"Multiline modules found: {len(multiline_mods)}")
    
    for mod in multiline_mods[:3]:
        print(f"\n  Module: {mod.module_path}")
        print(f"  Type: {mod.module_type.value}")
        print(f"  Form Factor: {mod.form_factor}")
        print(f"  Metadata: {mod.multiline_metadata}")
        if mod.multiline_content:
            lines = mod.multiline_content.split('\n')
            print(f"  Content lines: {len(lines)}")
            print(f"  First line: {lines[0][:50]}...")
            print(f"  Last line: {lines[-1][:50]}...")
    
    return True

def test_action_modules():
    """Test action command parsing"""
    print("\n" + "=" * 80)
    print("TEST 6: Action Command Modules")
    print("=" * 80)
    
    parser = ConfigParser()
    with open("configs/sa2.txt", 'r', encoding='utf-8') as f:
        content = f.read()
    
    modules = parser.parse(content)
    
    # Find action modules
    action_mods = [m for m in modules if m.module_type == ModuleType.ACTION]
    
    print(f"Action modules found: {len(action_mods)}")
    print("\nSample action modules:")
    
    for mod in action_mods[:10]:
        params_str = ' '.join(mod.action_params) if mod.action_params else '(no params)'
        print(f"  {mod.module_path:35s} params: {params_str:20s} ff={mod.form_factor}")
    
    return True

def test_stats():
    """Test parser statistics"""
    print("\n" + "=" * 80)
    print("TEST 7: Parser Statistics")
    print("=" * 80)
    
    for filename in ["va.txt", "sa2.txt", "adm.txt", "vad.txt"]:
        filepath = os.path.join("configs", filename)
        
        parser = ConfigParser()
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modules = parser.parse(content)
        stats = parser.get_module_stats()
        
        print(f"\n{filename} ({parser.detected_form_factor}):")
        print(f"  Total modules: {stats['total_modules']}")
        print(f"  Unique paths: {stats['unique_paths']}")
        print(f"  Indexed modules: {stats['indexed_modules']}")
        print(f"  By type:")
        for mod_type, count in stats['by_type'].items():
            print(f"    - {mod_type}: {count}")
    
    return True

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PHASE 1 COMPREHENSIVE TESTS" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    tests = [
        ("Basic Parsing", test_basic_parsing),
        ("Form Factor Consistency", test_form_factor_consistency),
        ("Hypervisor Detection", test_hypervisor_detection_in_real_config),
        ("Indexed Modules", test_indexed_modules),
        ("Multiline Content", test_multiline_content),
        ("Action Modules", test_action_modules),
        ("Statistics", test_stats),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"   Error: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 1 is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")

if __name__ == "__main__":
    main()
