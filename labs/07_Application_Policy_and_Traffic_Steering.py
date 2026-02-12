# # Lab 07: Application Policy and Traffic Steering
#
# ## Overview
#
# In this lab, you'll configure application policies for the Durham site. You'll also 
# configure a guest WLAN and perform a Wi-Fi PSK rotation for your IoT devices.
#
# By completing this lab, you'll perform the following tasks:
# - Create a Guest WLAN
# - Configure application policies for the client devices in your Durham site
# - Perform a PSK rotation for your IoT devices

# ### Step 1.1 - Import Modules
#
# Import the following modules and objects for use in this lab:
# - `mistapi` - the Mist API Python package
# - `v1` from `mistapi.api` - shorthand for the v1 API namespace
# - `pprint` - for formatting output
# - `load_config_from_yaml` - shared helper from our project
# - `time` - for time-based operations
# - `random`, `string` - for generating random passwords

# %%
import mistapi
from mistapi.api import v1 as mist
import time
import random
import string
import importlib
import utils
importlib.reload(utils)
from utils import load_config_from_yaml

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
# ## Part 2: Creating a Guest WLAN
#
# In this lab part, you'll create the Guest WLAN for the Durham site.

# ### Step 2.1 - Retrieve Durham WLAN Template
#
# You'll use the existing `Durham WLAN Template` WLAN template for the new Guest WLAN.
# Use the `orgs.templates.listOrgTemplates()` function to retrieve the list of existing 
# WLAN templates, then filter to select the template you're looking for.

# %%
wlan_templates = mist.orgs.templates.listOrgTemplates(session, org_id=org_id).data
wlan_template = next(filter(lambda t: t.get('name') == 'Durham WLAN Template', wlan_templates), None)

if wlan_template:
    print(f"Found WLAN template: {wlan_template['name']} (ID: {wlan_template['id']})")
else:
    print("Durham WLAN Template not found!")
    print("Available templates:")
    for template in wlan_templates:
        print(f"  - {template.get('name', 'Unknown')}")

# ### Step 2.2 - Create Guest WLAN
#
# For this lab, you'll create a WLAN with an SSID of `JMA_Guest_XXXX` where `XXXX` is 
# the last four characters in your org ID.
#
# You'll configure this WLAN for Open Access and set the `template_id` to the ID from 
# the WLAN template you just created. You'll also set some per-client bandwidth limits:
# - Upload limit: 512kbps
# - Download limit: 1Mbps
#
# As with the corporate WLAN, you'll set the 5-GHz radio to high density mode to help 
# reduce interference.
#
# GUI Reference: `Organization > Wireless > WLAN Templates`

# %%
if wlan_template:
    payload = {
        "ssid": f"JMA_Guest_{org_id[-4:]}",
        "enabled": True,
        "bands": ["5"],
        "client_limit_up_enabled": True,
        "client_limit_up": 512,
        "client_limit_down_enabled": True,
        "client_limit_down": 1000,
        "portal": {
            "enabled": False
        },
        "auth": {
            "type": "open"
        },
        "rateset": {
            "5": {
                "template": "high-density",
                "min_rssi": 0
            }
        },
        "template_id": wlan_template['id'],
        "org_id": org_id,
        "interface": "all"
    }
    
    wlan = mist.orgs.wlans.createOrgWlan(session, org_id=org_id, body=payload).data
    print(f"Created Guest WLAN: {wlan['ssid']} (ID: {wlan['id']})")
else:
    print("Cannot create WLAN without template!")

# ### Step 2.3 - Create Guest Label
#
# You'll be using WLAN template policies to control permitted applications for users on 
# the Guest WLAN. This will require a label to match the Guest WLAN. You'll create this 
# at the organization level.
#
# These labels are known in the API as `wxtags`, so you use the 
# `orgs.wxtags.createOrgWxTag()` function to create the `Guest` label.
#
# GUI Reference: `Organization > Wireless > Labels`

# %%
if wlan:
    payload = {
        "op": "in",
        "values": [wlan['id']],
        "name": "Guest",
        "for_site": False,
        "type": "match",
        "match": "wlan_id"
    }
    
    guest_label = mist.orgs.wxtags.createOrgWxTag(session, org_id=org_id, body=payload).data
    print(f"Created Guest label: {guest_label['name']} (ID: {guest_label['id']})")

# ### Step 2.4 - Create Guest WLAN Policy Rule
#
# Now that you have your label to match the Guest WLAN, you can create a rule to match it. 
# You want to make sure that, while users on your Guest WLAN can access the internet, 
# they're not using too much of your bandwidth on potentially malicious bittorrent downloads.
#
# The Juniper Mist API knows WLAN rules as `wxrules`, so you'll use the 
# `orgs.wxrules.createOrgWxRule()` function to create a rule with an `allow` action, 
# while `bit-torrent` configured under `blocked_apps`.
#
# GUI Reference: `Organization > Wireless > WLAN Templates > Durham WLAN Template: Policy`

# %%
if guest_label and wlan_template:
    payload = {
        "src_wxtags": [guest_label['id']],
        "dst_wxtags": [],
        "enabled": True,
        "action": "allow",
        "dst_allow_wxtags": [],
        "dst_deny_wxtags": [],
        "blocked_apps": ["bit-torrent"],
        "template_id": wlan_template['id']
    }
    
    guest_rule = mist.orgs.wxrules.createOrgWxRule(session, org_id=org_id, body=payload).data
    print(f"Created Guest WLAN rule (ID: {guest_rule['id']})")
    print(f"  - Action: {guest_rule['action']}")
    print(f"  - Blocked apps: {guest_rule.get('blocked_apps', [])}")

# ---
# ## Part 3: Application Policy and Traffic Steering
#
# In this lab part, you'll configure application policies and traffic steering for client 
# devices in the Durham site.
#
# You will add several rules to the existing `Durham WAN Edge Template` to fulfill the 
# following requirements:
# - The web server at 10.99.99.130 should only be able to access the Internet to download 
#   regular updates.
# - The MQTT server at 10.99.99.131 should only be able to access the Internet to 
#   communicate with another MQTT server in the lab cloud at 192.168.10.254.
# - The Client1 device at 10.99.99.99 should be reachable from the Internet via SSH. 
#   You'll configure destination NAT for this device using the pre-translation IP of 
#   192.168.170.2 and port of 2222.
# - Other clients in the Durham site should be able to access the Internet except for the 
#   following blocked URL categories: Adult, Advertisement, Games, Malware, Violence
# - Outbound traffic to the MQTT cloud server should prefer the MPLS link.
# - All other Internet-bound traffic should use the local breakout (LBO) traffic steering 
#   path which prefers the broadband (INET) WAN link.

# ### Step 3.1 - Retrieve Durham WAN Edge Template
#
# You first need to fetch the existing WAN Edge template, which contains the application 
# policies. Use the `orgs.gatewaytemplates.listOrgGatewayTemplates()` to retrieve existing 
# templates, then filter to grab the `Durham WAN Edge Template`.

# %%
wan_templates = mist.orgs.gatewaytemplates.listOrgGatewayTemplates(session, org_id=org_id).data
wan_template = next(filter(lambda t: t.get('name') == 'Durham WAN Edge Template', wan_templates), None)

if wan_template:
    print(f"Found WAN Edge template: {wan_template['name']} (ID: {wan_template['id']})")
    print(f"Current service policies: {len(wan_template.get('service_policies', []))}")
else:
    print("Durham WAN Edge Template not found!")
    print("Available templates:")
    for template in wan_templates:
        print(f"  - {template.get('name', 'Unknown')}")

# ### Step 3.2 - Create Application Definitions
#
# You also need to create a few new applications as match conditions for the new 
# application policies:
#
# - `Blocklist`: contains blocked URL categories
# - `SoftwareUpdates`: matches the `ubuntu` category for Ubuntu system updates
# - `Cloud_MQTT`: matches a "cloud" MQTT server IP
# - `Desktop1_SSH`: matches the pre-translation IP for Client1
#
# GUI Reference: `Organization > WAN > Applications`

# %%
# Create the Blocklist application
payload = {
    "name": "Blocklist",
    "type": "app_categories",
    "app_categories": ["Adult", "Advertisement", "Games", "Malware", "Violence"],
    "app_subcategories": [],
    "traffic_type": "default"
}

blocklist = mist.orgs.services.createOrgService(session, org_id=org_id, body=payload).data
print(f"Created Blocklist application (ID: {blocklist['id']})")

# Create the SoftwareUpdates application
payload = {
    "name": "SoftwareUpdates",
    "type": "apps",
    "apps": ["ubuntu"],
    "traffic_type": "default"
}

software_updates = mist.orgs.services.createOrgService(session, org_id=org_id, body=payload).data
print(f"Created SoftwareUpdates application (ID: {software_updates['id']})")

# Create the Cloud_MQTT application
payload = {
    "name": "Cloud_MQTT",
    "type": "custom",
    "addresses": ["192.168.10.254/24"],
    "specs": [{"protocol": "any"}],
    "traffic_type": "default"
}

cloud_mqtt = mist.orgs.services.createOrgService(session, org_id=org_id, body=payload).data
print(f"Created Cloud_MQTT application (ID: {cloud_mqtt['id']})")

# Create the Desktop1_SSH application
payload = {
    "addresses": ["192.168.170.2/24"],
    "specs": [{"protocol": "tcp", "port_range": "2222-2222"}],
    "traffic_type": "default",
    "name": "Desktop1_SSH",
    "type": "custom"
}

desktop_ssh = mist.orgs.services.createOrgService(session, org_id=org_id, body=payload).data
print(f"Created Desktop1_SSH application (ID: {desktop_ssh['id']})")

# ### Step 3.3 - Create Internet Network
#
# For the destination NAT rule, you'll need to configure the Internet as a source network.
#
# GUI Reference: `Organization > WAN > Networks`

# %%
payload = {
    "isolation": True,
    "subnet": "0.0.0.0/0",
    "ip": "0.0.0.0",
    "prefix": "0",
    "disallow_mist_services": True,
    "name": "Internet"
}

internet_lan = mist.orgs.networks.createOrgNetwork(session, org_id=org_id, body=payload).data
print(f"Created Internet network (ID: {internet_lan['id']})")

# ### Step 3.4 - Retrieve LAN1 Network
#
# To match on individual clients, you need to create `User` objects for the Web and MQTT 
# servers. Users are configured as part of `Network` objects.
#
# Use the `orgs.networks.listOrgNetworks()` function to retrieve current networks and 
# filter to select the `LAN1` network.

# %%
networks = mist.orgs.networks.listOrgNetworks(session, org_id=org_id).data
network = next(filter(lambda n: n.get('name') == 'LAN1', networks), None)

if network:
    print(f"Found LAN1 network (ID: {network['id']})")
else:
    print("LAN1 network not found!")
    print("Available networks:")
    for net in networks:
        print(f"  - {net.get('name', 'Unknown')}")

# ### Step 3.5 - Add Users to LAN1 Network
#
# Now that you have the `LAN1` network object, you have to add the users under `tenants` 
# and `users`.

# %%
if network:
    web_server_1 = {"addresses": ["10.99.99.130"]}
    mqtt_server_1 = {"addresses": ["10.99.99.131"]}
    
    network['tenants'] = {
        'WEB_SERVER_1': {"addresses": ["10.99.99.130"]},
        'MQTT_SERVER_1': {"addresses": ["10.99.99.131"]}
    }
    network['users'] = []
    network['users'].append({'name': 'WEB_SERVER_1', 'addresses': web_server_1['addresses']})
    network['users'].append({'name': 'MQTT_SERVER_1', 'addresses': mqtt_server_1['addresses']})
    
    print("Added users to LAN1 network:")
    print("  - WEB_SERVER_1: 10.99.99.130")
    print("  - MQTT_SERVER_1: 10.99.99.131")

# ### Step 3.6 - Configure Destination NAT for Client1 SSH Access
#
# NAT configurations are also part of the Network object. Add the Client1 SSH destination 
# NAT configuration to the `network` object.
#
# Because this destination NAT configuration is applied to traffic from the Internet, 
# you'll apply it to the underlay. You also need to add the configuration under 
# `internet_access`.
#
# Finally, use the updated `network` object to update the Juniper Mist network using the 
# `orgs.networks.updateOrgNetwork()` function.
#
# GUI Reference: `Organization > WAN > Networks: LAN1 USERS, DESTINATION NAT`

# %%
if network:
    network['destNats'] = []
    network['destNats'].append({
        "name": "Desktop1_SSH",
        "external_ip": "192.168.170.2",
        "external_port": "2222",
        "internal_ip": "10.99.99.99",
        "port": "22",
        "applies_to": "Underlay"
    })
    
    internet_access = {
        "static_nat": {},
        "destination_nat": {
            "192.168.170.2:2222": {
                "name": "Desktop1_SSH",
                "internal_ip": "10.99.99.99",
                "port": "22"
            }
        }
    }
    network['internet_access'] = internet_access
    
    network = mist.orgs.networks.updateOrgNetwork(
        session, 
        org_id=org_id, 
        network_id=network['id'], 
        body=network
    ).data
    
    print("Updated LAN1 network with destination NAT:")
    print("  - External: 192.168.170.2:2222 -> Internal: 10.99.99.99:22")

# ### Step 3.7 - Update WAN Edge Template with Application Policies
#
# Now that you've laid the groundwork, you can finally put everything in motion.
#
# You already saved the current WAN Edge template to `wan_template`, so you just need to 
# update `service_policies` with your new policies. You can also add your new traffic 
# steering configuration here to direct traffic to the MQTT server through `LBO_MPLS` 
# which prefers the MPLS path over the INET path.
#
# You can then update the template with the 
# `orgs.gatewaytemplates.updateOrgGatewayTemplate()` function.
#
# GUI Reference: `Organization > WAN > WAN Edge Templates > Durham WAN Edge Template: Application Policies`

# %%
if wan_template:
    # Policy 2: Deny web server from accessing Internet
    wan_template['service_policies'].append({
        "name": "Policy-2",
        "tenants": ["WEB_SERVER_1.LAN1"],
        "services": ["Internet"],
        "action": "deny",
        "idp": {"enabled": False},
        "local_routing": True
    })
    
    # Policy 3: Allow web server software updates via LBO
    wan_template['service_policies'].append({
        "name": "Policy-3",
        "tenants": ["WEB_SERVER_1.LAN1"],
        "services": ["SoftwareUpdates"],
        "action": "allow",
        "path_preference": "LBO",
        "idp": {"enabled": False}
    })
    
    # Policy 4: Deny MQTT server from accessing Internet
    wan_template['service_policies'].append({
        "name": "Policy-4",
        "tenants": ["MQTT_SERVER_1.LAN1"],
        "services": ["Internet"],
        "action": "deny",
        "idp": {"enabled": False},
        "local_routing": True
    })
    
    # Policy 5: Allow MQTT server to cloud MQTT via LBO_MPLS
    wan_template['service_policies'].append({
        "name": "Policy-5",
        "tenants": ["MQTT_SERVER_1.LAN1"],
        "services": ["Cloud_MQTT"],
        "action": "allow",
        "path_preference": "LBO_MPLS",
        "idp": {"enabled": False}
    })
    
    # Policy 6: Allow SSH access to Desktop1 from Internet
    wan_template['service_policies'].append({
        "name": "Policy-6",
        "tenants": ["Internet"],
        "services": ["Desktop1_SSH"],
        "action": "allow",
        "path_preference": "LAN"
    })
    
    # Add LBO_MPLS path preference
    if 'path_preferences' not in wan_template:
        wan_template['path_preferences'] = {}
    
    wan_template['path_preferences']['LBO_MPLS'] = {
        "strategy": "ordered",
        "paths": [
            {"name": "MPLS", "type": "wan"},
            {"name": "INET", "type": "wan"}
        ]
    }
    
    # Update the template
    wan_template = mist.orgs.gatewaytemplates.updateOrgGatewayTemplate(
        session, 
        org_id=org_id, 
        gatewaytemplate_id=wan_template['id'], 
        body=wan_template
    ).data
    
    print("Updated Durham WAN Edge Template with application policies:")
    print(f"  - Total service policies: {len(wan_template.get('service_policies', []))}")
    print(f"  - Path preferences: {list(wan_template.get('path_preferences', {}).keys())}")

# ### Step 3.8 - Validation (Manual GUI Check)
#
# To verify the configuration:
# 1. Open a web browser and navigate to `manage.mist.com`
# 2. Login with your provided credentials
# 3. Select your assigned organization
# 4. Navigate to `WAN Edges > WAN Edges`
# 5. Select `Durham` from the `site` dropdown
# 6. Click on your `SSR-1` device
# 7. Scroll down to `Traffic Steering` and `Application Policies` sections
# 8. Confirm that your new configurations have been applied

print("\n" + "="*80)
print("Part 3 Complete: Application Policy and Traffic Steering")
print("="*80)
print("\nManual Validation Required:")
print("  1. Open browser and navigate to manage.mist.com")
print("  2. Go to: WAN Edges > WAN Edges > Durham > SSR-1")
print("  3. Verify Traffic Steering and Application Policies sections")
print("="*80 + "\n")

# ---
# ## Part 4: PSK Management
#
# In this lab part, you'll update the WLAN used by your IoT devices to support multiple 
# PSKs with cloud PSK management. You'll then lay the groundwork to rotate your keys and 
# automatically update them on your IoT devices.

# ### Step 4.1 - Retrieve Organization WLANs
#
# To enable PSK management for your IoT devices, you'll first need to modify the WLAN 
# settings for the internal and Guest WLANs.
#
# You'll retrieve the list of WLANs using the `orgs.wlans.listOrgWlans()` function.

# %%
wlans = mist.orgs.wlans.listOrgWlans(session, org_id=org_id).data
print(f"Found {len(wlans)} WLANs:")
for wlan_item in wlans:
    print(f"  - {wlan_item.get('ssid', 'Unknown')} (ID: {wlan_item['id']})")

# ### Step 4.2 - Retrieve Internal WLAN
#
# You'll deal with the internal WLAN first, so use filter to select the `JMA_WLAN_XXXX` 
# WLAN. Recall that the `XXXX` are the last 4 characters of your Org ID.

# %%
org_wlan = next(filter(lambda w: w.get('ssid') == f"JMA_WLAN_{org_id[-4:]}", wlans), None)

if org_wlan:
    print(f"Found internal WLAN: {org_wlan['ssid']} (ID: {org_wlan['id']})")
else:
    print(f"Internal WLAN JMA_WLAN_{org_id[-4:]} not found!")

# ### Step 4.3 - Enable Cloud PSK for Internal WLAN
#
# Now that you have the WLAN object for the `JMA_WLAN_XXXX` WLAN, you can modify the 
# appropriate settings to enable the following:
# - Multiple passphrases with Cloud PSK
# - Default PSK: `juniper123`
# - Configure as a personal WLAN
#
# After making the modifications to the `org_wlan` object, use the 
# `orgs.wlans.updateOrgWlan()` function to update the existing WLAN.
#
# GUI Reference: `Organization > Wireless > WLAN Templates > Durham WLAN Template: WLANs > JMA_WLAN_XXXX`

# %%
if org_wlan:
    org_wlan['dynamic_psk'] = {
        'enabled': True,
        'source': 'cloud_psks',
        'default_psk': 'juniper123',
        'private_wlan': True
    }
    
    org_wlan = mist.orgs.wlans.updateOrgWlan(
        session, 
        org_id=org_id, 
        wlan_id=org_wlan['id'], 
        body=org_wlan
    ).data
    
    print("Updated internal WLAN with Cloud PSK:")
    print(f"  - SSID: {org_wlan['ssid']}")
    print(f"  - Dynamic PSK enabled: {org_wlan.get('dynamic_psk', {}).get('enabled', False)}")
    print(f"  - PSK source: {org_wlan.get('dynamic_psk', {}).get('source', 'N/A')}")

# ### Step 4.4 - Enable Cloud PSK for Guest WLAN
#
# Now you'll do the same with the Guest WLAN. In the case of the Guest WLAN, you also 
# want to change from open access authentication to PSK authentication.

# %%
if wlan:  # wlan variable from Part 2
    guest_wlan = next(filter(lambda w: w.get('ssid') == f"JMA_Guest_{org_id[-4:]}", wlans), None)
    
    if guest_wlan:
        guest_wlan['dynamic_psk'] = {
            'enabled': True,
            'source': 'cloud_psks',
            'default_psk': 'juniper123',
            'private_wlan': True
        }
        guest_wlan['auth'] = {
            'type': 'psk',
            'psk': 'juniper123'
        }
        
        guest_wlan = mist.orgs.wlans.updateOrgWlan(
            session, 
            org_id=org_id, 
            wlan_id=guest_wlan['id'], 
            body=guest_wlan
        ).data
        
        print("Updated Guest WLAN with Cloud PSK:")
        print(f"  - SSID: {guest_wlan['ssid']}")
        print(f"  - Auth type: {guest_wlan.get('auth', {}).get('type', 'N/A')}")
        print(f"  - Dynamic PSK enabled: {guest_wlan.get('dynamic_psk', {}).get('enabled', False)}")

# ### Step 4.5 - Create Random Password Generator Function
#
# This new multiple PSK setup won't do much good without some PSKs, so let's create some. 
# You'll generate the PSKs as random strings to include special characters, numbers, and 
# letters. To do so, create a utility function called `random_password()` that generates 
# such a password of a defined length.

# %%
def random_password(length):
    """Generate a random password with letters, digits, and special characters."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# Test the function
test_password = random_password(12)
print(f"Generated test password: {test_password}")

# ### Step 4.6 - Generate and Create PSKs
#
# Time to generate the PSKs. You'll create two PSKs for two roles: IoT and Guest. 
# The IoT role will be assigned to the following clients:
# - wifi-client-1
# - wifi-client-2
# - wifi-client-3
#
# The Guest role will be assigned to wifi-client-4.
#
# For now, you'll set the PSKs to expire in 2 hours.
#
# Use the `random_password()` function to generate each key, then the 
# `orgs.psks.createOrgPsk()` function to add it to the Juniper Mist cloud.
#
# GUI Reference: `Organization > Wireless > Pre-Shared Keys`

# %%
if org_wlan:
    # Generate passphrases
    iot_passphrase = random_password(12)  # create 12 character psks
    guest_passphrase = random_password(12)
    psk_expiry_time = time.time() + (60 * 60 * 2)  # Time is measured in seconds
    
    # Create IoT PSK
    payload = {
        'usage': 'multiple',
        'name': 'iot-key-1',
        'ssid': org_wlan['ssid'],
        'passphrase': iot_passphrase,
        'role': 'IoT',
        'expire_time': psk_expiry_time
    }
    
    iot_psk = mist.orgs.psks.createOrgPsk(session, org_id=org_id, body=payload).data
    print("Created IoT PSK:")
    print(f"  - Name: {iot_psk['name']}")
    print(f"  - SSID: {iot_psk['ssid']}")
    print(f"  - Role: {iot_psk.get('role', 'N/A')}")
    print(f"  - Passphrase: {iot_passphrase}")
    
    # Create Guest PSK
    if guest_wlan:
        payload = {
            'usage': 'multiple',
            'name': 'guest-key-1',
            'ssid': guest_wlan['ssid'],
            'passphrase': guest_passphrase,
            'role': 'Guest',
            'expire_time': psk_expiry_time
        }
        
        guest_psk = mist.orgs.psks.createOrgPsk(session, org_id=org_id, body=payload).data
        print("\nCreated Guest PSK:")
        print(f"  - Name: {guest_psk['name']}")
        print(f"  - SSID: {guest_psk['ssid']}")
        print(f"  - Role: {guest_psk.get('role', 'N/A')}")
        print(f"  - Passphrase: {guest_passphrase}")

# ### Step 4.7 - PSK Deployment Logic (Conceptual)
#
# In a real deployment, you would need to implement logic to deploy these PSKs to your 
# IoT devices. The basic logic would be:
#
# 1. Check for any PSKs matching the given device's defined role
# 2. If there are any permanent PSKs, choose the key most recently created and use it
# 3. If there are no permanent PSKs, choose the temporary PSK with the latest expiry time
# 4. Deploy the selected PSK to the device
#
# Note: This step requires device-specific API integration (e.g., SSH, API) to configure 
# the Wi-Fi settings on each IoT device. This is typically done via configuration 
# management tools like Ansible, or custom scripts depending on your device types.

print("\n" + "="*80)
print("Part 4 Complete: PSK Management")
print("="*80)
print("\nNext Steps for PSK Deployment:")
print("  1. Implement device-specific configuration scripts")
print("  2. Use configuration management tools (Ansible, etc.)")
print("  3. Schedule automated PSK rotation")
print("  4. Monitor PSK expiry and device connectivity")
print("="*80 + "\n")

# ---
# ## Lab Complete
#
# You have successfully completed Lab 07: Application Policy and Traffic Steering!
#
# Summary of completed tasks:
# - Created a Guest WLAN with bandwidth limits and application policies
# - Configured application policies for web and MQTT servers
# - Set up traffic steering preferences (LBO and LBO_MPLS)
# - Configured destination NAT for SSH access
# - Enabled Cloud PSK management for WLANs
# - Generated and deployed PSKs with role-based access

print("\n" + "="*80)
print("LAB 07 COMPLETE")
print("="*80)
print("\nSummary:")
print("  ✓ Guest WLAN created with application policies")
print("  ✓ Application policies configured for Durham site")
print("  ✓ Traffic steering configured (LBO, LBO_MPLS)")
print("  ✓ Destination NAT configured for SSH access")
print("  ✓ Cloud PSK management enabled")
print("  ✓ IoT and Guest PSKs created")
print("\nRefer to the Juniper Mist GUI for validation and monitoring.")
print("="*80 + "\n")
