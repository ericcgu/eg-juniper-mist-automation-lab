# # Lab 05: Automating Day 1 Operations with Python and the Juniper Mist API
#
# ## Overview
#
# In this lab, you will prepare and execute a fully automated deployment of an enterprise site.
#
# By completing this lab, you will perform the following tasks:
#
# - Assign an EX Series switch, a SSR router, and Juniper AP to the Durham site
# - Configure the site for basic connectivity
# - Test and validate your new site

# ### Step 1.1 - Import Modules
#
# Import the following modules and objects for use in this lab:
# - `mistapi` - the Mist API Python package
# - `v1` from `mistapi.api` - shorthand for the v1 API namespace  
# - `pprint` - for formatting output
# - `load_config_from_yaml` - shared helper from our project
# - `time` - for delays where needed

# %%
import sys
from pathlib import Path

# Ensure project root is in sys.path for utils import
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import mistapi
from mistapi.api import v1 as mist
from pprint import pprint
import time

# Reload utils module to pick up changes
import importlib
import utils
importlib.reload(utils)
from utils import load_config_from_yaml, save_config_to_yaml

# ### Step 1.2 - Load Environment Variables
#
# Load configuration from:
# - `.env` file (secrets: `MIST_API_TOKEN`)
# - `config/env.yml` (non-secrets: host, org_id, MACs, IPs, VLANs)
#
# The `load_config_from_yaml()` helper merges both sources into a single dictionary.

# %%
env = load_config_from_yaml()
org_id = env['org_id']
token = env['token']
print(f"Organization ID: {org_id}")
print(f"Using token: {token[:8]}...")

# ### Step 1.3 - Setup API Session
#
# Create the `mistapi.APISession` object and run the `.login()` function.

# %%
session = mistapi.APISession(apitoken=token, host=env['host'])
session.login()


# ---
# ## Part 3: Assign and Configure the SSR-1 Edge Device
#
# In this lab part, you will assign the SSR-1 device to the Durham site and 
# configure it as a WAN Edge device.

# ### Step 3.1 - List Current Sites
#
# Before proceeding, check to see what sites are already configured.

# %%
sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
print(f"Current sites ({len(sites)}):")
for site in sites:
    print(f"  - {site['name']} (ID: {site['id']})")

# ### Step 3.2 - Create or Update Durham Site
#
# Filter the sites list to find the Durham site. If it doesn't exist, create it.
# If it does exist, update it with the correct information.

# %%
durham_sites = list(filter(lambda s: s.get("name") == "Durham", sites))
site = None
if not durham_sites:
    print("Site not found, creating new site")
    site_payload = {
        "name": "Durham",
        "address": "111 Spoke Ave, Durham, NC 27705",
        "latlng": {
            "lat": 36.020475097827116,
            "lng": -78.91700322940933
        },
        "timezone": "America/New_York",
        "country_code": "US"
    }
    site = mist.orgs.sites.createOrgSite(session, org_id=org_id, body=site_payload).data
    print(f"Created new Durham site: {site['id']}")
else:
    print("Existing site found, updating info")
    site = durham_sites[0]
    site_payload = {
        "name": "Durham",
        "address": "111 Spoke Ave, Durham, NC 27705",
        "latlng": {
            "lat": 36.020475097827116,
            "lng": -78.91700322940933
        },
        "timezone": "America/New_York",
        "country_code": "US"
    }
    site = mist.sites.sites.updateSiteInfo(session, site_id=site["id"], body=site_payload).data
    print(f"Updated existing Durham site: {site['id']}")

site_id = site['id']
pprint(site)

# ### Step 3.3 - Get Edge Devices
#
# Use the `orgs.inventory.getOrgInventory()` function to retrieve all currently 
# adopted devices of type `gateway`.

# %%
edges = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='gateway').data
print(f"Found {len(edges)} edge devices:")
for edge in edges:
    print(f"  - {edge.get('name', 'Unknown')} (MAC: {edge['mac']})")

# ### Step 3.4 - Select SSR-1 Device
#
# Filter the edges to find the SSR-1 device using its MAC address from the env file.

# %%
mac = "".join(env['ssr1_mac'].split(":"))
ssr1_edges = list(filter(lambda e: e.get('mac') == mac, edges))
edge = ssr1_edges[0] if ssr1_edges else None
if edge:
    print(f"Found SSR-1 device: {edge.get('name', 'Unknown')} (MAC: {edge['mac']})")
    pprint(edge)
else:
    print(f"SSR-1 device with MAC {mac} not found in inventory!")
    print("Available edges:")
    pprint(edges)

# ### Step 3.5 - Assign SSR-1 to Durham Site
#
# To assign a device to a site, use the `orgs.inventory.updateOrgInventoryAssignment()` function.

# %%
if edge:
    payload = {
        "op": "assign",
        "managed": True,
        "macs": [mac],
        "site_id": site['id']
    }
    response = mist.orgs.inventory.updateOrgInventoryAssignment(session, org_id=org_id, body=payload).data
    print("SSR-1 assigned to Durham site")
    pprint(response)

# ### Step 3.6 - Set SSR-1 Device Name
#
# Make sure that the SSR device for this site has the correct name of `SSR-1`.

# %%
if edge:
    payload = {'name': "SSR-1"}
    ssr1 = mist.sites.devices.updateSiteDevice(session, site_id=site['id'], device_id=edge['id'], body=payload).data
    print("SSR-1 device name updated")

# ### Step 3.7 - Create Site Variables
#
# Create the site variables needed for this deployment:
# - `LAN_PFX`: 10.99.99
# - `WAN_PFX`: 192.168.170

# %%
payload = {
    "vars": {
        "LAN_PFX": "10.99.99",
        "WAN_PFX": "192.168.170"
    }
}
settings = mist.sites.setting.updateSiteSettings(session, site_id=site['id'], body=payload).data
print("Site variables created:")
pprint(payload)

# ### Step 3.8 - Create LAN Network
#
# In the Juniper Mist API, LANs are called `networks`. Create a new network
# that references the site variables created above.

# %%
payload = {
    "name": "LAN1",
    "subnet": "{{LAN_PFX}}.0/24",
    "ip": "{{LAN_PFX}}.0",
    "prefix": "24",
    "disallow_mist_services": True,  # Access To Juniper Mist Cloud option
    "isolation": True  # "Advertise to Overlay" option (True = Do not advertise)
}
network = mist.orgs.networks.createOrgNetwork(session, org_id=org_id, body=payload).data
print("LAN1 network created:")
pprint(network)

# ### Step 3.9 - Create Internet Application
#
# Create the Internet application that will be used in the WAN Edge template.
# In the Juniper Mist API, applications are called `services`.

# %%
payload = {
    "name": "Internet",
    "type": "custom",
    "addresses": ["0.0.0.0/0"],  # This covers all IP addresses
    "specs": [
        {
            "protocol": "any"  # any, tcp, udp or icmp
        }
    ],
    "traffic_type": "default"  # Class-of-Service settings
}
app = mist.orgs.services.createOrgService(session, org_id=org_id, body=payload).data
print("Internet application created:")
pprint(app)

# ### Step 3.10 - Create WAN Edge Template
#
# Create a comprehensive WAN Edge template for the Durham site using all the
# objects defined so far.

# %%
payload = {
    "name": "Durham WAN Edge Template",
    # The ip_configs object defines connected LANs and local IP addresses for each LAN
    "ip_configs": {
        "LAN1": {
            "type": "static",
            "ip": "{{LAN_PFX}}.1"  # This gives us the .1 address on the LAN
        }
    },
    "dns_servers": ["8.8.8.8"],
    # The port_config section creates WAN objects and assigns them to device interfaces
    "port_config": {
        # The INET WAN is configured to set IP address via DHCP
        "ge-0/0/0": {
            "name": "INET",
            "usage": "wan",
            "ip_config": {
                "type": "dhcp"
            }
        },
        # The MPLS WAN configures a static IP for MPLS connection
        "ge-0/0/1": {
            "name": "MPLS", 
            "usage": "wan",
            "ip_config": {
                "type": "static",
                "ip": "{{WAN_PFX}}.2",
                "netmask": "/24",
                "gateway": "{{WAN_PFX}}.1"
            }
        },
        # Assign the LAN network to the internal interface
        "ge-0/0/2": {
            "networks": ["LAN1"],
            "usage": "lan"
        }
    },
    # path_preferences are Traffic Steering Policies
    "path_preferences": {
        "LBO": {
            "strategy": "ordered",
            "paths": [
                {
                    "name": "INET",
                    "type": "wan"
                },
                {
                    "name": "MPLS",
                    "type": "wan"
                }
            ]
        },
        "LAN": {
            "strategy": "ordered",
            "paths": [
                {
                    "type": "local",
                    "networks": ["LAN1"]
                }
            ]
        }
    },
    "dhcpd_config": {  # Configure local DHCP server on the SSR device
        "enabled": True,
        "LAN1": {
            "type": "local",
            "ip_start": "10.99.99.10",
            "ip_end": "10.99.99.98",
            "gateway": "10.99.99.1",
            "dns_servers": ["8.8.8.8"]
        }
    },
    "oob_ip_config": {  # OOB management connection from DHCP
        "type": "dhcp",
        "node1": {
            "type": "dhcp"
        }
    },
    # Service Policies are Application Policies
    "service_policies": [
        {
            "name": "Policy-1",
            "tenants": ["LAN1"],  # Tenants are Networks in the GUI
            "services": ["Internet"],  # Services are Applications in the GUI
            "action": "allow",
            "path_preference": "LBO"
        }
    ]
}

edge_template = mist.orgs.gatewaytemplates.createOrgGatewayTemplate(session, org_id=org_id, body=payload).data
print("Durham WAN Edge Template created:")
print(f"Template ID: {edge_template['id']}")

# ### Step 3.11 - Apply WAN Edge Template to Site
#
# Assign the WAN Edge template to the Durham site by updating the site info.

# %%
payload = {
    "gatewaytemplate_id": edge_template['id']
}
site = mist.sites.sites.updateSiteInfo(session, site_id=site_id, body=payload).data
print("WAN Edge template applied to Durham site")

# ---
# ## Part 4: Configure Switch Settings
#
# In this lab part you will assign the `EX-1` switch to the Durham site and 
# apply its configuration with a switch template.

# ### Step 4.1 - Get Switch Inventory
#
# Fetch a list of adopted switches within your organization.

# %%
switches = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='switch').data
print(f"Found {len(switches)} switches:")
for switch in switches:
    print(f"  - {switch.get('name', 'Unknown')} (MAC: {switch['mac']})")

# ### Step 4.2 - Select and Assign EX-1 Switch
#
# Select the correct switch from the list using the MAC address and assign it to Durham site.

# %%
mac = "".join(env['ex1_mac'].split(":"))
ex1_switches = list(filter(lambda s: s.get('mac') == mac, switches))
switch = ex1_switches[0] if ex1_switches else None
if switch:
    print(f"Found EX-1 switch: {switch.get('name', 'Unknown')} (MAC: {switch['mac']})")
    # Assign switch to Durham site
    payload = {
        "op": "assign",
        "managed": True,
        "macs": [mac],
        "site_id": site_id
    }
    response = mist.orgs.inventory.updateOrgInventoryAssignment(session, org_id=org_id, body=payload).data
    print("EX-1 assigned to Durham site")
else:
    print(f"EX-1 switch with MAC {mac} not found!")

# ### Step 4.3 - Set EX-1 Device Name
#
# Set the correct name for the switch.

# %%
if switch:
    payload = {'name': "EX-1"}
    ex1 = mist.sites.devices.updateSiteDevice(session, site_id=site_id, device_id=switch['id'], body=payload).data
    print("EX-1 device name updated")

# ### Step 4.4 - Add Switch Variables
#
# Add additional variables required for the switch configuration.

# %%
new_vars = {
    "ROOT_PW": "juniper123",
    "CLIENT_VLAN": env['mgmt_vlan'],
    "UPLINK_VLAN_1": env['vlan_1'],
    "UPLINK_VLAN_2": env['vlan_2'],
    "GW": env['ex_gateway']
}

# Get existing site settings first
settings = mist.sites.setting.getSiteSetting(session, site_id=site_id).data
old_vars = settings.get('vars', {})

# Merge old and new variables
payload = {'vars': {}}
payload['vars'] = old_vars | new_vars

# Update site settings
settings = mist.sites.setting.updateSiteSettings(session, site_id=site_id, body=payload).data
print("Switch variables added to site settings:")
pprint(new_vars)

# ### Step 4.5 - Create Switch Template
#
# Create a comprehensive switch template (network template in the API) for the Durham site.

# %%
payload = {
    # Configure VLANs (specific to lab environment)
    "networks": {
        "CLIENT_VLAN": {
            "vlan_id": "{{CLIENT_VLAN}}"
        },
        "UPLINK_VLAN_1": {
            "vlan_id": "{{UPLINK_VLAN_1}}"
        },
        "UPLINK_VLAN_2": {
            "vlan_id": "{{UPLINK_VLAN_2}}"
        }
    },
    # Port Profiles
    "port_usages": {
        "lab_uplink": {
            "mode": "trunk",
            "port_network": "default",
            "networks": [
                "CLIENT_VLAN",
                "UPLINK_VLAN_1", 
                "UPLINK_VLAN_2"
            ],
            "stp_edge": False
        },
        "wifi_hosts": {
            "mode": "access",
            "port_network": "UPLINK_VLAN_2",
            "stp_edge": True
        },
        "lab_ap": {
            "mode": "access",
            "port_network": "UPLINK_VLAN_1",
            "stp_edge": True
        },
        "desktops": {
            "mode": "trunk",
            "port_network": "default",
            "networks": [
                "CLIENT_VLAN",
                "UPLINK_VLAN_1",
                "UPLINK_VLAN_2"
            ],
            "stp_edge": True
        }
    },
    # Switch Matching Configuration
    "switch_matching": {
        "enable": True,
        "rules": [
            {
                "name": "ex-1",
                "port_config": {
                    "ge-0/0/0": {
                        "usage": "wifi_hosts"
                    },
                    "ge-0/0/1": {
                        "usage": "lab_ap"
                    },
                    "ge-0/0/22": {
                        "usage": "desktops"
                    },
                    "ge-0/0/23": {
                        "usage": "lab_uplink"
                    }
                },
                "match_name[0:4]": "EX-1"  # Match device name starting with "EX-1"
            }
        ]
    },
    # Static routes
    "extra_routes": {
        "0.0.0.0/0": {
            "via": "{{GW}}",
            "discard": False
        }
    },
    "switch_mgmt": {
        "config_revert_timer": 10,
        "root_password": "{{ROOT_PW}}"
    },
    "dns_servers": ["8.8.8.8"],
    "name": "Durham Switches"
}

switch_template = mist.orgs.networktemplates.createOrgNetworkTemplate(session, org_id=org_id, body=payload).data
print("Durham switch template created:")
print(f"Template ID: {switch_template['id']}")

# ### Step 4.6 - Apply Switch Template to Site
#
# Apply the template to the Durham site.

# %%
payload = {
    'networktemplate_id': switch_template['id']
}
site = mist.sites.sites.updateSiteInfo(session, site_id=site_id, body=payload).data
print("Switch template applied to Durham site")

# ---
# ## Part 5: Configure Wireless Network
#
# In this lab part, you will configure your wireless network.

# ### Step 5.1 - Get Access Point Inventory
#
# Fetch the list of currently adopted access points.

# %%
aps = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='ap').data
print(f"Found {len(aps)} access points:")
for ap in aps:
    print(f"  - {ap.get('name', 'Unknown')} (MAC: {ap['mac']})")

# ### Step 5.2 - Assign AP-1 to Durham Site
#
# Assign the AP to the Durham site using its MAC address.

# %%
if aps and len(aps) > 0:
    ap = aps[0]  # Take the first AP
    mac = "".join(env['ap1_mac'].split(":"))
    
    payload = {
        "op": "assign",
        "managed": True,
        "macs": [mac],
        "site_id": site_id
    }
    assignment = mist.orgs.inventory.updateOrgInventoryAssignment(session, org_id=org_id, body=payload).data
    print("AP-1 assigned to Durham site")

# ### Step 5.3 - Set AP-1 Device Name
#
# Configure the name for the AP.

# %%
if aps and len(aps) > 0:
    payload = {'name': "AP-1"}
    ap1 = mist.sites.devices.updateSiteDevice(session, site_id=site_id, device_id=ap['id'], body=payload).data
    print("AP-1 device name updated")

# ### Step 5.4 - Create RF Template
#
# Create an RF template for the Durham site optimized for the lab environment.

# %%
payload = {
    "band_24_usage": "auto",
    "country_code": "US",  # Set regulatory compliance for US
    # Only 5GHz is enabled to limit interference
    "band_5": {
        "disabled": False,
        "power": 5  # Lowest power setting to avoid interference
    },
    "band_6": {
        "disabled": True
    },
    "band_24": {
        "disabled": True
    },
    "name": "Durham RF Template"
}

rf_template = mist.orgs.rftemplates.createOrgRfTemplate(session, org_id=org_id, body=payload).data
print("Durham RF Template created:")
print(f"Template ID: {rf_template['id']}")

# ### Step 5.5 - Apply RF Template to Site
#
# RF template assignment is configured under site configuration.

# %%
payload = {
    "rftemplate_id": rf_template['id']
}
site_info = mist.sites.sites.updateSiteInfo(session, site_id=site_id, body=payload)
print("RF template applied to Durham site")

# ### Step 5.6 - Create WLAN Template
#
# Create a WLAN template for the Durham site.

# %%
payload = {
    "applies": {
        "org_id": org_id
    },
    "name": "Durham WLAN Template"
}
wlan_template = mist.orgs.templates.createOrgTemplate(session, org_id=org_id, body=payload).data
print("Durham WLAN Template created:")
print(f"Template ID: {wlan_template['id']}")

# ### Step 5.7 - Create WLAN with PSK Authentication
#
# Create a WLAN with SSID based on the org ID and PSK authentication.

# %%
payload = {
    "ssid": f"JMA_WLAN_{org_id[-4:]}",  # Use last 4 characters of org_id
    "enabled": True,
    "bands": ["5"],  # Only 5GHz
    "band_steer": False,
    "auth": {
        "type": "psk",
        "enable_mac_auth": False,
        "private_wlan": False,
        "key_idx": 1,
        "multi_psk_only": False,
        "eap_reauth": False,
        "psk": "juniper123"
    },
    "rateset": {
        "5": {
            "template": "high-density",  # High-density setting to minimize interference
            "min_rssi": 0
        }
    },
    "template_id": wlan_template['id']
}

wlan = mist.orgs.wlans.createOrgWlan(session, org_id=org_id, body=payload).data
print("WLAN created:")
print(f"SSID: {payload['ssid']}")
print(f"PSK: {payload['auth']['psk']}")

# ---
# ## Part 6: Validation and Summary
#
# Wait for configurations to apply and provide a comprehensive summary.

# ### Step 6.1 - Wait for AP Connection
#
# Wait for the AP to come online and connect to the Mist cloud.

# %%
print("Waiting for AP to connect to Mist cloud...")
ap_connected = False
for attempt in range(1, 31):  # Wait up to 15 minutes (30 * 30 seconds)
    try:
        ap_stats = mist.sites.stats.listSiteDevicesStats(session, site_id=site_id, type='ap', status='connected').data
        if len(ap_stats) > 0:
            print(f"AP is connected! (attempt {attempt})")
            ap_connected = True
            break
        else:
            print(f"Attempt {attempt}/30: AP not connected yet, waiting 30 seconds...")
            time.sleep(30)
    except Exception as e:
        print(f"Attempt {attempt}/30: Error checking AP status: {e}")
        time.sleep(30)

if not ap_connected:
    print("WARNING: AP did not connect after 15 minutes. Check your configurations.")
else:
    print("SUCCESS: AP is connected and ready!")

# ### Step 6.2 - Deployment Summary
#
# Provide a comprehensive summary of what was deployed.

# %%
print("\n" + "="*60)
print("LAB 5 DEPLOYMENT SUMMARY")
print("="*60)
print(f"Durham Site ID: {site_id}")
print(f"Durham Site Address: 111 Spoke Ave, Durham, NC 27705")
print("\nDeployed Components:")
print("------------------")
print("✓ Durham site created/updated")
print("✓ Site variables configured (LAN_PFX, WAN_PFX)")
print("✓ LAN1 network created")
print("✓ Internet application created")
print("✓ SSR-1 assigned and configured with WAN Edge template")
print("✓ EX-1 switch assigned and configured with switch template")
print("✓ AP-1 assigned and configured")
print("✓ RF template created and applied")
print(f"✓ WLAN created: {payload['ssid']}")

print("\nKey Configuration Details:")
print("-----------------------")
print("SSR-1 WAN Edge:")
print("  - ge-0/0/0: INET (DHCP)")
print("  - ge-0/0/1: MPLS (192.168.170.2/24)")
print("  - ge-0/0/2: LAN1 (10.99.99.1/24)")
print("  - DHCP Server: 10.99.99.10-98")

print("\nEX-1 Switch:")
print("  - ge-0/0/0: wifi_hosts")
print("  - ge-0/0/1: lab_ap")
print("  - ge-0/0/22: desktops")
print("  - ge-0/0/23: lab_uplink")

print(f"\nWireless:")
print(f"  - SSID: JMA_WLAN_{org_id[-4:]}")
print("  - PSK: juniper123")
print("  - Band: 5GHz only")
print("  - Power: 5 (minimum)")

if ap_connected:
    print("\n✓ All configurations deployed successfully!")
    print("✓ Access Point is connected and operational")
    print("\nTo test:")
    print("1. Connect a wireless device to the SSID")
    print("2. Verify DHCP assignment from 10.99.99.x range")
    print("3. Test internet connectivity")
else:
    print("\n⚠ Deployment completed but AP connection needs verification")
    print("Check the Mist GUI for AP status")

print("="*60)

def main():
    """
    Main function to execute the lab steps.
    Note: All lab steps are already executed above in the notebook-style format.
    """
    print("Lab 5: Automating Day 1 Operations with Python and the Juniper Mist API")
    print("All configuration steps have been completed above.")
    print("Check the deployment summary for results.")

if __name__ == "__main__":
    main()
