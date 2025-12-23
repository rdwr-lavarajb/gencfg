"""Quick verification that form factor is in parsed data"""
import json
import glob

# Find the latest parsed file
files = glob.glob('data/parsed/parsed_modules_*.json')
if not files:
    print("❌ No parsed files found")
    exit(1)

latest_file = max(files)
print(f"Checking: {latest_file}\n")

with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get config modules (not comment lines)
config_modules = [m for m in data['modules'] if not m['module_path'].startswith('/*')]

print(f"Total config modules: {len(config_modules)}\n")

# Check first 10 modules
print("First 10 modules:")
print("=" * 80)
for i, mod in enumerate(config_modules[:10], 1):
    ff = mod.get('form_factor', 'MISSING')
    hyp = mod.get('hypervisor_support') or 'N/A'
    idx = mod.get('index') or ''
    
    print(f"{i}. {mod['module_path']} {idx}")
    print(f"   Form Factor: {ff}, Hypervisor: {hyp}")

# Count by form factor
print("\n" + "=" * 80)
print("Form Factor Distribution:")
ff_counts = {}
for mod in config_modules:
    ff = mod.get('form_factor', 'MISSING')
    ff_counts[ff] = ff_counts.get(ff, 0) + 1

for ff, count in sorted(ff_counts.items()):
    print(f"  {ff}: {count}")

# Check hypervisor support
hyp_modules = [m for m in config_modules if m.get('hypervisor_support')]
print(f"\nModules with hypervisor support: {len(hyp_modules)}")

if config_modules and config_modules[0].get('form_factor'):
    print("\n✅ Form factor data is present in parsed modules!")
else:
    print("\n❌ Form factor data is MISSING from parsed modules!")
