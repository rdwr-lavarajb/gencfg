# Phase 2 Quick Reference

## Key Decisions

| Decision | Choice |
|----------|--------|
| AI Provider | OpenAI GPT-4 |
| Placeholder Style | Descriptive: `{{management_ip_address}}` |
| Template Strategy | One template with all optional params |
| Default Threshold | 70% occurrence |
| AI Call Strategy | One call per module path (batch all instances) |

## Parameter Type Map

| Type | Example Value | Validation |
|------|--------------|------------|
| `ipv4_address` | `10.250.4.26` | IPv4 format |
| `ipv4_netmask` | `255.255.255.0` | Valid netmask |
| `integer` | `818` | Numeric |
| `port` | `1159` | 1-65535 |
| `flag` | `ena`, `dis` | Fixed options |
| `enum` | `v4`, `v6` | Fixed options |
| `quoted_string` | `"server_name"` | Quoted text |
| `vlan_id` | `818` | 1-4094 |

## Module Categories

- `system_management` - Users, access, management interface
- `network_layer2` - VLANs, ports, spanning tree
- `network_layer3` - Interfaces, routing, gateways
- `load_balancing` - Virtual/real servers, groups, services
- `security_ssl` - Certificates, SSL policies
- `security_access` - SNMP, SSH, authentication
- `monitoring` - Syslog, NTP, health checks
- `high_availability` - Sync, floating IPs
- `application` - Scripts, caching, compression

## Special Handling

### Certificates
```json
{
  "certificate_content": {
    "type": "pem_certificate",
    "preserve": "exact",
    "description": "PEM-encoded certificate (preserve formatting)"
  }
}
```

### Scripts
```json
{
  "script_content": {
    "type": "tcl_script",
    "preserve": "exact",
    "description": "TCL script body (preserve formatting)"
  }
}
```

## AI Prompt Pattern

```
Input: Module examples + detected patterns
Output: JSON with {
  description, category, tags,
  parameters: {semantic names + descriptions},
  dependencies: {requires, required_by}
}
```

## Default Value Rules

- **≥70%**: Set as default
- **50-69%**: Mark as "common" but no default
- **<50%**: No default

## Output Structure

```
data/
└── templates/
    ├── templated_modules_YYYYMMDD_HHMMSS.json
    ├── statistics.json
    └── categories.json
```

## Cost Estimate

~$2.50 per full processing run (27 modules with GPT-4)

## Implementation Order

1. Value Extractor (Python)
2. AI Analyzer (OpenAI)
3. Template Generator (Python)
4. Default Calculator (Python)
5. Storage (Python)
