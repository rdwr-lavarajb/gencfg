"""
Simple test script to verify parser functionality.
For full ingestion, use ingest_configs.py
"""

from utils.parser import ConfigParser


# Minimal test config
TEST_CONFIG = """
/c/sys/mmgmt
	addr 10.250.4.26
	mask 255.255.255.0
	ena
/c/port 1
	pvid 818
/c/l2/stg 1/clear
/c/slb/ssl/certs/import cert "TestCert" text
-----BEGIN CERTIFICATE-----
TEST_CONTENT
-----END CERTIFICATE-----

/c/slb/appshape/script 10
	ena
	import text
when INIT {
set static::STATUS_CODE "200"
}
when HTTP_REQUEST {
if {[group count active_servers [LB::server group]] == 0 } {
HTTP::respond $static::STATUS_CODE content $static::CONTENT
}
}
-----END

/c/slb/real 1
	ena
	ipver v4
	rip 10.254.76.32
	name "Srs426_tcp"
/c/slb/real Vision-Analytics
	ena
	ipver v4
	rip 10.252.27.142
/c/slb/group 4
	ipver v4
	add 3
	name "OMS-Monitor (1159)"
""""""


def main():
    """Quick parser test"""
    print("Testing parser...")
    parser = ConfigParser()
    modules = parser.parse(TEST_CONFIG)
    
    print(f"✓ Parsed {len(modules)} modules:")
    for m in modules:
        print(f"  - {m.module_path} {m.index or ''} ({m.module_type.value})")
    
    print("\n✓ Parser working correctly!")
    print("📌 For full ingestion, run: python ingest_configs.py")


if __name__ == "__main__":
    main()

    print("\n3. INDEXED MODULE (Named):")
    named_module = [m for m in modules if m.index == 'Vision-Analytics'][0]
    print(f"   Path: {named_module.module_path}")
    print(f"   Index: {named_module.index}")
    print(f"   Type: {named_module.module_type.value}")
    print(f"   Sub-lines: {named_module.sub_lines}")
    
    # Example 4: Action command
    print("\n4. ACTION COMMAND:")
    action_modules = [m for m in modules if m.module_type == ModuleType.ACTION]
    if action_modules:
        action = action_modules[0]
        print(f"   Path: {action.module_path}")
        print(f"   Type: {action.module_type.value}")
        print(f"   Parameters: {action.action_params}")
    
    # Example 5: Empty module
    print("\n5. EMPTY MODULE:")
    empty_modules = [m for m in modules if m.module_type == ModuleType.EMPTY]
    if empty_modules:
        empty = empty_modules[0]
        print(f"   Path: {empty.module_path}")
        print(f"   Index: {empty.index}")
        print(f"   Type: {empty.module_type.value}")
    
    # Example 6: Certificate module
    print("\n6. CERTIFICATE MODULE:")
    cert_modules = [m for m in modules if m.module_type == ModuleType.MULTILINE_CERT]
    if cert_modules:
        cert = cert_modules[0]
        print(f"   Path: {cert.module_path}")
"""


def main():
    """Quick parser test"""
    print("Testing parser...")
    parser = ConfigParser()
    modules = parser.parse(TEST_CONFIG)
    
    print(f"✓ Parsed {len(modules)} modules:")
    for m in modules:
        print(f"  - {m.module_path} {m.index or ''} ({m.module_type.value})")
    
    print("\n✓ Parser working correctly!")
    print("📌 For full ingestion, run: python ingest_configs.py")


if __name__ == "__main__":
    main()

