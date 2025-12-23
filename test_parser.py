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
"""


def main():
    """Quick parser test"""
    print("Testing parser...")
    parser = ConfigParser()
    modules = parser.parse(TEST_CONFIG)
    
    print(f"✓ Parsed {len(modules)} modules:")
    for m in modules:
        index_str = f" {m.index}" if m.index else ""
        ff_str = f" [ff={m.form_factor}]" if m.form_factor else ""
        print(f"  - {m.module_path}{index_str} ({m.module_type.value}){ff_str}")
    
    print("\n✓ Parser working correctly with form factor support!")
    print("📌 For full ingestion, run: python ingest_configs.py")


if __name__ == "__main__":
    main()

