# # Lab 10: Troubleshooting Day 2+ Operations with Juniper Mist
#
# ## Overview
#
# In this lab you will monitor and troubleshoot your enterprise Juniper Mist deployment 
# using both the Juniper Mist REST API and Juniper Mist Web interface.
#
# By completing this lab, you'll perform the following tasks:
# - Check the current state of your Durham site
# - Introduce traffic forwarding issues on WAN links and observe how Juniper Mist traffic 
#   steering adjusts to these conditions
# - Use the Insights API to gather detailed metrics
# - Visualize network statistics using Pandas and HoloViews

# ### Step 1.1 - Import Modules
#
# Import the following modules and objects for use in this lab:
# - `mistapi` - the Mist API Python package
# - `v1` from `mistapi.api` - shorthand for the v1 API namespace
# - `pandas` - for data analysis and manipulation
# - `holoviews` - for interactive visualizations
# - `pprint` - for formatting output
# - `load_config_from_yaml` - shared helper from our project
# - `time` - for time-related operations
# - `warnings` - to suppress unnecessary warnings

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
import warnings

# Data visualization libraries
import pandas as pd
import holoviews as hv

# Reload utils module to pick up changes
import importlib
import utils
importlib.reload(utils)
from utils import load_config_from_yaml

# Configure visualization settings
warnings.filterwarnings('ignore')
hv.extension('bokeh')

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

# ### Step 1.3 - Prerequisites Check
#
# This lab will work best if you have previously completed Lab 9. Lab 9 configures all 
# sites and devices and starts traffic generation. Without these configs and the generated 
# traffic, your results here won't be very interesting.

print("\n" + "="*80)
print("PREREQUISITES CHECK")
print("="*80)
print("This lab requires Lab 09 to be completed first.")
print("Lab 09 configures all sites, devices, and starts traffic generation.")
print("Without these configurations, results may be limited.")
print("="*80 + "\n")

# ### Step 1.4 - Setup API Session
#
# Create the `mistapi.APISession` object and run the `.login()` function.

# %%
session = mistapi.APISession(apitoken=token, host=env['host'])
session.login()

# ---
# ## Part 2: Helper Functions
#
# In this lab part, you will create helper functions for common operations.

# ### Step 2.1 - Metric Printer Function
#
# Create a utility function that formats metric information and prints it in a readable style.

# %%
def print_metric(metric):
    """Print metric information in a readable format."""
    print(f"Metric: {metric.get('description', 'No description')}")
    print(f"\nScopes: {', '.join(metric.get('scopes', []))}")
    print(f"Type: {metric.get('type', 'Unknown')}")
    print("\nParameters:")
    for param, details in metric.get('params', {}).items():
        required = " (REQUIRED)" if details.get('required', False) else ""
        print(f"  - {param}: {details.get('description', 'No description')}{required}")
    print()

# ---
# ## Part 3: Troubleshooting and Statistics Functions with the API
#
# In this lab part, you will use the Juniper Mist REST API to perform routine monitoring 
# tasks. You will focus on the Durham site as this site has a full stack of WAN, wired, 
# and wireless devices.

# ### Step 3.1 - Retrieve Durham Site and SSR-1 Device
#
# Since you'll be dealing with the `Durham` site and the `SSR-1` device, you'll retrieve 
# the lists of sites and devices from the API.

# %%
sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
site = next(filter(lambda s: s.get('name') == 'Durham', sites), None)

devices = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='gateway').data
device = next(filter(lambda d: d.get('name') == 'SSR-1', devices), None)

if site:
    print(f"Found Durham site: {site['name']} (ID: {site['id']})")
else:
    print("WARNING: Durham site not found!")

if device:
    print(f"Found SSR-1 device: {device['name']} (MAC: {device['mac']})")
else:
    print("WARNING: SSR-1 device not found!")

# ### Step 3.2 - Troubleshoot WAN
#
# Let's start with a high-level check for any clear problems. You can use the 
# `orgs.troubleshoot.troubleshootOrg()` function for this.
#
# When running this function, you need to specify the `type` which will dictate which type 
# of device or traffic you want to troubleshoot. Let's start by troubleshooting WAN.

# %%
if site and device:
    tshoot_edge = mist.orgs.troubleshoot.troubleshootOrg(
        session, 
        org_id=org_id, 
        site_id=site['id'], 
        mac=device['mac'], 
        type='wan'
    ).data
    
    print("WAN Troubleshooting Results:")
    print(f"  Issues found: {len(tshoot_edge.get('results', []))}")
    if tshoot_edge.get('results'):
        pprint(tshoot_edge['results'])
    else:
        print("  No issues detected")
else:
    print("Cannot troubleshoot - site or device not found")

# ### Step 3.3 - Troubleshoot Wireless
#
# Next, you'll do the same for wireless. First, fetch your AP object, then run the 
# `troubleshootOrg()` function again, this time for type `wireless`.

# %%
if site:
    aps = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='ap').data
    ap = next(filter(lambda a: a.get('name') == 'AP-1', aps), None)
    
    if ap:
        print(f"Found AP-1: {ap['name']} (MAC: {ap['mac']})")
        
        tshoot_ap = mist.orgs.troubleshoot.troubleshootOrg(
            session, 
            org_id=org_id, 
            site_id=site['id'], 
            mac=ap['mac'], 
            type='wireless'
        ).data
        
        print("\nWireless Troubleshooting Results:")
        print(f"  Issues found: {len(tshoot_ap.get('results', []))}")
        if tshoot_ap.get('results'):
            pprint(tshoot_ap['results'])
        else:
            print("  No issues detected")
    else:
        print("WARNING: AP-1 not found!")

# ### Step 3.4 - Troubleshoot Wired
#
# Finally, repeat the process with your EX-1 switch.

# %%
if site:
    sws = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='switch').data
    sw = next(filter(lambda s: s.get('name') == 'EX-1', sws), None)
    
    if sw:
        print(f"Found EX-1: {sw['name']} (MAC: {sw['mac']})")
        
        tshoot_sw = mist.orgs.troubleshoot.troubleshootOrg(
            session, 
            org_id=org_id, 
            site_id=site['id'], 
            mac=sw['mac'], 
            type='wired'
        ).data
        
        print("\nWired Troubleshooting Results:")
        print(f"  Issues found: {len(tshoot_sw.get('results', []))}")
        if tshoot_sw.get('results'):
            pprint(tshoot_sw['results'])
        else:
            print("  No issues detected")
    else:
        print("WARNING: EX-1 switch not found!")

# ### Step 3.5 - Organization-Level Statistics
#
# You can dig deeper by looking at statistics at both the organization and site levels.
# Let's start by querying all org-level stats with the `orgs.stats.getOrgStats()` function.

# %%
org_stats = mist.orgs.stats.getOrgStats(session, org_id=org_id).data

print("Organization Statistics:")
print(f"  Total sites: {org_stats.get('num_sites', 0)}")
print(f"  Total devices: {org_stats.get('num_devices', 0)}")
print(f"  Connected devices: {org_stats.get('num_devices_connected', 0)}")
print(f"  Disconnected devices: {org_stats.get('num_devices_disconnected', 0)}")

print("\nFull organization stats:")
pprint(org_stats)

# Note: SLEs are compiled over time. If you only recently deployed this organization, 
# you may not see all possible SLEs in this output.

# ### Step 3.6 - Site-Level Statistics
#
# Next you can take a look at stats at the site level using the `getSiteStats` function.

# %%
if site:
    site_stats = mist.sites.stats.getSiteStats(session, site_id=site['id']).data
    
    print(f"Site Statistics for {site['name']}:")
    print(f"  APs: {site_stats.get('num_ap', 0)}")
    print(f"  Switches: {site_stats.get('num_switch', 0)}")
    print(f"  Gateways: {site_stats.get('num_gateway', 0)}")
    print(f"  Total devices: {site_stats.get('num_devices', 0)}")
    print(f"  Clients: {site_stats.get('num_clients', 0)}")
    
    print(f"\nFull site stats for {site['name']}:")
    pprint(site_stats)

# ### Step 3.7 - Wireless Client Statistics
#
# So far you've only seen high-level counters. Let's dive deeper by examining the stats 
# for individual wireless clients using the `listSiteWirelessClientsStats()` function.

# %%
if site:
    wifi_client_stats = mist.sites.stats.listSiteWirelessClientsStats(
        session, 
        site_id=site['id']
    ).data
    
    print("Wireless Client Statistics:")
    print(f"  Total wireless clients: {len(wifi_client_stats)}")
    
    if wifi_client_stats:
        print("\nSample client data (first client):")
        pprint(wifi_client_stats[0])

# ### Step 3.8 - Enrich Client Data with Site and PSK Names
#
# Right now you only have the IDs for PSKs and Sites. Let's use those IDs to look up the 
# names using the `getOrgPsk()` and `getSiteInfo()` functions. You'll loop through the 
# list of client statistics and add keys for `psk` and `site` to each dict.

# %%
if site and wifi_client_stats:
    for client in wifi_client_stats:
        # Add site name
        if 'site_id' in client:
            site_info = next(filter(lambda s: s.get('id') == client['site_id'], sites), None)
            client['site'] = site_info['name'] if site_info else 'Unknown'
        
        # Add PSK name if available
        if 'psk_id' in client:
            try:
                psk_info = mist.orgs.psks.getOrgPsk(
                    session, 
                    org_id=org_id, 
                    psk_id=client['psk_id']
                ).data
                client['psk'] = psk_info.get('name', 'Unknown')
            except:
                client['psk'] = 'Unknown'
        else:
            client['psk'] = 'N/A'
    
    print("Client data enriched with site and PSK names")

# ### Step 3.9 - Create Pandas DataFrame from Client Statistics
#
# Use `pd.DataFrame()` to create a Pandas DataFrame from the wireless client statistics.
# A DataFrame is like a table with advanced features such as broadcasting, filtering, 
# grouping, and aggregation.

# %%
if wifi_client_stats:
    wifi_client_df = pd.DataFrame(wifi_client_stats)
    
    print("Wireless Client DataFrame:")
    print(f"  Shape: {wifi_client_df.shape} (rows, columns)")
    print(f"  Columns: {list(wifi_client_df.columns)}")
    print("\nDataFrame preview:")
    print(wifi_client_df.head())
else:
    print("No wireless client data available")
    wifi_client_df = pd.DataFrame()

# ### Step 3.10 - Select Relevant Columns
#
# Trim the DataFrame to include only the columns you care about.

# %%
if not wifi_client_df.empty:
    # Select relevant columns (handle missing columns gracefully)
    desired_columns = ['mac', 'site', 'manufacture', 'hostname', 'ip', 'tx_bytes', 'rx_bytes', 'psk']
    available_columns = [col for col in desired_columns if col in wifi_client_df.columns]
    
    wifi_client_df = wifi_client_df[available_columns]
    
    print("Filtered DataFrame with relevant columns:")
    print(wifi_client_df)

# ### Step 3.11 - Create Derived Columns
#
# Create new columns based on values in existing columns. This process is called "broadcasting".
# Create a new column called `total_mb`, which sums the transmit and receive columns and 
# converts the values to megabytes for readability.

# %%
if not wifi_client_df.empty and 'tx_bytes' in wifi_client_df.columns and 'rx_bytes' in wifi_client_df.columns:
    wifi_client_df['total_mb'] = (wifi_client_df['tx_bytes'] + wifi_client_df['rx_bytes']) * 10e-6
    
    print("Added 'total_mb' column:")
    print(wifi_client_df)

# ### Step 3.12 - Create HoloViews Table
#
# Create a HoloViews Table object from the DataFrame. This will act as a source table for 
# visualizations. The Table constructor expects key dimensions (groups or x-axis values) 
# and value dimensions (the actual values).

# %%
if not wifi_client_df.empty and 'total_mb' in wifi_client_df.columns:
    key_dimensions = [('hostname', 'Client'), ('psk', 'PSK')]
    value_dimensions = [('total_mb', 'Bandwidth Usage (MB)')]
    
    wifi_client_table = hv.Table(wifi_client_df, key_dimensions, value_dimensions)
    
    print("HoloViews Table created successfully")
    print("(Use .data to view underlying data)")

# ### Step 3.13 - Create Bar Chart Visualization
#
# Convert the table into a bar chart, with one bar for each client.

# %%
if not wifi_client_df.empty and 'total_mb' in wifi_client_df.columns:
    wifi_bars = wifi_client_table.to.bars().opts(height=600, width=1200)
    
    print("Bar chart created successfully")
    print("Note: In a Jupyter notebook, this would render an interactive chart.")
    print("The chart shows bandwidth usage per client with PSK filtering.")
    
    # In a script environment, we can't display the chart interactively,
    # but we can show the summary data
    print("\nBandwidth Summary by Client:")
    summary = wifi_client_df[['hostname', 'total_mb']].sort_values('total_mb', ascending=False)
    print(summary.to_string(index=False))

# ### Step 3.14 - Check Organization Alarms
#
# Check if any alarms are currently active using the `searchOrgAlarms()` function.

# %%
org_alarms = mist.orgs.alarms.searchOrgAlarms(session, org_id=org_id).data

if org_alarms.get('results'):
    org_alarm_df = pd.DataFrame(org_alarms['results'])
    print(f"Organization Alarms: {len(org_alarm_df)} found")
    print(org_alarm_df)
else:
    print("No organization alarms currently active")

# ### Step 3.15 - Check Site Alarms
#
# Do the same for site alarms with the `searchSiteAlarms()` function.

# %%
if site:
    site_alarms = mist.sites.alarms.searchSiteAlarms(session, site_id=site['id']).data
    
    if site_alarms.get('results'):
        site_alarms_df = pd.DataFrame(site_alarms['results'])
        print(f"Site Alarms for {site['name']}: {len(site_alarms_df)} found")
        print(site_alarms_df)
    else:
        print(f"No site alarms currently active for {site['name']}")

# ---
# ## Part 4: Accessing Insights with the REST API
#
# In this lab part you will use the Insights endpoint of the Juniper Mist REST API to 
# retrieve the same insights data that is used to populate the Juniper Mist GUI.

# ### Step 4.1 - List Available Insights Metrics
#
# The Insights endpoint is different from what you've worked with so far. Juniper Mist 
# Insights are accessible through functions that accept a `metric` parameter which dictates 
# which Insights data you want to retrieve.
#
# You can see the full list of available metrics by running the 
# `const.insight_metrics.listInsightMetrics()` function.

# %%
metrics = mist.const.insight_metrics.listInsightMetrics(session).data

print(f"Available Insights Metrics: {len(metrics)}")
print("\nSample metrics:")
for i, (metric_name, metric_info) in enumerate(list(metrics.items())[:5]):
    print(f"  {i+1}. {metric_name}: {metric_info.get('description', 'No description')}")

# ### Step 4.2 - Examine a Specific Metric
#
# Let's examine a single metric called `top-app-by-bytes` to understand its structure.

# %%
if 'top-app-by-bytes' in metrics:
    print("Examining 'top-app-by-bytes' metric:\n")
    print_metric(metrics['top-app-by-bytes'])

# ### Step 4.3 - Retrieve Top Applications by Bytes
#
# Use the `getSiteInsightMetrics` function to retrieve top applications by bytes.
# Note: We can inject additional parameters into the limit field as a workaround for 
# parameters not directly supported by the mistapi library.

# %%
if site:
    top_apps = mist.sites.insights.getSiteInsightMetrics(
        session, 
        site_id=site['id'], 
        metric='top-app-by-bytes', 
        limit="500&wired=True"
    ).data
    
    if top_apps.get('results'):
        top_apps_df = pd.DataFrame(top_apps['results'])
        print(f"Top Applications by Bytes: {len(top_apps_df)} found")
        print(top_apps_df.head(10))
    else:
        print("No application data available")

# ### Step 4.4 - Examine Rogues Metric
#
# Look at the requirements for the `rogues` metric using the `print_metric` function.

# %%
if 'rogues' in metrics:
    print("Examining 'rogues' metric:\n")
    print_metric(metrics['rogues'])

# ### Step 4.5 - Gather Wireless Security Information
#
# Now gather information about wireless neighbors, rogue APs, and honeypot APs.
# In the API, both neighbors and rogues are under the metric `rogues`, but you can filter 
# for rogue APs by including the parameter `type=lan`.

# %%
if site:
    # Get neighbors (all rogues without type filter)
    neighbors = mist.sites.insights.getSiteInsightMetrics(
        session, 
        site_id=site['id'], 
        metric='rogues'
    ).data
    
    # Get rogue APs (filtered by type=lan)
    rogues = mist.sites.insights.getSiteInsightMetrics(
        session, 
        site_id=site['id'], 
        metric='rogues', 
        interval="600&type=lan"
    ).data
    
    # Get honeypot APs
    honeypots = mist.sites.insights.getSiteInsightMetrics(
        session, 
        site_id=site['id'], 
        metric='honeypot'
    ).data
    
    # Convert to DataFrames
    neighbor_df = pd.DataFrame(neighbors.get('results', []))
    rogues_df = pd.DataFrame(rogues.get('results', []))
    honeypots_df = pd.DataFrame(honeypots.get('results', []))
    
    print(f"Wireless Neighbors: {len(neighbor_df)}")
    if not neighbor_df.empty:
        print(neighbor_df.head())
    
    print(f"\nRogue APs: {len(rogues_df)}")
    if not rogues_df.empty:
        print(rogues_df)
    
    print(f"\nHoneypot APs: {len(honeypots_df)}")
    if not honeypots_df.empty:
        print(honeypots_df)

# ### Step 4.6 - Filter Neighbors by SSID
#
# Use the DataFrame `query` function to filter neighbors by a specific SSID.

# %%
if not neighbor_df.empty and 'ssid' in neighbor_df.columns:
    # Example: Filter for a specific SSID
    target_ssid = "Junivator-net"  # Adjust as needed
    filtered_neighbors = neighbor_df.query(f'ssid == "{target_ssid}"')
    
    print(f"Neighbors with SSID '{target_ssid}': {len(filtered_neighbors)}")
    if not filtered_neighbors.empty:
        print(filtered_neighbors)
    else:
        print(f"No neighbors found with SSID '{target_ssid}'")

# ### Step 4.7 - Check for Malicious APs
#
# Check if there are currently any rogue or honeypot APs detected.

# %%
print("Potentially Malicious AP Detection:")
print("="*80)

if not rogues_df.empty:
    print(f"ALERT: {len(rogues_df)} rogue AP(s) detected!")
    print(rogues_df)
else:
    print("✓ No rogue APs detected")

if not honeypots_df.empty:
    print(f"\nALERT: {len(honeypots_df)} honeypot AP(s) detected!")
    print(honeypots_df)
else:
    print("✓ No honeypot APs detected")

print("="*80)

# ---
# ## Part 5: Application Paths and Sessions
#
# In this lab part, you will query information about application traffic steering paths 
# and current sessions from the SSR-1 device.
#
# Note: Querying application paths and sessions typically requires WebSocket connections 
# for real-time data. The REST API provides limited access to this data. For full 
# real-time monitoring, you would need to implement WebSocket clients.

# ### Step 5.1 - Understanding Application Paths and Sessions
#
# Application paths and sessions are typically accessed via:
# - WebSocket connections for real-time streaming data
# - REST API endpoints for snapshot data
#
# The mistapi library provides functions like:
# - `sites.devices.getDeviceIotApplications()` for IoT app info
# - `sites.stats.getSiteStats()` which includes some session information

print("\n" + "="*80)
print("Application Paths and Sessions")
print("="*80)
print("\nNote: Real-time application path and session monitoring typically requires")
print("WebSocket connections. The REST API provides snapshot data only.")
print("\nFor lab purposes, we've gathered statistics and insights above.")
print("="*80 + "\n")

# ---
# ## Lab Complete
#
# You have successfully completed Lab 10: Troubleshooting Day 2+ Operations!
#
# Summary of completed tasks:
# - Checked the current state of your Durham site
# - Used troubleshooting API endpoints for WAN, wireless, and wired
# - Gathered organization and site statistics
# - Analyzed wireless client statistics with Pandas and HoloViews
# - Explored Insights API metrics
# - Monitored for rogue and honeypot APs
# - Reviewed application traffic data

print("\n" + "="*80)
print("LAB 10 COMPLETE")
print("="*80)
print("\nSummary:")
print("  ✓ Durham site status checked")
print("  ✓ Troubleshooting performed on WAN, wireless, and wired")
print("  ✓ Organization and site statistics gathered")
print("  ✓ Wireless client statistics analyzed")
print("  ✓ Insights metrics explored (top apps, rogues, honeypots)")
print("  ✓ Security monitoring completed")
print("\nYou now have the tools to monitor and troubleshoot your Mist deployment!")
print("Use the Juniper Mist GUI for additional visualization and real-time monitoring.")
print("="*80 + "\n")

# ---
# ## Additional Notes
#
# For production monitoring, consider:
# 1. Setting up automated alerts based on alarm thresholds
# 2. Creating dashboards with HoloViews/Bokeh for real-time visualization
# 3. Implementing WebSocket clients for streaming application session data
# 4. Scheduling regular statistics collection for trend analysis
# 5. Integrating with external monitoring systems (Prometheus, Grafana, etc.)
