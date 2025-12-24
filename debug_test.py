from generate_config import generate_config_from_requirement
from phase5.value_extractor import ValueExtractor
from phase5.parameter_matcher import ParameterMatcher

# Test the failing case
requirement = "Create VIP 10.1.1.100 on port 443 with SSL offload"

# First check what values are extracted
extractor = ValueExtractor()
extracted = extractor.extract(requirement)
print("Extracted values:")
for value_type, values in extracted.items():
    if 'port' in value_type or 'integer' in value_type:
        for v in values:
            print(f"  {value_type}: {v.value} (confidence: {v.confidence})")
print()

# Test parameter matching specifically for real_port
matcher = ParameterMatcher()
param_info = {'type': 'integer', 'original_key': 'real_port'}

print("Testing scoring for real_port parameter:")
for value_type in ['port', 'integer']:
    if value_type in extracted:
        for idx, extr in enumerate(extracted[value_type]):
            score = matcher._calculate_match_score(
                'real_port',
                param_info,
                extr.value,
                value_type,
                extr
            )
            keywords = matcher._extract_keywords('real_port')
            print(f"  {value_type} value {extr.value}: score={score:.3f}, keywords={keywords}")
print()

result = generate_config_from_requirement(requirement, verbose=False)

config = result['config']
print(f"Generated {len(config.modules)} modules")
print()

for module in config.modules:
    if module.module_path == '/c/slb/virt':
        print(f"Module: {module.module_path}")
        for assignment in module.parameter_assignments:
            if 'port' in assignment.parameter_name.lower():
                print(f"  {assignment.parameter_name} = {assignment.value} (source: {assignment.source}, conf: {assignment.confidence:.3f})")
        print()

# Check specifically for port=443
for module in config.modules:
    for assignment in module.parameter_assignments:
        if assignment.parameter_name == 'port':
            print(f"Found port parameter in {module.module_path}: {assignment.value}")
            if assignment.value != '443':
                print(f"  ERROR: Expected 443, got {assignment.value}")
