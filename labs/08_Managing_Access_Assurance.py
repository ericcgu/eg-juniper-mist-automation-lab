# # Lab 08: Managing Access Assurance
#
# ## Overview
#
# In this lab, you will go through the steps required to connect Wi-Fi clients to a 
# local network using Juniper Mist Access Assurance with a public key infrastructure (PKI).
#
# By completing this lab, you will perform the following tasks:
# - Verify the Durham site in Juniper Mist
# - Create a WLAN with EAP-TLS
# - Create authentication labels (NAC tags)
# - Create an authentication policy (NAC rule)
# - Install the necessary client certificates and build the wireless clients
# - Connect the wireless clients to the WLAN using Juniper Mist Access Assurance with EAP-TLS
# - Troubleshoot a client that is not able to authenticate using the Mist API

# ---
# ## Part 1: Configuring the Site
#
# In this lab you will use your Durham site to implement Access Assurance.

# ### Step 1.1 - Import Modules
#
# Import the following modules and objects for use in this lab:
# - `mistapi` - the Mist API Python package
# - `v1` from `mistapi.api` - shorthand for the v1 API namespace
# - `pprint` - for formatting output
# - `load_config_from_yaml` - shared helper from our project

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

# ### Step 1.4 - List Existing Sites
#
# Before proceeding, check to see what sites are already configured.
#
# Run the `orgs.sites.listOrgSites()` function to retrieve a list of current sites.
#
# > NOTE: The `mistapi` session object returns API responses as an instance of the 
# > `APIResponse` class. For simplicity, you'll usually just grab the `.data` attribute,
# > which contains the response JSON.

# %%
sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
print(f"Found {len(sites)} site(s)")
for site in sites:
    print(f"  - {site.get('name', 'Unknown')} (ID: {site.get('id', 'N/A')})")

# ### Step 1.5 - Find or Create Durham Site
#
# Filter the `sites` list to find just the Durham site. Depending on whether you've done
# all the previous labs, this may or may not already exist.
#
# After filtering, check if it was found. If the site does not exist yet, use 
# `orgs.sites.createOrgSite()` to create it. If it does exist, use 
# `sites.sites.updateSiteInfo()` to update the name on the existing site.
#
# GUI: `Organization > Site Configuration > Sites`

# %%
site = next(filter(lambda s: s.get('name') == 'Durham', sites), None)

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

if site is None:
    print("Site not found, creating new site")
    site = mist.orgs.sites.createOrgSite(session, org_id=org_id, body=site_payload).data
    print(f"Created Durham site with ID: {site['id']}")
else:
    print("Existing site found, updating info")
    site = mist.sites.sites.updateSiteInfo(session, site_id=site["id"], body=site_payload).data
    print(f"Updated Durham site with ID: {site['id']}")

site_id = site['id']

# ---
# ## Part 2: Configuring the WLAN
#
# For this lab, you'll create a single WLAN with an SSID of `JMA_AA_WLAN_XXXX` where 
# `XXXX` is the last four characters in your org ID. You will use the existing 
# `Durham WLAN Template` and add the WLAN to the template.
#
# > **Note:** The code below automatically creates this name from the `org_id` variable.

# ### Step 2.1 - Retrieve Durham WLAN Template
#
# Get the Durham WLAN template using built-in Python filter.

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

# ### Step 2.2 - Create WLAN with WPA3-Enterprise and Mist NAC
#
# You'll enable WPA3-Enterprise security using Mist Auth as the authentication server and
# set the `template_id` to the ID from the WLAN template. Pass this payload to the 
# `orgs.wlans.createOrgWlan()` function to define the WLAN.
#
# The WLAN will utilize:
# - 5GHz radio band
# - WPA3 EAP type
# - Mist NAC authentication enabled
#
# GUI: `Organization > Wireless: WLAN Templates > Durham WLAN Template`

# %%
payload = {
    # The [-4:] syntax selects the last 4 characters from the org_id string
    "ssid": f"JMA_AA_WLAN_{org_id[-4:]}",
    "enabled": True,
    # This WLAN will run only on 5GHz
    "bands": ["5"],
    "band_steer": False,
    "auth": {
        # WPA3-Enterprise with EAP-TLS
        "type": "eap",
        "enable_mac_auth": False,
        "private_wlan": False,
        "key_idx": 1,
        "multi_psk_only": False,
        "eap_reauth": False,
        "pairwise": ["wpa3"]
    },
    "mist_nac": {
        # Authentication Servers: Mist Auth
        "enabled": True
    },
    "rateset": {
        "5": {
            # High-density setting for transmit rate to minimize interference
            "template": "high-density",
            "min_rssi": 0
        }
    },
    "template_id": wlan_template['id']
}

wlan = mist.orgs.wlans.createOrgWlan(session, org_id=org_id, body=payload).data
print(f"Created WLAN: {wlan['ssid']} (ID: {wlan['id']})")

# ---
# ## Part 3: Configuring Authentication Policy
#
# In this lab part, you will configure an authentication policy using labels and rules.
# As you recall, the order-of-events is important when configuring complex items in 
# Juniper Mist. Before you can create and apply a NAC rule (Auth Policy), you must first 
# create a NAC tag (Auth Policy Label) to use for the policy.
#
# > **Note:** The GUI refers to policies as "Auth Policies" while the API endpoint is 
# > "NAC rule". Similarly, the GUI refers to labels as "Auth Policy Labels" while the 
# > API endpoint is "NAC tag".

# ### Step 3.1 - Check Existing NAC Rules
#
# Check the organization for any existing NAC rules (Auth Policies).
#
# GUI: `Organization > Auth Policies`

# %%
nac_rules = mist.orgs.nacrules.listOrgNacRules(session, org_id=org_id).data
print(f"Found {len(nac_rules)} existing NAC rule(s)")
for rule in nac_rules:
    print(f"  - {rule.get('name', 'Unknown')} (ID: {rule.get('id', 'N/A')})")

# ### Step 3.2 - Check Existing NAC Tags
#
# Check the organization for any existing NAC tags (Auth Policy Labels).
#
# GUI: `Organization > Access: Auth Policy Labels`

# %%
nac_tags = mist.orgs.nactags.listOrgNacTags(session, org_id=org_id).data
print(f"Found {len(nac_tags)} existing NAC tag(s)")
for tag in nac_tags:
    print(f"  - {tag.get('name', 'Unknown')} (ID: {tag.get('id', 'N/A')})")

# ### Step 3.3 - Create NAC Tag (Auth Policy Label)
#
# Create a NAC tag (Auth Policy Label) named `AJMA-label`. This label will have a label 
# type of `Certificate Attribute`. The label values will be assigned `Common Name (CN)` 
# (from the certificate) and `*ajma*`.
#
# Using this label, applied to the authentication policy, the authentication process will 
# inspect all authentication attempts to match the common name value within the certificate 
# for the text string that includes anything before and after `ajma`.
#
# Example response:
# ```json
# {
#   "values": ["*ajma*"],
#   "id": "0cc56714-1176-4a37-b2c2-17784176373b",
#   "name": "AJMA-label",
#   "org_id": "3f12cb79-fb5e-4d4b-bfac-118d364f32d6",
#   "created_time": 1760989350,
#   "modified_time": 1760989350,
#   "type": "match",
#   "match": "cert_cn"
# }
# ```
#
# Make note of the `id`, you'll need that when you create your policy.
#
# API Reference: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/orgs/nac-tags/create-org-nac-tag

# %%
payload = {
    'values': ['*ajma*'],
    'name': 'AJMA-label',
    'type': 'match',
    'match': 'cert_cn'
}
ajma_label = mist.orgs.nactags.createOrgNacTag(session, org_id=org_id, body=payload).data
print(f"Created NAC tag: {ajma_label['name']} (ID: {ajma_label['id']})")
print(f"  Matches cert_cn: {ajma_label['values']}")

# ### Step 3.4 - Create NAC Rule (Auth Policy)
#
# With the labels created, you can now create the authentication policy called 
# `AJMA-Cert-Policy`. The policy will match on three criteria:
# - The `AJMA-label` NAC tag that matches on the term `*ajma*` within the common name of 
#   the certificate
# - The `Auth Type` (EAP-TLS)
# - The `Port Types` (Wireless)
#
# To build the policy, you define the matching criteria, policy action, and policy order.
#
# The first section configures the match criteria, including the `nactags` field which 
# references the UUID of the label you created in the previous step. The second section 
# defines the policy action (`allow`), the name of the policy, whether to enable it, and 
# the order it should be evaluated.
#
# Keep in mind, the `Last Rule` is an implicit `All Users` having `Network Access Denied`.
#
# GUI: `Organization > Auth Policies`
#
# API Reference: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/orgs/nac-rules/create-org-nac-rule

# %%
payload = {
    'matching': {
        'auth_type': 'eap-tls',
        'port_types': ['wireless'],
        'nactags': [ajma_label['id']]
    },
    'apply_tags': [],
    'action': 'allow',
    'enabled': True,
    'name': 'AJMA-Cert-Policy',
    'order': 0
}
ajma_rule = mist.orgs.nacrules.createOrgNacRule(session, org_id=org_id, body=payload).data
print(f"Created NAC rule: {ajma_rule['name']} (ID: {ajma_rule['id']})")
print(f"  Action: {ajma_rule['action']}")
print(f"  Order: {ajma_rule['order']}")
print(f"  Enabled: {ajma_rule['enabled']}")

# ---
# ## Part 4: Installing the Necessary Certificates
#
# In this lab you will get the Juniper Mist certificate for your organization. You will 
# also upload the AJMA certificate authority (CA) certificate to Juniper Mist. Finally, 
# you will run the Python automation to copy and install the clients' AJMA certificates 
# and keys on each respective client. Once complete, the clients will be able to 
# authenticate to the WPA3-Enterprise WLAN.

# ### Step 4.1 - Get Juniper Mist CA Certificate
#
# Get the Juniper Mist CA cert from your org and save it to a file.
#
# GUI: `Organization > Access: Certificates > View Mist Certificate`
#
# API Reference: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/orgs/cert/list-org-certificates

# %%
# Create directory for certificates if it doesn't exist
cert_dir = project_root / 'labs' / 'L08'
cert_dir.mkdir(parents=True, exist_ok=True)

certs = mist.orgs.cert.listOrgCertificates(session, org_id=org_id).data
mist_ca_path = cert_dir / 'mist-ca.crt'
with open(mist_ca_path, 'w') as f:
    f.write(certs['cert'])

print(f"Saved Mist CA certificate to: {mist_ca_path}")
print(f"Certificate expires: {certs.get('expiry', 'Unknown')}")

# ### Step 4.2 - Upload Client CA Certificate
#
# Next, you need to add the CA cert for your clients to authenticate to for NAC. The 
# client CA certificate is a file named `AJMA-CA_cert.crt`. The contents of the cert file 
# will be added to your organization as a certificate authority.
#
# > **Note:** The client CA cert, client cert, and client key have already been created.
# > They reside on the filesystem and will be automatically added to each wireless client 
# > in a later step of this lab. For this lab environment, these files should be placed 
# > in the `labs/L08/` directory.
#
# GUI: `Organization > Access: Certificates`
#
# API Reference: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/orgs/setting/update-org-settings

# %%
ajma_certs = mist.orgs.setting.getOrgSettings(session, org_id=org_id).data

# Read the AJMA CA certificate
ajma_ca_cert_path = cert_dir / 'AJMA-CA_cert.crt'
try:
    with open(ajma_ca_cert_path, 'r') as f:
        ajma_ca_cert = f.read()
    
    # Add the CA certificate to the organization settings
    if 'mist_nac' in ajma_certs.keys():
        if 'cacerts' not in ajma_certs['mist_nac']:
            ajma_certs['mist_nac']['cacerts'] = []
        ajma_certs['mist_nac']['cacerts'].append(ajma_ca_cert)
    else:
        ajma_certs['mist_nac'] = {'cacerts': [ajma_ca_cert]}
    
    org_settings = mist.orgs.setting.updateOrgSettings(session, org_id=org_id, body=ajma_certs).data
    print("Uploaded AJMA CA certificate to organization")
    print(f"Organization now has {len(org_settings.get('mist_nac', {}).get('cacerts', []))} CA cert(s)")
except FileNotFoundError:
    print(f"ERROR: AJMA CA certificate not found at: {ajma_ca_cert_path}")
    print("Please place the AJMA-CA_cert.crt file in the labs/L08/ directory")

# ### Step 4.3 - Create Wi-Fi Client Containers with Terraform
#
# > **MANUAL STEP REQUIRED:**
# >
# > Before you test out the Wi-Fi clients, you need to create and configure them. In the
# > lab environment, containers are used as Wi-Fi clients, which are provisioned and 
# > managed using Terraform.
# >
# > The following steps are environment-specific and may not be applicable to your setup:
# > 1. Copy Terraform providers configuration
# > 2. Generate Terraform configuration from Jinja2 templates
# > 3. Run `terraform init -upgrade`
# > 4. Run `terraform apply -auto-approve`
# >
# > This step may take up to 5 minutes to complete.
# >
# > A successful result should look similar to:
# > `Apply complete! Resources: 20 added, 0 changed, 0 destroyed.`
# >
# > If using a different environment, you'll need to adapt the client provisioning process
# > to your specific infrastructure.

# %%
# This cell is intentionally left as a comment block for manual Terraform operations
# 
# In the original lab environment, this would:
# 1. Connect to LXD host via SSH
# 2. Enumerate available wireless interfaces
# 3. Generate Terraform configuration using Jinja2 templates
# 4. Initialize and apply Terraform to create 4 wireless client containers
#
# For a production environment, replace this with your client provisioning logic.

print("=" * 60)
print("MANUAL STEP: Provision Wi-Fi client devices")
print("=" * 60)
print("In the lab environment, this involves:")
print("  1. Running Terraform to create 4 LXD containers (wifi-client-1 through 4)")
print("  2. Each container gets a wireless interface and client certificates")
print("  3. Certificates should be named: AJMA-wifi-1.crt, AJMA-wifi-1.pem, etc.")
print("")
print("For your environment, ensure you have:")
print("  - 4 Wi-Fi capable test devices or VMs")
print("  - Client certificates installed (AJMA-wifi-{1-4}.crt/.pem)")
print("  - WPA supplicant or equivalent configuration capability")
print("=" * 60)

# ---
# ## Part 5: Connecting Wi-Fi Clients Using Mist Access Assurance
#
# Now that you've installed the certificates and configured the wireless clients, test 
# their connectivity to your WLAN.

# ### Step 5.1 - Connect Wireless Clients
#
# > **MANUAL STEP REQUIRED:**
# >
# > In the lab environment, this step involves:
# > 1. Configuring wpa_supplicant.conf on each container with EAP-TLS settings
# > 2. Installing CA certificates on each container
# > 3. Starting wpa_supplicant to connect to the WLAN
# > 4. Running DHCP to obtain IP addresses
# > 5. Configuring routing tables
# > 6. Testing connectivity with ping
# >
# > The code below involves Python libraries (pylxd) for interfacing with LXC containers.
# > In a real-world environment, you would configure your actual wireless clients with 
# > the following EAP-TLS settings:
# >
# > - SSID: JMA_AA_WLAN_{last 4 of org_id}
# > - Security: WPA3-Enterprise
# > - EAP Type: TLS
# > - CA Certificate: System CA or Mist CA
# > - Client Certificate: AJMA-wifi-{1-4}.crt
# > - Private Key: AJMA-wifi-{1-4}.pem
# > - Private Key Password: lab123 (or your configured password)
# > - Identity: ajma-wifi-{1-4}
# >
# > **Expected Results:**
# > - wifi-client-1, 2, 3: Should successfully authenticate and connect
# > - wifi-client-4: Should FAIL authentication (intentional for troubleshooting practice)

# %%
ssid = f"JMA_AA_WLAN_{org_id[-4:]}"

print("=" * 60)
print("MANUAL STEP: Connect Wi-Fi clients to the WLAN")
print("=" * 60)
print(f"SSID: {ssid}")
print("Security: WPA3-Enterprise (EAP-TLS)")
print("")
print("Configure each client (1-4) with:")
print("  - EAP Type: TLS")
print("  - Identity: ajma-wifi-{1-4}")
print("  - Client Certificate: AJMA-wifi-{1-4}.crt")
print("  - Private Key: AJMA-wifi-{1-4}.pem")
print("  - Private Key Password: lab123")
print("  - CA Certificate: System CA store (with Mist and AJMA CA installed)")
print("")
print("Expected authentication results:")
print("  ✓ wifi-client-1, 2, 3: Should authenticate successfully")
print("  ✗ wifi-client-4: Should FAIL (invalid certificate)")
print("=" * 60)

# ### Step 5.2 - Check Client Connection Status
#
# You can verify client connectivity by checking how many clients are currently connected 
# to the Durham site. This uses the `distinct` parameter to display the status of the 
# client connections.
#
# Expected results:
# ```json
# {
#   'results': [
#     {'last_status': 'permitted', 'count': 2},
#     {'last_status': 'denied', 'count': 1},
#     {'last_status': 'session_started', 'count': 1}
#   ],
#   'limit': 10,
#   'distinct': 'last_status',
#   'total': 3
# }
# ```
#
# Results with `session_started` or `session_stopped` indicate successful connections.
# Only 1 client should show `denied` status.
#
# API Reference: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/sites/clients/nac/count-site-nac-clients

# %%
import time
print("Waiting 30 seconds for clients to connect...")
time.sleep(30)

clients_con = mist.sites.nac_clients.countSiteNacClients(
    session, 
    site_id=site_id, 
    distinct="last_status", 
    limit=10
).data

print("\nClient Connection Status Summary:")
print("-" * 40)
for result in clients_con.get('results', []):
    status = result.get('last_status', 'unknown')
    count = result.get('count', 0)
    print(f"  {status}: {count} client(s)")
print(f"\nTotal unique statuses: {clients_con.get('total', 0)}")

# ### Step 5.3 - View Client Events for Troubleshooting
#
# To investigate further, check the Durham site's client events. The `limit=10` parameter 
# will display the last 10 NAC client events.
#
# Look for events with:
# - `type: NAC_CLIENT_DENY` - Indicates a denied connection
# - `type: NAC_CLIENT_PERMIT` - Indicates a successful connection
# - `type: NAC_CLIENT_CERT_CHECK_SUCCESS` - Certificate validation succeeded
# - `text` field - Contains human-readable explanation of the event
#
# For the failed client (ajma-wifi-4), you should see:
# - `type: NAC_CLIENT_DENY`
# - `text: Client attempted unsupported authentication type, supported authentication types are EAP-TLS/EAP-TTLS+PAP`
#
# API Reference: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/sites/clients/nac/search-site-nac-client-events

# %%
events = mist.sites.nac_clients.searchSiteNacClientEvents(
    session, 
    site_id=site_id, 
    limit=10
).data

print("\nRecent NAC Client Events:")
print("=" * 60)
for idx, event in enumerate(events.get('results', []), 1):
    print(f"\nEvent {idx}:")
    print(f"  Type: {event.get('type', 'Unknown')}")
    print(f"  Username: {event.get('username', 'Unknown')}")
    print(f"  MAC: {event.get('mac', 'Unknown')}")
    print(f"  SSID: {event.get('ssid', 'Unknown')}")
    print(f"  Auth Type: {event.get('auth_type', 'N/A')}")
    
    if 'nacrule_name' in event:
        print(f"  NAC Rule: {event.get('nacrule_name')}")
    if 'cert_cn' in event:
        print(f"  Cert CN: {event.get('cert_cn')}")
    if 'text' in event:
        print(f"  Details: {event.get('text')}")
    
    print("-" * 60)

# ### Step 5.4 - View Detailed Client Information
#
# After identifying connected clients, get more detailed information about them by 
# searching the NAC clients for the site.
#
# This will show detailed information about each client including:
# - Authentication type and status
# - Certificate details (CN, issuer, serial, subject)
# - IP addresses
# - NAC rule matches
# - Connection history
#
# API Reference: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/sites/clients/nac/search-site-nac-clients

# %%
clients = mist.sites.nac_clients.searchSiteNacClients(session, site_id=site_id).data

print("\nDetailed NAC Client Information:")
print("=" * 60)
print(f"Total clients: {clients.get('total', 0)}")

for idx, client in enumerate(clients.get('results', []), 1):
    print(f"\nClient {idx}:")
    print(f"  Username: {client.get('last_username', 'Unknown')}")
    print(f"  MAC: {client.get('mac', 'Unknown')}")
    print(f"  Status: {client.get('last_status', 'Unknown')}")
    print(f"  Type: {client.get('type', 'Unknown')}")
    print(f"  Auth Type: {client.get('auth_type', 'N/A')}")
    print(f"  IP: {client.get('last_ip', 'N/A')}")
    print(f"  SSID: {client.get('last_ssid', 'N/A')}")
    print(f"  AP: {client.get('last_ap', 'N/A')}")
    
    if client.get('last_cert_cn'):
        print(f"  Cert CN: {client.get('last_cert_cn')}")
    if client.get('last_nacrule_name'):
        print(f"  NAC Rule: {client.get('last_nacrule_name')}")
    if client.get('nacrule_matched') is not None:
        print(f"  Rule Matched: {client.get('nacrule_matched')}")
    
    print("-" * 60)

# ### Step 5.5 - Search for Denied Clients Only
#
# Now search specifically for clients that were denied access. This helps quickly identify
# problematic clients.
#
# You can filter by:
# - `status="denied"` - Only show denied connections
# - `type="wireless"` - Include only wireless client events
# - `site_id` - Only include events from the Durham site

# %%
denied_clients = mist.sites.nac_clients.searchSiteNacClients(
    session, 
    site_id=site_id, 
    status="denied", 
    type="wireless"
).data

print("\nDenied Wireless Clients:")
print("=" * 60)
print(f"Total denied clients: {denied_clients.get('total', 0)}")

for idx, client in enumerate(denied_clients.get('results', []), 1):
    print(f"\nDenied Client {idx}:")
    print(f"  Username: {client.get('last_username', 'Unknown')}")
    print(f"  MAC: {client.get('mac', 'Unknown')}")
    print(f"  Status: {client.get('last_status', 'Unknown')}")
    print(f"  Cert CN: {client.get('cert_cn', 'N/A')}")
    print(f"  Cert Issuer: {client.get('cert_issuer', 'N/A')}")
    print(f"  Rule Matched: {client.get('nacrule_matched', False)}")
    print("-" * 60)

# ### Step 5.6 - Search for Denial Events
#
# Search specifically for `NAC_CLIENT_DENY` events to understand why clients were denied.
#
# Parameters:
# - `duration="10m"` - Look back 10 minutes
# - `type="NAC_CLIENT_DENY"` - Only show denial events
# - `limit=10` - Return up to 10 results
#
# The `text` field will contain the reason for denial. For ajma-wifi-4, this should 
# indicate an issue with the authentication type or certificate.

# %%
fail_events = mist.sites.nac_clients.searchSiteNacClientEvents(
    session, 
    site_id=site_id, 
    type="NAC_CLIENT_DENY", 
    limit=10, 
    duration="10m"
).data

print("\nRecent Client Denial Events (Last 10 minutes):")
print("=" * 60)
print(f"Total denial events: {len(fail_events.get('results', []))}")

for idx, event in enumerate(fail_events.get('results', []), 1):
    print(f"\nDenial Event {idx}:")
    print(f"  Username: {event.get('username', 'Unknown')}")
    print(f"  MAC: {event.get('mac', 'Unknown')}")
    print(f"  SSID: {event.get('ssid', 'Unknown')}")
    print(f"  Reason: {event.get('text', 'No details provided')}")
    print(f"  NAC Rule ID: {event.get('nacrule_id', 'N/A')}")
    print("-" * 60)

# ### Step 5.7 - Search for Specific Client by Username
#
# You can also search for a specific client by username. This is useful when you know 
# which client is having issues and want to see all events related to that client.
#
# Here we search for `ajma-wifi-4` which is the client with the intentionally invalid 
# certificate.

# %%
specific_client_events = mist.sites.nac_clients.searchSiteNacClientEvents(
    session, 
    site_id=site_id, 
    username="ajma-wifi-4", 
    limit=5
).data

print("\nEvents for ajma-wifi-4:")
print("=" * 60)
for idx, event in enumerate(specific_client_events.get('results', []), 1):
    print(f"\nEvent {idx}:")
    print(f"  Type: {event.get('type', 'Unknown')}")
    print(f"  Timestamp: {event.get('timestamp', 'Unknown')}")
    print(f"  MAC: {event.get('mac', 'Unknown')}")
    print(f"  SSID: {event.get('ssid', 'Unknown')}")
    if 'text' in event:
        print(f"  Details: {event.get('text')}")
    if 'cert_cn' in event:
        print(f"  Cert CN: {event.get('cert_cn')}")
    print("-" * 60)

# ### Step 5.8 - Cleanup (Optional)
#
# > **MANUAL STEP:**
# >
# > If you provisioned Wi-Fi client containers using Terraform in Step 4.3, you should 
# > clean them up before proceeding to the next lab.
# >
# > In the lab environment, this would be done with:
# > `terraform destroy -auto-approve`
# >
# > Expected output: `Destroy complete! Resources: 20 destroyed.`
# >
# > For other environments, remove your test Wi-Fi clients as appropriate.

# %%
print("=" * 60)
print("MANUAL STEP: Cleanup Wi-Fi Client Resources")
print("=" * 60)
print("If you created test Wi-Fi clients for this lab, clean them up now.")
print("")
print("For the lab environment:")
print("  terraform destroy -auto-approve")
print("")
print("For other environments:")
print("  Remove or disconnect test Wi-Fi client devices")
print("=" * 60)

# ---
# ## Lab Complete!
#
# You have successfully:
# - ✓ Configured the Durham site
# - ✓ Created a WPA3-Enterprise WLAN with EAP-TLS
# - ✓ Created NAC tags (Auth Policy Labels) for certificate matching
# - ✓ Created NAC rules (Auth Policies) for access control
# - ✓ Installed and configured CA certificates
# - ✓ Connected (or attempted to connect) Wi-Fi clients
# - ✓ Troubleshot authentication failures using the Mist API
#
# Key takeaways:
# - NAC tags must be created before NAC rules that reference them
# - Certificate-based authentication provides strong security
# - The Mist API provides detailed visibility into authentication events
# - The `searchSiteNacClientEvents` API is invaluable for troubleshooting
# - Certificate validation failures can be diagnosed through event logs

print("\n" + "=" * 60)
print("LAB 08 COMPLETE!")
print("=" * 60)
