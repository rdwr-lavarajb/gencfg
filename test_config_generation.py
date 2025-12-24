"""
Comprehensive Test Suite for Configuration Generation
Tests all phases of the configuration generation pipeline.
"""

from pathlib import Path
from generate_config import generate_config_from_requirement
from phase6.config_validator import ConfigValidator
import json


class ConfigGenerationTester:
    """Test suite for configuration generation"""
    
    def __init__(self):
        self.validator = ConfigValidator()
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def run_all_tests(self):
        """Run all test cases"""
        print("=" * 80)
        print("🧪 COMPREHENSIVE CONFIGURATION GENERATION TEST SUITE")
        print("=" * 80)
        print()
        
        # Test categories
        self.test_vip_configurations()
        self.test_server_configurations()
        self.test_network_configurations()
        self.test_ssl_configurations()
        self.test_complex_scenarios()
        self.test_edge_cases()
        
        # Print summary
        self.print_summary()
    
    def test_vip_configurations(self):
        """Test VIP creation scenarios"""
        print("\n" + "=" * 80)
        print("📦 TEST CATEGORY: VIP Configurations")
        print("=" * 80)
        
        test_cases = [
            {
                "name": "Basic VIP with HTTP",
                "requirement": "Create VIP 192.168.1.100 on port 80",
                "expected_modules": ["/c/slb/virt"],
                "expected_params": {"vip": "192.168.1.100", "port": "80"}
            },
            {
                "name": "VIP with SSL on port 443",
                "requirement": "Create VIP 10.1.1.100 on port 443 with SSL offload",
                "expected_modules": ["/c/slb/virt", "/c/slb/virt/service"],
                "expected_params": {"vip": "10.1.1.100", "port": "443"}
            },
            {
                "name": "VIP with HTTPS",
                "requirement": "Configure HTTPS virtual server 172.16.1.50",
                "expected_modules": ["/c/slb/virt"],
                "expected_params": {"vip": "172.16.1.50"}
            },
            {
                "name": "VIP with custom port",
                "requirement": "Setup load balancer VIP 10.10.10.10 port 8080",
                "expected_modules": ["/c/slb/virt"],
                "expected_params": {"vip": "10.10.10.10", "port": "8080"}
            }
        ]
        
        for test_case in test_cases:
            self.run_test(test_case)
    
    def test_server_configurations(self):
        """Test server and server group configurations"""
        print("\n" + "=" * 80)
        print("📦 TEST CATEGORY: Server Configurations")
        print("=" * 80)
        
        test_cases = [
            {
                "name": "Real server configuration",
                "requirement": "Add real server 192.168.1.10",
                "expected_modules": ["/c/slb/real"],
                "expected_params": {"rip": "192.168.1.10"}
            },
            {
                "name": "Server group configuration",
                "requirement": "Create server group with member 10.0.0.5",
                "expected_modules": ["/c/slb/group", "/c/slb/real"],
                "expected_params": {}
            },
            {
                "name": "Multiple real servers",
                "requirement": "Configure backend servers 192.168.2.10, 192.168.2.11, 192.168.2.12",
                "expected_modules": ["/c/slb/real"],
                "expected_params": {}
            }
        ]
        
        for test_case in test_cases:
            self.run_test(test_case)
    
    def test_network_configurations(self):
        """Test network/interface configurations"""
        print("\n" + "=" * 80)
        print("📦 TEST CATEGORY: Network Configurations")
        print("=" * 80)
        
        test_cases = [
            {
                "name": "VLAN configuration",
                "requirement": "Create VLAN 100 with IP 10.0.100.1/24",
                "expected_modules": ["/c/l2/vlan"],
                "expected_params": {}
            },
            {
                "name": "Interface configuration",
                "requirement": "Configure interface with IP 172.16.0.1",
                "expected_modules": ["/c/l3/if"],
                "expected_params": {}
            },
            {
                "name": "Port configuration",
                "requirement": "Configure port 1 with 1000Mbps",
                "expected_modules": ["/c/port"],
                "expected_params": {}
            }
        ]
        
        for test_case in test_cases:
            self.run_test(test_case)
    
    def test_ssl_configurations(self):
        """Test SSL/TLS configurations"""
        print("\n" + "=" * 80)
        print("📦 TEST CATEGORY: SSL Configurations")
        print("=" * 80)
        
        test_cases = [
            {
                "name": "SSL policy configuration",
                "requirement": "Create SSL policy for HTTPS offload",
                "expected_modules": ["/c/slb/ssl/sslpol"],
                "expected_params": {}
            },
            {
                "name": "SSL with VIP",
                "requirement": "Setup SSL offload for VIP 10.1.1.50 on port 443",
                "expected_modules": ["/c/slb/virt", "/c/slb/ssl/sslpol"],
                "expected_params": {"vip": "10.1.1.50", "port": "443"}
            }
        ]
        
        for test_case in test_cases:
            self.run_test(test_case)
    
    def test_complex_scenarios(self):
        """Test complex multi-component scenarios"""
        print("\n" + "=" * 80)
        print("📦 TEST CATEGORY: Complex Scenarios")
        print("=" * 80)
        
        test_cases = [
            {
                "name": "Complete load balancing setup",
                "requirement": "Setup load balancer with VIP 10.1.1.100 port 443 SSL, backend servers 192.168.1.10 and 192.168.1.11",
                "expected_modules": ["/c/slb/virt", "/c/slb/group", "/c/slb/real"],
                "expected_params": {"vip": "10.1.1.100"}
            },
            {
                "name": "Web server farm",
                "requirement": "Create web server farm on 172.16.1.100 port 80 with 3 backend servers",
                "expected_modules": ["/c/slb/virt", "/c/slb/group"],
                "expected_params": {"vip": "172.16.1.100", "port": "80"}
            },
            {
                "name": "HTTPS with health check",
                "requirement": "Configure HTTPS VIP 10.10.10.10 with health monitoring",
                "expected_modules": ["/c/slb/virt"],
                "expected_params": {"vip": "10.10.10.10"}
            }
        ]
        
        for test_case in test_cases:
            self.run_test(test_case)
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n" + "=" * 80)
        print("📦 TEST CATEGORY: Edge Cases")
        print("=" * 80)
        
        test_cases = [
            {
                "name": "Invalid IP address",
                "requirement": "Create VIP 999.999.999.999",
                "expected_modules": [],
                "should_fail": True
            },
            {
                "name": "No specific parameters",
                "requirement": "Configure load balancer",
                "expected_modules": ["/c/slb/virt"],
                "expected_params": {}
            },
            {
                "name": "Multiple IPs",
                "requirement": "Setup VIPs 10.0.0.1, 10.0.0.2, 10.0.0.3",
                "expected_modules": ["/c/slb/virt"],
                "expected_params": {}
            }
        ]
        
        for test_case in test_cases:
            self.run_test(test_case)
    
    def run_test(self, test_case):
        """Run a single test case"""
        test_name = test_case['name']
        requirement = test_case['requirement']
        expected_modules = test_case.get('expected_modules', [])
        expected_params = test_case.get('expected_params', {})
        should_fail = test_case.get('should_fail', False)
        
        print(f"\n🧪 Test: {test_name}")
        print(f"   Requirement: {requirement}")
        
        try:
            # Generate configuration
            result = generate_config_from_requirement(requirement, verbose=False)
            
            if should_fail:
                if result['config'] is None:
                    self.record_pass(test_name, "Expected failure occurred")
                    return
                else:
                    self.record_fail(test_name, "Should have failed but succeeded")
                    return
            
            if not result['config']:
                self.record_fail(test_name, "No configuration generated")
                return
            
            config = result['config']
            validation = result['validation']
            
            # Check expected modules are present
            actual_modules = [m.module_path for m in config.modules]
            missing_modules = [m for m in expected_modules if m not in actual_modules]
            
            if missing_modules:
                self.record_fail(test_name, f"Missing expected modules: {missing_modules}")
                return
            
            # Check expected parameters
            for module in config.modules:
                for assignment in module.parameter_assignments:
                    param_name = assignment.parameter_name
                    if param_name in expected_params:
                        expected_value = expected_params[param_name]
                        actual_value = assignment.value
                        if str(expected_value) != str(actual_value):
                            self.record_fail(
                                test_name,
                                f"Parameter mismatch: {param_name} = {actual_value}, expected {expected_value}"
                            )
                            return
            
            # Validate configuration
            if not validation.is_valid and validation.errors:
                self.record_fail(
                    test_name,
                    f"Validation errors: {len(validation.errors)} error(s)"
                )
                return
            
            # Test passed
            self.record_pass(test_name, f"Generated {len(actual_modules)} module(s)")
            
        except Exception as e:
            self.record_fail(test_name, f"Exception: {str(e)}")
    
    def record_pass(self, test_name, message):
        """Record a passing test"""
        self.passed += 1
        self.test_results.append({
            'name': test_name,
            'status': 'PASS',
            'message': message
        })
        print(f"   ✅ PASS: {message}")
    
    def record_fail(self, test_name, message):
        """Record a failing test"""
        self.failed += 1
        self.test_results.append({
            'name': test_name,
            'status': 'FAIL',
            'message': message
        })
        print(f"   ❌ FAIL: {message}")
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Pass Rate: {pass_rate:.1f}%")
        
        if self.failed > 0:
            print(f"\n⚠️  Failed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"   • {result['name']}: {result['message']}")
        
        # Save results to file
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        results_file = output_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'passed': self.passed,
                    'failed': self.failed,
                    'pass_rate': pass_rate
                },
                'tests': self.test_results
            }, f, indent=2)
        
        print(f"\n💾 Test results saved to: {results_file}")
        print()


if __name__ == "__main__":
    tester = ConfigGenerationTester()
    tester.run_all_tests()
