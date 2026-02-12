# Deployment Variables Template Explanation

## Two-Stage Templating Architecture

This deployment uses a **two-stage templating system** to allow maximum flexibility:

### Stage 1: Jinja2 Rendering (Python → YAML)
**Template:** `labs/deployment_vars.yml`  
**Renderer:** Python with Jinja2  
**Output:** `labs/L09/deployment.yml`

### Stage 2: Mist Variable Substitution (Mist → Config)
**Template:** `labs/L09/deployment.yml`  
**Renderer:** Juniper Mist Platform  
**Output:** Final device configurations

---

## Stage 1: Jinja2 Variables (Injected by Python)

These variables are replaced **during the Python script execution** using values from your `config/env.yml` and `.env` files:

### Organization & Device Variables
```yaml
# Python injects these from env dictionary:
{{org_id}}          → Your actual org ID (e.g., "a1b2c3d4-e5f6-...")
{{ssr1_mac}}        → SSR-1 MAC address
{{ssr2_mac}}        → SSR-2 MAC address  
{{ssr3_mac}}        → SSR-3 MAC address
{{ssr4_mac}}        → SSR-4 MAC address
{{ap1_mac}}         → AP-1 MAC address
{{ex1_mac}}         → EX-1 MAC address
{{mgmt_vlan}}       → Management VLAN ID
{{vlan_1}}          → Uplink VLAN 1 ID
{{vlan_2}}          → Uplink VLAN 2 ID
{{ex_gateway}}      → Switch gateway IP
```

### Example - Before Jinja2 Rendering:
```yaml
wlans:
  - ssid: JMA_WLAN_{{org_id[-4:]}}
    enabled: True

sites:
  - info:
      name: Durham
    settings:
      vars:
        CLIENT_VLAN: {{mgmt_vlan}}
        UPLINK_VLAN_1: {{vlan_1}}
    assignments:
      edges:
        - name: SSR-1
          mac: "{{ssr1_mac}}"
```

### Example - After Jinja2 Rendering:
```yaml
wlans:
  - ssid: JMA_WLAN_3f2a
    enabled: True

sites:
  - info:
      name: Durham
    settings:
      vars:
        CLIENT_VLAN: 100
        UPLINK_VLAN_1: 101
    assignments:
      edges:
        - name: SSR-1
          mac: "02:00:00:00:00:01"
```

---

## Stage 2: Mist Variables (Injected by Mist Platform)

These variables remain **literal in the rendered YAML** and are replaced by Mist when deploying to actual devices:

### Site-Specific Variables
```yaml
# These stay as-is in labs/L09/deployment.yml:
{{LAN_PFX}}         → Replaced per-site (e.g., "10.99.99" for Durham)
{{WAN_PFX}}         → Replaced per-site (e.g., "192.168.170" for Durham)
{{WAN1_PFX}}        → Hub site WAN1 prefix
{{WAN2_PFX}}        → Hub site WAN2 prefix
{{CLIENT_VLAN}}     → Site-specific client VLAN
{{UPLINK_VLAN_1}}   → Site-specific uplink VLAN 1
{{UPLINK_VLAN_2}}   → Site-specific uplink VLAN 2
{{GW}}              → Site gateway IP
{{ROOT_PW}}         → Switch root password
```

### Double-Wrapping Syntax

To preserve Mist variables through Jinja2 rendering, we use **double-wrapping**:

```yaml
# In deployment_vars.yml (template):
ip: "{{'{{LAN_PFX}}'}}.1"
vlan_id: {{'"{{CLIENT_VLAN}}"'}}

# After Jinja2 rendering (labs/L09/deployment.yml):
ip: "{{LAN_PFX}}.1"
vlan_id: "{{CLIENT_VLAN}}"

# After Mist processes it for Durham site:
ip: "10.99.99.1"
vlan_id: "100"

# After Mist processes it for Westford site:
ip: "10.88.88.1"
vlan_id: "100"
```

---

## Why Two Stages?

### Stage 1 (Jinja2) handles:
- ✅ **Organization-wide constants** - Same across all sites
- ✅ **Device identifiers** - MAC addresses, device names
- ✅ **Account-specific values** - API keys, org IDs
- ✅ **Global settings** - VLAN IDs, shared configurations

### Stage 2 (Mist) handles:
- ✅ **Site-specific values** - Different for each location
- ✅ **Dynamic configurations** - Per-device customization
- ✅ **Network addressing** - Site-specific IP ranges
- ✅ **Deployment-time values** - Values that change per deployment

---

## Example: Complete Flow

### 1. Template (deployment_vars.yml)
```yaml
wan_edge_templates:
  - name: Durham WAN Edge Template
    sites:
      - Durham
    ip_configs:
      LAN1:
        ip: "{{'{{LAN_PFX}}'}}.1"
    port_config:
      ge-0/0/1:
        ip_config:
          ip: "{{'{{WAN_PFX}}'}}.2"

sites:
  - info:
      name: Durham
    settings:
      vars:
        LAN_PFX: 10.99.99
        WAN_PFX: 192.168.170
    assignments:
      edges:
        - mac: "{{ssr1_mac}}"
```

### 2. After Python Renders (labs/L09/deployment.yml)
```yaml
wan_edge_templates:
  - name: Durham WAN Edge Template
    sites:
      - Durham
    ip_configs:
      LAN1:
        ip: "{{LAN_PFX}}.1"
    port_config:
      ge-0/0/1:
        ip_config:
          ip: "{{WAN_PFX}}.2"

sites:
  - info:
      name: Durham
    settings:
      vars:
        LAN_PFX: 10.99.99
        WAN_PFX: 192.168.170
    assignments:
      edges:
        - mac: "02:00:00:00:00:01"
```

### 3. After Mist Deploys to Durham Site
```yaml
# Final configuration on SSR-1 device:
wan_edge_templates:
  - name: Durham WAN Edge Template
    ip_configs:
      LAN1:
        ip: "10.99.99.1"        # {{LAN_PFX}} replaced
    port_config:
      ge-0/0/1:
        ip_config:
          ip: "192.168.170.2"   # {{WAN_PFX}} replaced
```

---

## Key Patterns to Remember

### 1. Single Curly Braces → Jinja2 Rendering
```yaml
mac: "{{ssr1_mac}}"              # Replaced by Python
ssid: JMA_WLAN_{{org_id[-4:]}}   # Replaced by Python
```

### 2. Double-Wrapped → Preserved for Mist
```yaml
ip: "{{'{{LAN_PFX}}'}}.1"        # Becomes: "{{LAN_PFX}}.1"
vlan: {{'"{{CLIENT_VLAN}}"'}}    # Becomes: "{{CLIENT_VLAN}}"
```

### 3. No Wrapping → Static Values
```yaml
type: spoke                       # Always "spoke"
enabled: True                     # Always True
```

---

## Variables Injected in Your Deployment

Based on your `config/env.yml`, these Jinja2 variables are injected:

| Variable      | Type          | Example Value          | Description                    |
|---------------|---------------|------------------------|--------------------------------|
| org_id        | String (UUID) | a1b2c3d4-e5f6-7890...  | Your Mist organization ID      |
| ssr1_mac      | MAC Address   | 02:00:00:00:00:01      | Durham WAN Edge MAC            |
| ssr2_mac      | MAC Address   | 02:00:00:00:00:02      | Westford WAN Edge MAC          |
| ssr3_mac      | MAC Address   | 02:00:00:00:00:03      | Sunnyvale Hub MAC              |
| ssr4_mac      | MAC Address   | 02:00:00:00:00:04      | Cupertino Hub MAC              |
| ap1_mac       | MAC Address   | 02:00:00:00:00:0a      | Durham AP MAC                  |
| ex1_mac       | MAC Address   | 02:00:00:00:00:14      | Durham Switch MAC              |
| mgmt_vlan     | Integer       | 100                    | Management VLAN ID             |
| vlan_1        | Integer       | 101                    | Uplink VLAN 1 ID               |
| vlan_2        | Integer       | 102                    | Uplink VLAN 2 ID               |
| ex_gateway    | IP Address    | 192.168.1.1            | Switch default gateway         |

---

## Troubleshooting

### If you see `{{variable_name}}` in deployed configs:
- ✅ **Jinja2 var** → Check `env` dictionary has the value
- ✅ **Mist var** → Check site settings have the value defined

### If Jinja2 rendering fails:
- Check syntax: `{{var}}` for Jinja2, `{{'{{var}}'}}` for Mist
- Verify all variables exist in `env` dictionary
- Check for typos in variable names

### If Mist deployment fails:
- Verify site variables are configured in Site Settings
- Check that Site Variables match the template expectations
- Ensure variable names in template match Site Settings
