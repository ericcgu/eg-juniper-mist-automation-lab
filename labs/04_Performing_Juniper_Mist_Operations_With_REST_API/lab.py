# # Lab 04: Performing Juniper Mist Operations with the MistAPI Python Package and the REST API
#
# ## Overview
#
# In this lab, you will perform Juniper Mist Day 1 operations using Python.
#
# By completing this lab, you will perform the following tasks:
#
# - Perform basic Juniper Mist API functions with Python `requests`
# - Perform basic Juniper Mist API functions with the `mistapi` Python package
#
# For this lab and all labs that follow, all the configurations will be applied
# using the REST API only. It may be helpful to view the results from the Juniper
# Mist GUI after each change is made.

# ### Step 1.1 - Import Modules
#
# Import the following modules and objects for use in this lab:
# - `mistapi` - the Mist API Python package
# - `v1` from `mistapi.api` - shorthand for the v1 API namespace
# - `requests` - for basic HTTP requests
# - `pprint` - for formatting output
# - `load_config_from_yaml` - shared helper from our project

# %%
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import mistapi
import requests
import yaml
from mistapi.api import v1 as mist
from pprint import pprint

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
pprint(env)

# ### Step 1.3 - Setup API Session
#
# Create a requests session with the API token from config.

# %%
# Step 1.3 - Setup API session with token
mist_api_root = f"https://{env['host']}/"
token = env['token']
session = requests.Session()
session.headers.update({'Authorization': f'Token {token}'})
print(f"Using token: {token[:8]}...")

# ### Step 1.4 - Discover Your Organization ID
#
# Use the `api/v1/self` endpoint to learn about your own account, including the
# organizations you have access to.

# %%
# Step 1.4 - Get org info using token auth
self_uri = "api/v1/self"
self_response = session.get(mist_api_root + self_uri)
pprint(self_response.json())

# ### Step 1.5 - Extract Organization ID
#
# The `privileges` list contains an entry for each Juniper Mist entity your account
# can access. Grab the first entry and extract `org_id`.
#
# > **Why add `org_id` to the `env` dictionary?**
# > You want to save these values to `config/env.yml` for use in later labs.

# %%
# Step 1.5 - Extract and store org_id
org_id = self_response.json()['privileges'][0]['org_id']
env['org_id'] = org_id
print(f"Organization ID: {org_id}")

# Save org_id to config/env.yml immediately
if org_id:
    save_config_to_yaml(env)

# ### Step 1.6 - List Existing Sites
#
# Check for existing sites using the sites endpoint.
#
# **GUI:** `Organization > Site Configuration > Sites`

# %%
# Step 1.6 - List sites
sites_uri = f"api/v1/orgs/{org_id}/sites"
sites = session.get(mist_api_root + sites_uri)
print(f"Status: {sites.status_code}")
pprint(sites.json())

# ### Step 1.7 - Retrieve Device Inventory
#
# **What is Mist Inventory?**
#
# Mist Inventory is the central repository in the Juniper Mist Cloud that tracks
# every piece of hardware associated with your organization. It serves as the
# "Master List" for all access points (APs), switches, and gateways (WAN Edges)
# that have been claimed or adopted.
#
# Think of it as the database that manages the lifecycle of your hardware—from
# the moment you "Claim" a device via its activation code to when it is assigned
# to a specific site and eventually "Released."
#
# The inventory endpoint (`api/v1/orgs/{org_id}/inventory`) returns all devices.
# Each device in the response includes a `type` field indicating whether it's an
# `ap`, `switch`, or `gateway`.
#
# **GUI:** `Organization > Inventory: Entire Org`

# %%
# Step 1.7 - Get all device inventory
inventory_uri = f"{mist_api_root}api/v1/orgs/{org_id}/inventory"
all_devices = session.get(inventory_uri).json()

print(f"=== All Devices (Total: {len(all_devices)}) ===")
pprint(all_devices)

# > **Q:** What is the current state of the inventory?
# >
# > **A:** The access point has been pre-adopted, but neither the switch nor
# > routers have. You should see only the AP currently in the inventory.

# ---
# ### Steps 1.8-1.9: MANUAL STEP - Adopt SSR-1
#
# This step **cannot** be performed from this notebook. Use the virtual console:
#
# 1. Connect to SSR-1 via console (CloudShell)
# 2. Login: user `root`, password `128tRoutes`
# 3. Run `pcli` to start the CLI
# 4. Run `adopt mist-instance Global03` and follow the prompts
# 5. Use your Mist credentials from the `.env` file
#
# ![ss1](../data/L04/screenshots/ss1.png)
# ![ss2](../data/L04/screenshots/ss2.png)
#
# > **Troubleshooting Virtual Console:**
# > - Try right-clicking the connection and opening in a new/private window
# > - Use a private/incognito window
# > - Switch browsers (Chrome, Firefox, Edge)
# > - Clear your browser cache

# ### Step 1.10 - Verify SSR-1 Adoption
#
# Re-fetch the edge inventory. Note the `mac` of the newly added device.

# %%
# Step 1.10 - Check edge inventory after SSR-1 adoption
edge_params = {'type': 'gateway'}
edges = session.get(inventory_uri, params=edge_params).json()
ssr1_device = next((device for device in edges if device.get('name') == 'SSR-1'), None)
pprint(ssr1_device)

# ### Step 1.11 - Record SSR-1 MAC Address
#
# Automatically extract the MAC address from the first edge device.

# %%
# Step 1.11 - Extract SSR-1 MAC from API response by device name

if ssr1_device:
    ssr1_mac = ssr1_device.get('mac')
    if ssr1_mac:
        env['ssr1_mac'] = ssr1_mac
        save_config_to_yaml(env)
        print(f"SSR-1 MAC: {ssr1_mac} - Saved to config/env.yml")
    else:
        print("SSR-1 device found but has no MAC address")
else:
    print("SSR-1 device not found in edge inventory")

# ---
# ### Step 1.12: MANUAL STEP - Adopt SSR-2
#
# Repeat the adoption process for SSR-2:
# 1. Connect via console, login as `root` / `128tRoutes`
# 2. Run `pcli`, then `adopt mist-instance Global03`
#
# ![ss4](../data/L04/screenshots/ss4.png)

# ### Step 1.13 - Verify SSR-2 Adoption

# %%
# Step 1.13 - Check edge inventory after SSR-2 adoption
edges = session.get(inventory_uri, params=edge_params).json()
ssr2_device = next((device for device in edges if device.get('name') == 'SSR-2'), None)
pprint(ssr2_device)

# ### Step 1.14 - Record SSR-2 MAC Address

# %%
# Step 1.14 - Extract SSR-2 MAC from API response by device name
if ssr2_device:
    ssr2_mac = ssr2_device.get('mac')
    if ssr2_mac:
        env['ssr2_mac'] = ssr2_mac
        save_config_to_yaml(env)
        print(f"SSR-2 MAC: {ssr2_mac} - Saved to config/env.yml")
    else:
        print("SSR-2 device found but has no MAC address")
else:
    print("SSR-2 device not found in edge inventory")

# ---
# ### Step 1.15: MANUAL STEP - Adopt SSR-3
#
# Repeat the adoption process for SSR-3.
#
# ![ss5](../data/L04/screenshots/ss5.png)

# ### Step 1.16 - Verify SSR-3 Adoption

# %%
# Step 1.16 - Check edge inventory after SSR-3 adoption
edges = session.get(inventory_uri, params=edge_params).json()
ssr3_device = next((device for device in edges if device.get('name') == 'SSR-3'), None)
pprint(ssr3_device)

# ### Step 1.17 - Record SSR-3 MAC Address

# %%
# Step 1.17 - Extract SSR-3 MAC from API response by device name
if ssr3_device:
    ssr3_mac = ssr3_device.get('mac')
    if ssr3_mac:
        env['ssr3_mac'] = ssr3_mac
        save_config_to_yaml(env)
        print(f"SSR-3 MAC: {ssr3_mac} - Saved to config/env.yml")
    else:
        print("SSR-3 device found but has no MAC address")
else:
    print("SSR-3 device not found in edge inventory")

# ---
# ### Step 1.18: MANUAL STEP - Adopt SSR-4
#
# Repeat the adoption process for SSR-4.
#
# ![ss6](../data/L04/screenshots/ss6.png)

# ### Step 1.19 - Verify SSR-4 Adoption

# %%
# Step 1.19 - Check edge inventory after SSR-4 adoption
edges = session.get(inventory_uri, params=edge_params).json()
ssr4_device = next((device for device in edges if device.get('name') == 'SSR-4'), None)
pprint(ssr4_device)

# ### Step 1.20 - Record SSR-4 MAC Address

# %%
# Step 1.20 - Extract SSR-4 MAC from API response by device name

if ssr4_device:
    ssr4_mac = ssr4_device.get('mac')
    if ssr4_mac:
        env['ssr4_mac'] = ssr4_mac
        save_config_to_yaml(env)
        print(f"SSR-4 MAC: {ssr4_mac} - Saved to config/env.yml")
    else:
        print("SSR-4 device found but has no MAC address")
else:
    print("SSR-4 device not found in edge inventory")

# ---
# ### Steps 1.21-1.22: EX Switch Adoption Prerequisites
#
# To adopt the EX switch, you'll generate the required configuration in the Mist
# interface and use the Juniper PyEZ Python library to apply it.
#
# Ensure `junos-eznc` is installed (included in `requirements.txt`).
#
# On Linux you may also need:
# ```bash
# sudo apt install -y libffi-dev libssl-dev libxml2-dev libxslt1-dev python3-dev
# ```

# ### Step 1.23: MANUAL STEP - Get EX Adoption Config
#
# 1. Navigate to `manage.mist.com`
# 2. Go to `Organization > Inventory > Switches`
# 3. Click `Adopt Switches`
# 4. Copy the generated configuration to clipboard
#
# ![ss3](../data/L04/screenshots/ss3.png)

# ### Step 1.24 - Apply EX Adoption Config
#
# Paste the copied configuration between the triple quotes below.
# **Remove** the final line reading `delete phone-home`.
#
# > **Note:** The triple quotes `"""` wrap multi-line strings in Python.

# %%
# Step 1.24 - Apply EX adoption config via PyEZ
from jnpr.junos import Device
from jnpr.junos.utils.config import Config

config = """

"""

with Device(host=env['ex_ip'], user='lab', passwd='lab123') as dev:
    cu = Config(dev)
    cu.load(config, format='set')
    cu.commit()

# ### Step 1.25 - Verify Switch Adoption
#
# **GUI:** `Organization > Inventory > Switches: Entire Org`

# %%
# Step 1.25 - Verify switch inventory
switch_params = {'type': 'switch'}
switches = session.get(inventory_uri, params=switch_params).json()
pprint(switches)

# ### Step 1.26 - Review Environment Dictionary

# %%
# Step 1.26 - Display current env
pprint(env)

# ### Step 1.27 - Save Environment Data
#
# Save your environment data to `config/env.yml` for use in later labs.
# The API token is excluded since it belongs in `.env`.
#
# Expected output:
# ```yaml
# ap1_mac: xxxxxxxxx
# ex1_mac: xxxxxxxxxxxxxxx
# host: xxxxxxxxx
# org_id: 000000-000-00000000
# ssr1_mac: xxxxxxxxxxxxxx
# token: xxxxxxxxxxxxxxxx
# ...
# ```

# %%
# Step 1.27 - Save config to env.yml
from pathlib import Path

config_path = Path(__file__).resolve().parent.parent.parent / "config" / "env.yml"

# Exclude token from YAML (it belongs in .env)
env_to_save = {k: v for k, v in env.items() if k != 'token'}

with open(config_path, 'w') as f:
    yaml.dump(env_to_save, f)

print(f"Saved config to {config_path}")

# ### Step 1.28 - Verify Saved Config

# %%
# Step 1.28 - Read back saved config
with open(config_path, 'r') as f:
    print(f.read())

# ---
# ## Part 2: Basic Juniper Mist Operations with Python Requests
#
# In this lab part, you will perform basic Juniper Mist API operations using
# the Python `requests` module.

# ### Step 2.1 - List Sites with Requests
#
# Check the list of currently configured sites for your assigned organization.
#
# **GUI:** `Organization > Site Configuration > Sites`

# %%
# Step 2.1 - List org sites
sites_uri = mist_api_root + f"api/v1/orgs/{org_id}/sites"
sites = session.get(sites_uri).json()
pprint(sites)

# > **Q:** What is the output from this step?
# >
# > **A:** You should see at least one currently existing site.

# ### Step 2.2 - Create a New Site (POST)
#
# Create a new site by sending a `POST` request to `api/v1/orgs/{org_id}/sites`.

# %%
# Step 2.2 - Create a site
sites_uri = mist_api_root + f"api/v1/orgs/{org_id}/sites"
site_payload = {
    "name": "L3-Site",
    "country_code": "US",
    "address": "1123 Fiction Lane, Hollywood 90210"
}
new_site = session.post(sites_uri, json=site_payload).json()
pprint(new_site)

# ### Step 2.3 - Read a Specific Site (GET + filter)
#
# Retrieve the site information for `L3-Site` using Python's built-in `filter()`.
#
# **GUI:** `Organization > Site Configuration > Sites`

# %%
# Step 2.3 - Filter for a specific site
sites = session.get(sites_uri).json()
l3_site = list(filter(lambda s: s['name'] == 'L3-Site', sites))[0]
site_id = l3_site['id']
pprint(l3_site)

# ### Step 2.4 - Get Site Settings
#
# Two important site endpoints:
# - `api/v1/orgs/{org_id}/sites` - basic details (name, location, templates)
# - `api/v1/sites/{site_id}/setting` - detailed settings (including inherited)
#
# Retrieve the existing settings before modifying them.

# %%
# Step 2.4 - Get site settings
settings_uri = mist_api_root + f"api/v1/sites/{site_id}/setting"
site_settings = session.get(settings_uri).json()
pprint(site_settings)

# > **Q:** Why is there so little data in this site settings object?
# >
# > **A:** The Juniper Mist API only stores values you have explicitly set.
# > Default values are applied behind the scenes automatically.

# ### Step 2.5 - Update Site Settings (PUT)
#
# Enable Honeypot Access Point detection by adding a `rogue` configuration.

# %%
# Step 2.5 - Enable honeypot detection
site_settings['rogue'] = {
    'honeypot_enabled': True
}

updated_settings = session.put(settings_uri, json=site_settings).json()
pprint(updated_settings)

# ### Step 2.6 - Delete a Site (DELETE)
#
# Clean up by removing the test site.

# %%
# Step 2.6 - Delete the test site
site_uri = mist_api_root + f"api/v1/sites/{site_id}"
deleted_site = session.delete(site_uri)
print(f"Delete status code: {deleted_site.status_code}")

# > **Q:** What result is obtained?
# >
# > **A:** You should see a status code of `200`, indicating success.

# ---
# ## Part 3: Perform Basic Juniper Mist Operations using the MistAPI Python Package
#
# In this lab part, you will perform the same CRUD operations from Part 2,
# but this time using the `mistapi` Python package.

# ### Step 3.1 - Authenticate with MistAPI
#
# Create an `mistapi.APISession` instance and call `.login()`.

# %%
# Step 3.1 - Create mistapi session
session = mistapi.APISession(apitoken=env['token'], host=env['host'])
session.login()

# > **Q:** Were you able to authenticate successfully?
# >
# > **A:** You should see the `Welcome !` banner. If authentication fails,
# > verify your `.env` file and `config/env.yml` are correct.

# ### Step 3.2 - List Sites with MistAPI
#
# `api/v1/orgs/{org_id}/sites` translates to `orgs.sites.listOrgSites()`

# %%
# Step 3.2 - List sites via mistapi
sites = mist.orgs.sites.listOrgSites(session, org_id=org_id)
pprint(sites.data)

# > **Q:** Why use `orgs.sites.listOrgSites()` instead of `api.v1.sites.listOrgSites()`?
# >
# > **A:** You imported `api.v1` as `mist`, so all functions are under this namespace.
# > This allows slightly less verbose code.

# ### Step 3.3 - Retrieve Inventory with MistAPI
#
# `orgs.inventory.getOrgInventory()` accepts a `type` argument.

# %%
# Step 3.3 - Get inventory via mistapi
aps = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='ap').data
switches = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='switch').data
edges = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='gateway').data

print("=== Access Points ===")
pprint(aps)
print("\n=== Switches ===")
pprint(switches)
print("\n=== WAN Edges ===")
pprint(edges)

# > **Q:** Why tack `.data` to the end of function calls?
# >
# > **A:** MistAPI methods return `APIResponse` objects. The `.data` attribute
# > gives you the parsed JSON directly.

# ### Step 3.4 - List Applications/Services

# %%
# Step 3.4 - List org services
applications = mist.orgs.services.listOrgServices(session, org_id=org_id).data
pprint(applications)

# > **Note:** Unless you have previously added applications in another lab,
# > you should see an empty list here.

# ### Step 3.5 - Create a Site with MistAPI (POST)

# %%
# Step 3.5 - Create a site via mistapi
site_payload = {
    "name": "L3-Site-Two",
    "country_code": "US",
    "address": "1123 Fiction Lane, Hollywood 90210"
}
new_site = mist.orgs.sites.createOrgSite(session, org_id=org_id, body=site_payload).data
pprint(new_site)

# ### Step 3.6 - Read a Specific Site with MistAPI

# %%
# Step 3.6 - Filter for specific site via mistapi
sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
l3_site = list(filter(lambda s: s['name'] == 'L3-Site-Two', sites))[0]
site_id = l3_site['id']
pprint(l3_site)

# ### Step 3.7 - Get Site Settings with MistAPI

# %%
# Step 3.7 - Get site settings via mistapi
l3_site_settings = mist.sites.setting.getSiteSetting(session, site_id=site_id).data
pprint(l3_site_settings)

# ### Step 3.8 - Update Site Settings with MistAPI (PUT)
#
# Enable Rogue Access Point detection.

# %%
# Step 3.8 - Enable rogue AP detection
l3_site_settings['rogue'] = {}
l3_site_settings['rogue']['enabled'] = True
l3_site_updated = mist.sites.setting.updateSiteSettings(
    session, site_id=site_id, body=l3_site_settings
).data
pprint(l3_site_updated)

# ### Step 3.9 - Delete a Site with MistAPI (DELETE)

# %%
# Step 3.9 - Delete the test site
deleted_site = mist.sites.sites.deleteSite(session, site_id=site_id).data
pprint(deleted_site)

# > **Note:** `deleted_site` should be an empty dictionary - the site no longer exists!

# ---
# ## Lab Complete
#
# You have successfully:
# - Generated API tokens and authenticated with the Mist API
# - Adopted SSR, EX, and AP devices
# - Performed CRUD operations on sites using both `requests` and `mistapi`
# - Saved environment data for use in subsequent labs
