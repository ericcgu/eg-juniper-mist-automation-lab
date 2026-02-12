# # Lab 09: Deploy a Multi-site Hub-and-Spoke Network
#
# ## Overview
#
# In this lab you will use what you have learned about the Juniper Mist REST API to build 
# a script that will deploy and configure your entire infrastructure. To do so, you will 
# employ some scaling tricks to create a more streamlined and maintainable project.
#
# By completing this lab, you'll perform the following tasks:
# - Create a single source of truth for your infrastructure
# - Use the infrastructure details from your source of truth to deploy a multi-site 
#   hub-and-spoke enterprise
# - Start generating traffic across your network(s)

# ### Step 1.1 - Import Modules
#
# Import the following modules and objects for use in this lab:
# - `mistapi` - the Mist API Python package
# - `v1` from `mistapi.api` - shorthand for the v1 API namespace
# - `jinja2` - for creating deployment source-of-truth from templates
# - `pprint` - for formatting output
# - `load_config_from_yaml` - shared helper from our project
# - `time` - for time-related operations

# %%
import mistapi
from mistapi.api import v1 as mist
from jinja2 import Environment, FileSystemLoader
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

# ### Step 1.3 - Zeroize Environment (Optional)
#
# For this lab, it's best to start with a clean slate. If you have a `zeroize.py` script, 
# you can run it to remove all existing configurations for your organization without 
# releasing any adopted devices.
#
# This step is OPTIONAL and should only be run if you want to completely reset your 
# environment. Comment out or skip this step if you want to keep existing configurations.
#
# Manual Step: Run `python zeroize.py` in a terminal if available, or skip this step.

print("\n" + "="*80)
print("IMPORTANT: Zeroize Step")
print("="*80)
print("If you want to start with a clean environment, run 'python zeroize.py' manually.")
print("This will remove all configurations without releasing adopted devices.")
print("Skip this step if you want to keep existing configurations.")
print("="*80 + "\n")

# ### Step 1.4 - Setup API Session
#
# Create the `mistapi.APISession` object and run the `.login()` function.

# %%
session = mistapi.APISession(apitoken=token, host=env['host'])
session.login()

# ---
# ## Part 2: Prepare Lab Configuration Data
#
# In this lab part, you will prepare the objects required to perform the deployment.

# ### Step 2.1 - Load Deployment Configuration from Jinja2 Template
#
# For this deployment, you will use a Jinja2 template to create a YAML file that serves 
# as your single source-of-truth for your organization. This template contains mostly 
# hard-coded values for organization settings, but there are also several Jinja2-formatted 
# variables that need to be populated with the values in your `env` dictionary.
#
# Note: This step requires a deployment_vars.yml.j2 template file. If you don't have it, 
# you'll need to create a deployment configuration manually or use an existing YAML file.
#
# The template should be located in a templates directory. Adjust the path as needed.

# %%
import yaml

# Define paths
templates_dir = project_root / "templates"
output_dir = project_root / "labs" / "L09"
output_file = output_dir / "deployment_vars.yml"

# Create output directory if it doesn't exist
output_dir.mkdir(parents=True, exist_ok=True)

# Check if template exists
template_file = templates_dir / "deployment_vars.yml.j2"
if template_file.exists():
    print(f"Loading Jinja2 template from: {template_file}")
    
    # Load and render template
    environment = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = environment.get_template("deployment_vars.yml.j2")
    output = template.render(env)
    
    # Write source-of-truth to file
    with open(output_file, 'w') as f:
        f.write(output)
    
    # Save source-of-truth as python dict by parsing rendered YAML
    data = yaml.safe_load(output)
    
    print(f"Deployment configuration saved to: {output_file}")
    print(f"Configuration loaded with {len(data)} top-level keys")
else:
    print(f"WARNING: Template file not found at {template_file}")
    print("You'll need to manually create a deployment configuration or provide the template.")
    print("\nCreating minimal sample deployment configuration...")
    
    # Create a minimal sample configuration if template doesn't exist
    data = {
        'sites': [],
        'applications': [],
        'networks': [],
        'hub_profiles': [],
        'wan_edge_templates': [],
        'switch_templates': [],
        'wlan_templates': [],
        'rf_templates': [],
        'wlans': [],
        'wxtags': [],
        'wxrules': [],
        'psks': []
    }
    print("Sample configuration created. Populate 'data' dictionary with your deployment details.")

# Note: You can examine the deployment configuration by printing data or opening the 
# deployment_vars.yml file

# ---
# ## Part 3: Automate All The Things!
#
# In this lab part, you will deploy all the configurations for your org. The ordering of 
# the deployment is important to ensure all dependencies are in place. You will use the 
# following workflow:
#
# 1. Create Sites and Site variables
# 2. Assign devices to Sites
# 3. Create Applications
# 4. Create LAN Networks
# 5. Deploy Hub Profiles
# 6. Deploy WAN Edge Templates
# 7. Deploy Switch Templates
# 8. Deploy WLAN Templates
# 9. Create RF Templates
# 10. Create WLANs
# 11. Create Labels (wxtags)
# 12. Deploy WLAN Policies (wxrules)
# 13. Create Org PSKs

# ### Step 3.1 - Create Sites
#
# In this step, you'll grab the `sites` list from the `data` dictionary containing all 
# your organizational configs. Then you will loop through the sites to be created and 
# create each site defined within it.
#
# Site configuration is maintained both as `SiteInfo` and `SiteSettings`. You'll deal 
# first with the `SiteInfo`, which contains the name, location information, and template 
# assignments for the site.

# %%
if 'sites' in data and data['sites']:
    sites_data = data['sites']
    existing_sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    
    for site_config in sites_data:
        site_name = site_config.get('name', 'Unknown')
        existing_site = next(filter(lambda s: s.get('name') == site_name, existing_sites), None)
        
        if existing_site:
            print(f"Site '{site_name}' already exists, updating...")
            site = mist.sites.sites.updateSiteInfo(
                session, 
                site_id=existing_site['id'], 
                body=site_config
            ).data
            print(f"  Updated site: {site['name']} (ID: {site['id']})")
        else:
            print(f"Creating site: {site_name}")
            site = mist.orgs.sites.createOrgSite(
                session, 
                org_id=org_id, 
                body=site_config
            ).data
            print(f"  Created site: {site['name']} (ID: {site['id']})")
    
    print(f"\nSite creation complete. Total sites: {len(sites_data)}")
else:
    print("No sites defined in deployment configuration")

# ### Step 3.2 - Validation (Manual GUI Check)
#
# To verify the site creation:
# 1. Open a web browser and navigate to `manage.mist.com`
# 2. Login with your provided credentials
# 3. Select your assigned organization
# 4. Navigate to `Organization > Site Configuration`
# 5. Ensure that all sites defined in your deployment settings have been created

print("\n" + "="*80)
print("Manual Validation: Site Creation")
print("="*80)
print("1. Navigate to: Organization > Site Configuration")
print("2. Verify all 4 sites are created (Durham, Westford, Sunnyvale, Cupertino)")
print("="*80 + "\n")

# ### Step 3.3 - Configure Site Variables
#
# Next you'll deal with configuring the site variables, which are part of `SiteSettings`.
# You'll loop through each value in the `settings` key for each site and create that 
# setting for the site using `updateSiteSettings`.

# %%
if 'sites' in data and data['sites']:
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    
    for site_config in sites_data:
        site_name = site_config.get('name', 'Unknown')
        site = next(filter(lambda s: s.get('name') == site_name, sites), None)
        
        if site and 'settings' in site_config:
            print(f"Configuring variables for site: {site_name}")
            settings = mist.sites.setting.updateSiteSettings(
                session, 
                site_id=site['id'], 
                body=site_config['settings']
            ).data
            print(f"  Variables configured for {site_name}")
    
    print("\nSite variables configuration complete")

# ### Step 3.4 - Validation (Manual GUI Check)
#
# Navigate to each site and verify Site Variables have been created.

print("\n" + "="*80)
print("Manual Validation: Site Variables")
print("="*80)
print("1. Navigate to: Organization > Site Configuration")
print("2. Click on each site and scroll to 'Site Variables'")
print("3. Verify variables are configured correctly")
print("="*80 + "\n")

# ### Step 3.5 - Assign Devices to Sites
#
# Next, you'll assign the appropriate devices to each site.
#
# You'll start by grabbing the list of devices of each type (`ap`, `switch`, and `gateway`) 
# from the devices inventory using the `getOrgInventory` function. You'll then loop through 
# your `sites_data` again and find the devices to be assigned for each site.

# %%
if 'sites' in data and data['sites']:
    aps = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='ap').data
    switches = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='switch').data
    edges = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='gateway').data
    
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    
    for site_config in sites_data:
        site_name = site_config.get('name', 'Unknown')
        site = next(filter(lambda s: s.get('name') == site_name, sites), None)
        
        if not site:
            print(f"WARNING: Site '{site_name}' not found, skipping device assignment")
            continue
        
        print(f"\nAssigning devices to site: {site_name}")
        
        # Assign APs
        if 'aps' in site_config:
            for ap_mac in site_config['aps']:
                clean_mac = "".join(ap_mac.split(":"))
                ap = next(filter(lambda a: a.get('mac') == clean_mac, aps), None)
                
                if ap:
                    payload = {
                        "op": "assign",
                        "managed": True,
                        "macs": [clean_mac],
                        "site_id": site['id']
                    }
                    mist.orgs.inventory.updateOrgInventoryAssignment(
                        session, 
                        org_id=org_id, 
                        body=payload
                    )
                    print(f"  Assigned AP: {clean_mac}")
        
        # Assign Switches
        if 'switches' in site_config:
            for sw_mac in site_config['switches']:
                clean_mac = "".join(sw_mac.split(":"))
                sw = next(filter(lambda s: s.get('mac') == clean_mac, switches), None)
                
                if sw:
                    payload = {
                        "op": "assign",
                        "managed": True,
                        "macs": [clean_mac],
                        "site_id": site['id']
                    }
                    mist.orgs.inventory.updateOrgInventoryAssignment(
                        session, 
                        org_id=org_id, 
                        body=payload
                    )
                    print(f"  Assigned Switch: {clean_mac}")
        
        # Assign Gateways
        if 'edges' in site_config:
            for edge_mac in site_config['edges']:
                clean_mac = "".join(edge_mac.split(":"))
                edge = next(filter(lambda e: e.get('mac') == clean_mac, edges), None)
                
                if edge:
                    payload = {
                        "op": "assign",
                        "managed": True,
                        "macs": [clean_mac],
                        "site_id": site['id']
                    }
                    mist.orgs.inventory.updateOrgInventoryAssignment(
                        session, 
                        org_id=org_id, 
                        body=payload
                    )
                    print(f"  Assigned Gateway: {clean_mac}")
    
    print("\nDevice assignment complete")

# ### Step 3.6 - Validation (Manual GUI Check)
#
# Verify devices have been assigned to appropriate sites in the GUI.

print("\n" + "="*80)
print("Manual Validation: Device Assignment")
print("="*80)
print("1. Navigate to: Organization > Inventory")
print("2. Select 'Entire Org' from the 'Orgs' dropdown")
print("3. Check tabs for: WAN Edges, Switches, Access Points")
print("4. Verify devices are assigned to correct sites")
print("\nNote: AP may show 'Disconnected' until switch template is applied")
print("="*80 + "\n")

# ### Step 3.7 - Create Applications
#
# Next you'll create applications using the `createOrgService()` function.

# %%
if 'applications' in data and data['applications']:
    apps = data['applications']
    existing_apps = mist.orgs.services.listOrgServices(session, org_id=org_id).data
    
    for app in apps:
        app_name = app.get('name', 'Unknown')
        existing_app = next(filter(lambda a: a.get('name') == app_name, existing_apps), None)
        
        if existing_app:
            print(f"Application '{app_name}' already exists, skipping")
        else:
            print(f"Creating application: {app_name}")
            created_app = mist.orgs.services.createOrgService(
                session, 
                org_id=org_id, 
                body=app
            ).data
            print(f"  Created application: {created_app['name']} (ID: {created_app['id']})")
    
    print(f"\nApplication creation complete. Total: {len(apps)}")
else:
    print("No applications defined in deployment configuration")

# ### Step 3.8 - Validation (Manual GUI Check)

print("\n" + "="*80)
print("Manual Validation: Applications")
print("="*80)
print("1. Navigate to: Organization > WAN > Applications")
print("2. Verify all applications from deployment config are created")
print("="*80 + "\n")

# ### Step 3.9 - Create LAN Networks
#
# Next you'll create the LAN Networks, following the same pattern as with applications.

# %%
if 'networks' in data and data['networks']:
    networks = data['networks']
    existing_networks = mist.orgs.networks.listOrgNetworks(session, org_id=org_id).data
    
    for net in networks:
        net_name = net.get('name', 'Unknown')
        existing_net = next(filter(lambda n: n.get('name') == net_name, existing_networks), None)
        
        if existing_net:
            print(f"Network '{net_name}' already exists, skipping")
        else:
            print(f"Creating network: {net_name}")
            created_net = mist.orgs.networks.createOrgNetwork(
                session, 
                org_id=org_id, 
                body=net
            ).data
            print(f"  Created network: {created_net['name']} (ID: {created_net['id']})")
    
    print(f"\nNetwork creation complete. Total: {len(networks)}")
else:
    print("No networks defined in deployment configuration")

# ### Step 3.10 - Validation (Manual GUI Check)

print("\n" + "="*80)
print("Manual Validation: Networks")
print("="*80)
print("1. Navigate to: Organization > WAN > Networks")
print("2. Verify all networks from deployment config are created")
print("="*80 + "\n")

# ### Step 3.11 - Create VPN Endpoints
#
# Before deploying hub and WAN Edge profiles, you need to create VPN endpoints. When you 
# do this through the web interface, Juniper Mist will automatically create these VPN 
# objects. However, with the API, you need to create these yourself.
#
# You can use the `orgs.vpns.createOrgVpn` function to create all the VPN endpoints 
# defined in the hub and WAN Edge profiles.

# %%
if 'vpn' in data and data['vpn']:
    vpn_config = data['vpn']
    print(f"Creating VPN: {vpn_config.get('name', 'OrgOverlay')}")
    
    vpns = mist.orgs.vpns.createOrgVpn(session, org_id=org_id, body=vpn_config).data
    print("VPN created successfully")
elif 'hub_profiles' in data or 'wan_edge_templates' in data:
    # Create default VPN if not specified but hub/edge templates exist
    print("Creating default VPN for hub-and-spoke topology")
    payload = {
        "name": "OrgOverlay",
        "paths": {
            "SunnyvaleHub-INET": {},
            "SunnyvaleHub-MPLS": {},
            "CupertinoHub-INET": {},
            "CupertinoHub-MPLS": {}
        },
        "created_by": "user"
    }
    
    vpns = mist.orgs.vpns.createOrgVpn(session, org_id=org_id, body=payload).data
    print("Default VPN created successfully")
else:
    print("No VPN configuration needed")

# ### Step 3.12 - Deploy Hub Profiles
#
# Next you'll deploy the hub profiles which will configure hub sites as SD-WAN hub sites.
#
# The YAML file and the `data` dictionary do not perfectly match the structure of the 
# payload expected by the `createOrgDeviceProfile()` function. Inside of 
# `data['hub_profiles']`, you have keys like `device` and `site` which tell you where to 
# assign these profiles, but the profile itself should not include these keys.

# %%
if 'hub_profiles' in data and data['hub_profiles']:
    hub_profiles = data['hub_profiles']
    existing_hubs = mist.orgs.deviceprofiles.listOrgDeviceProfiles(
        session, 
        org_id=org_id, 
        type='gateway'
    ).data
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    devices = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='gateway').data
    
    for hub in hub_profiles:
        hub_name = hub.get('name', 'Unknown')
        existing_hub = next(filter(lambda h: h.get('name') == hub_name, existing_hubs), None)
        
        # Make a copy to avoid modifying original
        hub_payload = dict(hub)
        
        # Extract site and device info (remove from payload)
        site_name = hub_payload.pop('site', None)
        device_mac = hub_payload.pop('device', None)
        
        if existing_hub:
            print(f"Hub profile '{hub_name}' already exists, skipping")
        else:
            print(f"Creating hub profile: {hub_name}")
            created_hub = mist.orgs.deviceprofiles.createOrgDeviceProfile(
                session, 
                org_id=org_id, 
                body=hub_payload
            ).data
            print(f"  Created hub profile: {created_hub['name']} (ID: {created_hub['id']})")
            
            # Assign profile to device if specified
            if device_mac and site_name:
                site = next(filter(lambda s: s.get('name') == site_name, sites), None)
                if site:
                    clean_mac = "".join(device_mac.split(":"))
                    device = next(filter(lambda d: d.get('mac') == clean_mac, devices), None)
                    
                    if device:
                        assign_payload = {"deviceprofile_id": created_hub['id']}
                        mist.sites.devices.updateSiteDevice(
                            session, 
                            site_id=site['id'], 
                            device_id=device['id'], 
                            body=assign_payload
                        )
                        print(f"  Assigned to device: {clean_mac} at site {site_name}")
    
    print(f"\nHub profile deployment complete. Total: {len(hub_profiles)}")
else:
    print("No hub profiles defined in deployment configuration")

# ### Step 3.13 - Validation (Manual GUI Check)

print("\n" + "="*80)
print("Manual Validation: Hub Profiles")
print("="*80)
print("1. Navigate to: Organization > WAN > Hub Profiles")
print("2. Verify hub profiles are created and applied to correct devices")
print("="*80 + "\n")

# ### Step 3.14 - Deploy WAN Edge Templates
#
# Next, you'll deploy the WAN Edge templates. Similarly to the Hub Profiles, there are 
# some keys in the WAN Edge dictionary that you want to use to determine which sites to 
# assign them to, but that you don't want to include in the payload to the 
# `createOrgGatewayTemplate()` function.

# %%
if 'wan_edge_templates' in data and data['wan_edge_templates']:
    edge_templates = data['wan_edge_templates']
    existing_edges = mist.orgs.gatewaytemplates.listOrgGatewayTemplates(session, org_id=org_id).data
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    
    for edge in edge_templates:
        edge_name = edge.get('name', 'Unknown')
        existing_edge = next(filter(lambda e: e.get('name') == edge_name, existing_edges), None)
        
        # Make a copy to avoid modifying original
        edge_payload = dict(edge)
        
        # Extract sites info (remove from payload)
        site_names = edge_payload.pop('sites', [])
        
        if existing_edge:
            print(f"WAN Edge template '{edge_name}' already exists, skipping")
        else:
            print(f"Creating WAN Edge template: {edge_name}")
            created_edge = mist.orgs.gatewaytemplates.createOrgGatewayTemplate(
                session, 
                org_id=org_id, 
                body=edge_payload
            ).data
            print(f"  Created WAN Edge template: {created_edge['name']} (ID: {created_edge['id']})")
            
            # Assign template to sites if specified
            for site_name in site_names:
                site = next(filter(lambda s: s.get('name') == site_name, sites), None)
                if site:
                    site_payload = {"gatewaytemplate_id": created_edge['id']}
                    mist.sites.setting.updateSiteSettings(
                        session, 
                        site_id=site['id'], 
                        body=site_payload
                    )
                    print(f"  Assigned to site: {site_name}")
    
    print(f"\nWAN Edge template deployment complete. Total: {len(edge_templates)}")
else:
    print("No WAN Edge templates defined in deployment configuration")

# ### Step 3.15 - Validation (Manual GUI Check)

print("\n" + "="*80)
print("Manual Validation: WAN Edge Templates")
print("="*80)
print("1. Navigate to: Organization > WAN > WAN Edge Templates")
print("2. Verify templates are created and applied to correct sites")
print("="*80 + "\n")

# ### Step 3.16 - Deploy Switch Templates
#
# Next you'll deploy switch templates. As with the hub profiles and WAN Edge templates, 
# you need to remove the `sites` key from each switch template before applying to the 
# `createOrgNetworkTemplate()` function.

# %%
if 'switch_templates' in data and data['switch_templates']:
    switch_templates = data['switch_templates']
    existing_sws = mist.orgs.networktemplates.listOrgNetworkTemplates(session, org_id=org_id).data
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    
    for sw in switch_templates:
        sw_name = sw.get('name', 'Unknown')
        existing_sw = next(filter(lambda s: s.get('name') == sw_name, existing_sws), None)
        
        # Make a copy to avoid modifying original
        sw_payload = dict(sw)
        
        # Extract sites info (remove from payload)
        site_names = sw_payload.pop('sites', [])
        
        if existing_sw:
            print(f"Switch template '{sw_name}' already exists, skipping")
        else:
            print(f"Creating switch template: {sw_name}")
            created_sw = mist.orgs.networktemplates.createOrgNetworkTemplate(
                session, 
                org_id=org_id, 
                body=sw_payload
            ).data
            print(f"  Created switch template: {created_sw['name']} (ID: {created_sw['id']})")
            
            # Assign template to sites if specified
            for site_name in site_names:
                site = next(filter(lambda s: s.get('name') == site_name, sites), None)
                if site:
                    site_payload = {"networktemplate_id": created_sw['id']}
                    mist.sites.setting.updateSiteSettings(
                        session, 
                        site_id=site['id'], 
                        body=site_payload
                    )
                    print(f"  Assigned to site: {site_name}")
    
    print(f"\nSwitch template deployment complete. Total: {len(switch_templates)}")
else:
    print("No switch templates defined in deployment configuration")

# ### Step 3.17 - Validation (Manual GUI Check)

print("\n" + "="*80)
print("Manual Validation: Switch Templates")
print("="*80)
print("1. Navigate to: Organization > Wired > Switch Templates")
print("2. Verify templates are created and applied to correct sites")
print("="*80 + "\n")

# ### Step 3.18 - Deploy WLAN Templates
#
# Next you'll deploy the WLAN templates. These are already structured within your `data` 
# dictionary exactly as they are needed for use by the `createOrgTemplate()` function.

# %%
if 'wlan_templates' in data and data['wlan_templates']:
    wlan_templates = data['wlan_templates']
    existing_wlan_templates = mist.orgs.templates.listOrgTemplates(session, org_id=org_id).data
    
    for wlan_template in wlan_templates:
        template_name = wlan_template.get('name', 'Unknown')
        existing_template = next(
            filter(lambda t: t.get('name') == template_name, existing_wlan_templates), 
            None
        )
        
        if existing_template:
            print(f"WLAN template '{template_name}' already exists, skipping")
        else:
            print(f"Creating WLAN template: {template_name}")
            created_template = mist.orgs.templates.createOrgTemplate(
                session, 
                org_id=org_id, 
                body=wlan_template
            ).data
            print(f"  Created WLAN template: {created_template['name']} (ID: {created_template['id']})")
    
    print(f"\nWLAN template deployment complete. Total: {len(wlan_templates)}")
else:
    print("No WLAN templates defined in deployment configuration")

# ### Step 3.19 - Deploy RF Templates
#
# Next you'll deploy RF templates. These are already structured within your `data` 
# dictionary exactly as they are needed for use by the `createOrgRfTemplate()` function.
#
# You'll also need to apply your templates to the associated sites.

# %%
if 'rf_templates' in data and data['rf_templates']:
    rf_templates = data['rf_templates']
    existing_rf_templates = mist.orgs.rftemplates.listOrgRfTemplates(session, org_id=org_id).data
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    
    for rf in rf_templates:
        rf_name = rf.get('name', 'Unknown')
        existing_rf = next(filter(lambda r: r.get('name') == rf_name, existing_rf_templates), None)
        
        # Make a copy to avoid modifying original
        rf_payload = dict(rf)
        
        # Extract sites info (remove from payload)
        site_names = rf_payload.pop('sites', [])
        
        if existing_rf:
            print(f"RF template '{rf_name}' already exists, skipping")
        else:
            print(f"Creating RF template: {rf_name}")
            created_rf = mist.orgs.rftemplates.createOrgRfTemplate(
                session, 
                org_id=org_id, 
                body=rf_payload
            ).data
            print(f"  Created RF template: {created_rf['name']} (ID: {created_rf['id']})")
            
            # Assign template to sites if specified
            for site_name in site_names:
                site = next(filter(lambda s: s.get('name') == site_name, sites), None)
                if site:
                    site_payload = {"rftemplate_id": created_rf['id']}
                    mist.sites.setting.updateSiteSettings(
                        session, 
                        site_id=site['id'], 
                        body=site_payload
                    )
                    print(f"  Assigned to site: {site_name}")
    
    print(f"\nRF template deployment complete. Total: {len(rf_templates)}")
else:
    print("No RF templates defined in deployment configuration")

# ### Step 3.20 - Deploy WLANs
#
# Next you'll deploy the WLANs and attach them to the desired WLAN template.

# %%
if 'wlans' in data and data['wlans']:
    wlans = data['wlans']
    existing_wlans = mist.orgs.wlans.listOrgWlans(session, org_id=org_id).data
    existing_templates = mist.orgs.templates.listOrgTemplates(session, org_id=org_id).data
    
    for wlan in wlans:
        wlan_ssid = wlan.get('ssid', 'Unknown')
        existing_wlan = next(filter(lambda w: w.get('ssid') == wlan_ssid, existing_wlans), None)
        
        # Make a copy to avoid modifying original
        wlan_payload = dict(wlan)
        
        # Extract template name (remove from payload)
        template_name = wlan_payload.pop('template', None)
        
        if existing_wlan:
            print(f"WLAN '{wlan_ssid}' already exists, skipping")
        else:
            print(f"Creating WLAN: {wlan_ssid}")
            
            # Get template ID if template name is specified
            if template_name:
                template = next(
                    filter(lambda t: t.get('name') == template_name, existing_templates), 
                    None
                )
                if template:
                    wlan_payload['template_id'] = template['id']
            
            created_wlan = mist.orgs.wlans.createOrgWlan(
                session, 
                org_id=org_id, 
                body=wlan_payload
            ).data
            print(f"  Created WLAN: {created_wlan['ssid']} (ID: {created_wlan['id']})")
            if template_name:
                print(f"  Attached to template: {template_name}")
    
    print(f"\nWLAN deployment complete. Total: {len(wlans)}")
else:
    print("No WLANs defined in deployment configuration")

# ### Step 3.21 - Validation (Manual GUI Check)

print("\n" + "="*80)
print("Manual Validation: WLAN Templates and WLANs")
print("="*80)
print("1. Navigate to: Organization > Wireless > WLAN Templates")
print("2. Verify WLAN templates are created")
print("3. Click on each template and verify WLANs are attached")
print("="*80 + "\n")

# ### Step 3.22 - Create Labels (wxtags)
#
# Create wireless labels (wxtags) for WLAN policies.

# %%
if 'wxtags' in data and data['wxtags']:
    wxtags = data['wxtags']
    existing_wxtags = mist.orgs.wxtags.listOrgWxTags(session, org_id=org_id).data
    
    for wxtag in wxtags:
        tag_name = wxtag.get('name', 'Unknown')
        existing_tag = next(filter(lambda t: t.get('name') == tag_name, existing_wxtags), None)
        
        if existing_tag:
            print(f"Label '{tag_name}' already exists, skipping")
        else:
            print(f"Creating label: {tag_name}")
            created_tag = mist.orgs.wxtags.createOrgWxTag(
                session, 
                org_id=org_id, 
                body=wxtag
            ).data
            print(f"  Created label: {created_tag['name']} (ID: {created_tag['id']})")
    
    print(f"\nLabel creation complete. Total: {len(wxtags)}")
else:
    print("No labels (wxtags) defined in deployment configuration")

# ### Step 3.23 - Deploy WLAN Policies (wxrules)
#
# Deploy WLAN policy rules.

# %%
if 'wxrules' in data and data['wxrules']:
    wxrules = data['wxrules']
    existing_wxrules = mist.orgs.wxrules.listOrgWxRules(session, org_id=org_id).data
    
    for wxrule in wxrules:
        rule_id = wxrule.get('id', None)
        
        # Check if rule exists (rules don't have names, so we check by other criteria)
        print("Creating WLAN policy rule")
        created_rule = mist.orgs.wxrules.createOrgWxRule(
            session, 
            org_id=org_id, 
            body=wxrule
        ).data
        print(f"  Created WLAN policy rule (ID: {created_rule['id']})")
    
    print(f"\nWLAN policy deployment complete. Total: {len(wxrules)}")
else:
    print("No WLAN policies (wxrules) defined in deployment configuration")

# ### Step 3.24 - Create Org PSKs
#
# Create organization-level pre-shared keys for WLANs.

# %%
if 'psks' in data and data['psks']:
    psks = data['psks']
    existing_psks = mist.orgs.psks.listOrgPsks(session, org_id=org_id).data
    
    for psk in psks:
        psk_name = psk.get('name', 'Unknown')
        existing_psk = next(filter(lambda p: p.get('name') == psk_name, existing_psks), None)
        
        if existing_psk:
            print(f"PSK '{psk_name}' already exists, skipping")
        else:
            print(f"Creating PSK: {psk_name}")
            created_psk = mist.orgs.psks.createOrgPsk(
                session, 
                org_id=org_id, 
                body=psk
            ).data
            print(f"  Created PSK: {created_psk['name']} (ID: {created_psk['id']})")
    
    print(f"\nPSK creation complete. Total: {len(psks)}")
else:
    print("No PSKs defined in deployment configuration")

# ---
# ## Lab Complete
#
# You have successfully completed Lab 09: Deploy a Multi-site Hub-and-Spoke Network!
#
# Summary of completed tasks:
# - Created sites and configured site variables
# - Assigned devices to sites
# - Created applications and networks
# - Deployed hub profiles and WAN Edge templates
# - Deployed switch templates and WLAN templates
# - Created RF templates and WLANs
# - Created labels and WLAN policies
# - Created organization PSKs

print("\n" + "="*80)
print("LAB 09 COMPLETE")
print("="*80)
print("\nSummary:")
print("  ✓ Sites created and configured")
print("  ✓ Devices assigned to sites")
print("  ✓ Applications and networks created")
print("  ✓ Hub profiles and WAN Edge templates deployed")
print("  ✓ Switch templates and WLAN templates deployed")
print("  ✓ RF templates and WLANs created")
print("  ✓ Labels and WLAN policies configured")
print("  ✓ Organization PSKs created")
print("\nYour multi-site hub-and-spoke network is now deployed!")
print("Refer to the Juniper Mist GUI for validation and monitoring.")
print("="*80 + "\n")
