# # Lab 06: Executing Juniper Mist Webhooks
#
# ## Overview
#
# In this lab, you will configure and analyze Juniper Mist webhooks at both the organization and site level.
#
# By completing this lab, you will perform the following tasks:
# - Create an organization-level webhook
# - Create a site-level webhook
# - Analyze webhook events

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
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import mistapi
from mistapi.api import v1 as mist
from pprint import pprint
import time

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
# ## Part 2: Create a Test Webhook Receiver
#
# In this part, you will use a free, anonymous webhook site to receive webhook messages sent from Juniper Mist.
#
# Step 2.1: Open a web browser and navigate to https://webhook.site
# Step 2.2: Copy the unique URL shown. You will need this for the webhook configuration steps below.

print("Please open https://webhook.site in your browser and copy your unique URL for use in the next steps.")
webhook_url = input("Paste your webhook.site URL here: ")

# ---
# ## Part 3: Configure Organization-level Webhook
#
# In this part, you will configure Juniper Mist to send org-level webhooks to the receiver you set up above.

# ### Step 3.1 - Create Org-level Webhook
#
# We'll create a webhook for the org that sends 'audits' events.

# %%
org_webhook_payload = {
    "name": "StudentOrgWebhook",
    "url": webhook_url,
    "enabled": True,
    "type": "http_post",
    "topics": ["audits"]
}
org_webhook = mist.orgs.webhooks.createOrgWebhook(session, org_id=org_id, body=org_webhook_payload).data
print("Organization-level webhook created:")
pprint(org_webhook)

# ---
# ## Part 4: Configure Site-level Webhook
#
# In this part, you will configure a site-level webhook for the Durham site.

# ### Step 4.1 - Get Durham Site ID
#
# We'll look up the Durham site by name.

# %%
sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
durham_sites = list(filter(lambda s: s.get("name") == "Durham", sites))
if not durham_sites:
    raise Exception("Durham site not found. Please create it first.")
durham_site = durham_sites[0]
site_id = durham_site['id']
print(f"Durham site ID: {site_id}")

# ### Step 4.2 - Create Site-level Webhook
#
# We'll create a webhook for the site that sends infrastructure events.

# %%
site_webhook_payload = {
    "name": "StudentSiteWebhook",
    "url": webhook_url,
    "enabled": True,
    "type": "http_post",
    "topics": ["client-info", "client-sessions", "device-events"]
}
site_webhook = mist.sites.webhooks.createSiteWebhook(session, site_id=site_id, body=site_webhook_payload).data
print("Site-level webhook created:")
pprint(site_webhook)

# ---
# ## Part 5: Analyze Webhook Events
#
# At this point, you can trigger events in the Mist UI (such as creating or deleting a WLAN, or changing device settings) and observe the resulting webhook payloads at your webhook.site URL.
#
# You can also use the Mist API to list and delete webhooks as needed.

# ### Step 5.1 - List Org-level Webhooks
# %%
org_webhooks = mist.orgs.webhooks.listOrgWebhooks(session, org_id=org_id).data
print("Current org-level webhooks:")
pprint(org_webhooks)

# ### Step 5.2 - List Site-level Webhooks
# %%
site_webhooks = mist.sites.webhooks.listSiteWebhooks(session, site_id=site_id).data
print("Current site-level webhooks:")
pprint(site_webhooks)

# ---
# ## Part 6: Cleanup (Optional)
#
# You can delete webhooks using the API if you wish.
#
# Example:
# # mist.orgs.webhooks.deleteOrgWebhook(session, org_id=org_id, webhook_id=org_webhook['id'])
# # mist.sites.webhooks.deleteSiteWebhook(session, site_id=site_id, webhook_id=site_webhook['id'])

print("\nLab 6 complete. Check your webhook.site page for incoming webhook events as you make changes in the Mist UI!")
