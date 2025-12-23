"""Verify form factor information in generated templates"""
import json
import glob

# Find the latest template file
files = glob.glob('data/templates/templated_modules_*.json')
if not files:
    print("❌ No template files found")
    exit(1)

latest_file = max(files)
print(f"Checking: {latest_file}\n")

with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

templates = data.get('templates', [])
print(f"Total templates: {len(templates)}\n")

# Check form factor fields
print("=" * 80)
print("FORM FACTOR VERIFICATION")
print("=" * 80)

has_ff = 0
no_ff = 0

print("\nSample templates with form factor info:\n")
for i, template in enumerate(templates[:10], 1):
    path = template.get('module_path', 'unknown')
    supported_ffs = template.get('supported_form_factors', [])
    ff_dist = template.get('form_factor_distribution', {})
    hypervisor = template.get('hypervisor_support')
    
    if supported_ffs:
        has_ff += 1
    else:
        no_ff += 1
    
    print(f"{i}. {path}")
    print(f"   Supported Form Factors: {supported_ffs}")
    print(f"   Distribution: {ff_dist}")
    if hypervisor:
        print(f"   Hypervisor: {hypervisor}")
    print()

# Overall statistics
print("=" * 80)
print("STATISTICS")
print("=" * 80)

all_form_factors = {}
for template in templates:
    ff_dist = template.get('form_factor_distribution', {})
    for ff, count in ff_dist.items():
        all_form_factors[ff] = all_form_factors.get(ff, 0) + count

print(f"Templates with form factor info: {has_ff}/{len(templates)}")
print(f"Templates without form factor info: {no_ff}/{len(templates)}")
print(f"\nForm Factor Distribution Across All Templates:")
for ff, count in sorted(all_form_factors.items()):
    print(f"  {ff}: {count}")

# Check specific important templates
print("\n" + "=" * 80)
print("CRITICAL TEMPLATES CHECK")
print("=" * 80)

critical_paths = ['/c/slb/real', '/c/slb/group', '/c/slb/virt', '/c/l3/if', '/c/port']
for path in critical_paths:
    template = next((t for t in templates if t['module_path'] == path), None)
    if template:
        supported = template.get('supported_form_factors', [])
        dist = template.get('form_factor_distribution', {})
        print(f"✅ {path:20s} → {supported} {dist}")
    else:
        print(f"❌ {path:20s} → NOT FOUND")

if has_ff > 0:
    print("\n✅ Form factor data is present in templates!")
else:
    print("\n❌ Form factor data is MISSING from templates!")
