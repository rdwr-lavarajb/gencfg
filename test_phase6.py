"""
Test Phase 6 validation and multiple output formats.
"""

from pathlib import Path
from generate_config import generate_config_from_requirement
from phase6.output_renderer import OutputRenderer
from phase5.config_generator import ConfigGenerator

def test_phase6():
    """Test Phase 6 validation and rendering."""
    
    print("=" * 70)
    print("Testing Phase 6: Validation & Rendering")
    print("=" * 70)
    
    # Generate a configuration
    requirement = "Create VIP 10.1.1.100 on port 443 with SSL offload"
    
    print(f"\n📝 Requirement: {requirement}\n")
    
    result = generate_config_from_requirement(requirement, verbose=False)
    
    if not result['config']:
        print("❌ Failed to generate configuration")
        return
    
    config = result['config']
    validation = result['validation']
    
    # Print validation results
    print("\n" + "=" * 70)
    print("📋 VALIDATION RESULTS")
    print("=" * 70)
    print(f"\nStatus: {'✅ VALID' if validation.is_valid else '❌ INVALID'}")
    print(f"Errors: {len(validation.errors)}")
    print(f"Warnings: {len(validation.warnings)}")
    print(f"Info: {len(validation.info)}")
    
    if validation.errors:
        print("\n❌ Errors:")
        for error in validation.errors:
            print(f"  • {error.message}")
    
    if validation.warnings:
        print("\n⚠️  Warnings:")
        for warning in validation.warnings[:5]:
            print(f"  • {warning.message}")
    
    # Test different output formats
    renderer = OutputRenderer()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 70)
    print("📄 RENDERING TO MULTIPLE FORMATS")
    print("=" * 70)
    
    # 1. CLI Format (default)
    print("\n1️⃣  CLI Format...")
    cli_output = renderer.render_cli(config, include_metadata=True)
    cli_file = output_dir / "config.txt"
    renderer.save_to_file(cli_output, cli_file, format='cli')
    print(f"   ✅ Saved to: {cli_file}")
    print(f"   📊 Size: {len(cli_output)} bytes")
    
    # 2. JSON Format
    print("\n2️⃣  JSON Format...")
    json_output = renderer.render_json(config, pretty=True)
    json_file = output_dir / "config.json"
    renderer.save_to_file(json_output, json_file, format='json')
    print(f"   ✅ Saved to: {json_file}")
    print(f"   📊 Size: {len(json_output)} bytes")
    
    # 3. YAML Format
    print("\n3️⃣  YAML Format...")
    try:
        yaml_output = renderer.render_yaml(config)
        yaml_file = output_dir / "config.yaml"
        renderer.save_to_file(yaml_output, yaml_file, format='yaml')
        print(f"   ✅ Saved to: {yaml_file}")
        print(f"   📊 Size: {len(yaml_output)} bytes")
    except Exception as e:
        print(f"   ⚠️  YAML not available: {e}")
    
    # 4. HTML Format
    print("\n4️⃣  HTML Format...")
    html_output = renderer.render_html(config, title="Generated Load Balancer Config")
    html_file = output_dir / "config.html"
    renderer.save_to_file(html_output, html_file, format='html')
    print(f"   ✅ Saved to: {html_file}")
    print(f"   📊 Size: {len(html_output)} bytes")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ PHASE 6 TEST COMPLETE")
    print("=" * 70)
    print(f"\n📁 All outputs saved to: {output_dir.absolute()}")
    print(f"\n💡 Open {html_file} in your browser to view the HTML report!")
    print()

if __name__ == "__main__":
    test_phase6()
