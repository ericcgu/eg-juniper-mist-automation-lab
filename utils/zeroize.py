"""
Zeroize utility for cleaning up Juniper Mist organization configurations.

This module provides functionality to remove all configurations from a Mist organization
while keeping devices adopted. It reverses the deployment order to ensure proper cleanup.
"""

from mistapi.api import v1 as mist
from cryptography import x509
from cryptography.hazmat.backends import default_backend


def zeroize_organization(session, org_id, verbose=True):
    """
    Remove all configurations from a Mist organization without releasing devices.
    
    This function deletes configurations in reverse deployment order:
    1. Clean site references
    2. Delete PSKs
    3. Delete WLAN rules
    4. Delete Labels (wxtags)
    5. Delete WLANs
    6. Delete RF Templates
    7. Delete WLAN Templates
    8. Delete NAC Rules
    9. Delete NAC Tags
    10. Remove AJMA Certificates
    11. Delete Switch Templates
    12. Delete WAN Edge Templates
    13. Delete Hub Profiles
    14. Delete VPNs
    15. Delete Networks
    16. Delete Applications
    17. Unassign Devices
    18. Delete Sites
    
    Args:
        session: Authenticated mistapi.APISession object
        org_id: Organization ID (UUID string)
        verbose: Print progress messages (default: True)
    
    Returns:
        dict: Summary of deleted items with counts for each category
    """
    
    def log(message):
        """Print message if verbose mode is enabled."""
        if verbose:
            print(message)
    
    summary = {
        'sites_cleaned': 0,
        'psks_deleted': 0,
        'wxrules_deleted': 0,
        'wxtags_deleted': 0,
        'wlans_deleted': 0,
        'rf_templates_deleted': 0,
        'wlan_templates_deleted': 0,
        'nac_rules_deleted': 0,
        'nac_tags_deleted': 0,
        'ajma_certs_removed': 0,
        'switch_templates_deleted': 0,
        'edge_templates_deleted': 0,
        'hub_profiles_deleted': 0,
        'vpns_deleted': 0,
        'networks_deleted': 0,
        'applications_deleted': 0,
        'devices_unassigned': 0,
        'sites_deleted': 0
    }
    
    # Step 1: Clean dead references from sites
    log("\n=== Step 1: Cleaning site template references ===")
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    for site in sites:
        payload = {
            'rftemplate_id': None,
            'aptemplate_id': None,
            'secpolicy_id': None,
            'alarmtemplate_id': None,
            'networktemplate_id': None,
            'gatewaytemplate_id': None,
            'sitetemplate_id': None
        }
        log(f"Cleaning template references from site: {site['name']}")
        mist.sites.sites.updateSiteInfo(session, site_id=site['id'], body=payload)
        summary['sites_cleaned'] += 1
    
    # Step 2: Delete PSKs
    log("\n=== Step 2: Deleting PSKs ===")
    psks = mist.orgs.psks.listOrgPsks(session, org_id=org_id).data
    for psk in psks:
        log(f"Deleting PSK: {psk['name']}")
        mist.orgs.psks.deleteOrgPsk(session, org_id=org_id, psk_id=psk['id'])
        summary['psks_deleted'] += 1
    
    # Step 3: Delete WLAN Rules
    log("\n=== Step 3: Deleting WLAN Rules ===")
    rules = mist.orgs.wxrules.listOrgWxRules(session, org_id=org_id).data
    for rule in rules:
        log(f"Deleting WLAN rule: {rule['id']}")
        mist.orgs.wxrules.deleteOrgWxRule(session, org_id=org_id, wxrule_id=rule['id'])
        summary['wxrules_deleted'] += 1
    
    # Step 4: Delete Labels (wxtags)
    log("\n=== Step 4: Deleting Labels ===")
    labels = mist.orgs.wxtags.listOrgWxTags(session, org_id=org_id).data
    for label in labels:
        log(f"Deleting label: {label['name']}")
        mist.orgs.wxtags.deleteOrgWxTag(session, org_id=org_id, wxtag_id=label['id'])
        summary['wxtags_deleted'] += 1
    
    # Step 5: Delete WLANs
    log("\n=== Step 5: Deleting WLANs ===")
    wlans = mist.orgs.wlans.listOrgWlans(session, org_id=org_id).data
    for wlan in wlans:
        log(f"Deleting WLAN: {wlan['ssid']}")
        mist.orgs.wlans.deleteOrgWlan(session, org_id=org_id, wlan_id=wlan['id'])
        summary['wlans_deleted'] += 1
    
    # Step 6: Delete RF Templates
    log("\n=== Step 6: Deleting RF Templates ===")
    rf_templates = mist.orgs.rftemplates.listOrgRfTemplates(session, org_id=org_id).data
    for rf in rf_templates:
        log(f"Deleting RF template: {rf['name']}")
        mist.orgs.rftemplates.deleteOrgRfTemplate(session, org_id=org_id, rftemplate_id=rf['id'])
        summary['rf_templates_deleted'] += 1
    
    # Step 7: Delete WLAN Templates
    log("\n=== Step 7: Deleting WLAN Templates ===")
    wlan_templates = mist.orgs.templates.listOrgTemplates(session, org_id=org_id).data
    for template in wlan_templates:
        log(f"Deleting WLAN template: {template['name']}")
        mist.orgs.templates.deleteOrgTemplate(session, org_id=org_id, template_id=template['id'])
        summary['wlan_templates_deleted'] += 1
    
    # Step 8: Delete NAC Rules
    log("\n=== Step 8: Deleting NAC Rules ===")
    nac_rules = mist.orgs.nacrules.listOrgNacRules(session, org_id=org_id).data
    for rule in nac_rules:
        log(f"Deleting NAC rule: {rule.get('name', rule['id'])}")
        mist.orgs.nacrules.deleteOrgNacRule(session, org_id=org_id, nacrule_id=rule['id'])
        summary['nac_rules_deleted'] += 1
    
    # Step 9: Delete NAC Tags
    log("\n=== Step 9: Deleting NAC Tags ===")
    nac_tags = mist.orgs.nactags.listOrgNacTags(session, org_id=org_id).data
    for tag in nac_tags:
        log(f"Deleting NAC tag: {tag['name']}")
        mist.orgs.nactags.deleteOrgNacTag(session, org_id=org_id, nactag_id=tag['id'])
        summary['nac_tags_deleted'] += 1
    
    # Step 10: Remove AJMA Certificates
    log("\n=== Step 10: Removing AJMA Certificates ===")
    try:
        org_settings = mist.orgs.setting.getOrgSettings(session, org_id=org_id).data
        nac = org_settings.get('mist_nac')
        
        if nac is not None:
            certs = nac.get('cacerts')
            if certs is not None:
                ajma_cert_indices = []
                for i, cert_str in enumerate(certs):
                    cert_bytes = cert_str.encode('utf-8')
                    cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
                    subject = cert.subject
                    cn = subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
                    if cn == 'ajma-CA':
                        ajma_cert_indices.append(i)
                        log(f"Found AJMA CA certificate at index {i}")
                
                # Keep only non-AJMA certs
                filtered_certs = [cert for i, cert in enumerate(certs) if i not in ajma_cert_indices]
                org_settings['mist_nac']['cacerts'] = filtered_certs
                mist.orgs.setting.updateOrgSettings(session, org_id=org_id, body=org_settings)
                summary['ajma_certs_removed'] = len(ajma_cert_indices)
    except Exception as e:
        log(f"Note: Could not remove AJMA certificates: {e}")
    
    # Step 11: Delete Switch Templates
    log("\n=== Step 11: Deleting Switch Templates ===")
    switch_templates = mist.orgs.networktemplates.listOrgNetworkTemplates(session, org_id=org_id).data
    for template in switch_templates:
        log(f"Deleting switch template: {template['name']}")
        mist.orgs.networktemplates.deleteOrgNetworkTemplate(
            session, 
            org_id=org_id, 
            networktemplate_id=template['id']
        )
        summary['switch_templates_deleted'] += 1
    
    # Step 12: Delete WAN Edge Templates
    log("\n=== Step 12: Deleting WAN Edge Templates ===")
    edge_templates = mist.orgs.gatewaytemplates.listOrgGatewayTemplates(session, org_id=org_id).data
    for template in edge_templates:
        log(f"Deleting WAN Edge template: {template['name']}")
        mist.orgs.gatewaytemplates.deleteOrgGatewayTemplate(
            session, 
            org_id=org_id, 
            gatewaytemplate_id=template['id']
        )
        summary['edge_templates_deleted'] += 1
    
    # Step 13: Delete Hub Profiles
    log("\n=== Step 13: Deleting Hub Profiles ===")
    hub_profiles = mist.orgs.deviceprofiles.listOrgDeviceProfiles(
        session, 
        org_id=org_id, 
        type='gateway'
    ).data
    
    for hub in hub_profiles:
        log(f"Deleting hub profile: {hub['name']}")
        # First unassign any devices
        try:
            devices = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='gateway').data
            assigned_devices = [d for d in devices if d.get('deviceprofile_id') == hub['id']]
            
            if assigned_devices:
                payload = {'macs': [d['mac'] for d in assigned_devices]}
                mist.orgs.deviceprofiles.unassignOrgDeviceProfile(
                    session, 
                    org_id=org_id, 
                    deviceprofile_id=hub['id'], 
                    body=payload
                )
        except Exception as e:
            log(f"Note: Could not unassign devices from hub profile: {e}")
        
        # Then delete the profile
        mist.orgs.deviceprofiles.deleteOrgDeviceProfile(
            session, 
            org_id=org_id, 
            deviceprofile_id=hub['id']
        )
        summary['hub_profiles_deleted'] += 1
    
    # Step 14: Delete VPNs
    log("\n=== Step 14: Deleting VPNs ===")
    vpns = mist.orgs.vpns.listOrgVpns(session, org_id=org_id).data
    for vpn in vpns:
        log(f"Deleting VPN: {vpn.get('name', vpn['id'])}")
        mist.orgs.vpns.deleteOrgVpn(session, org_id=org_id, vpn_id=vpn['id'])
        summary['vpns_deleted'] += 1
    
    # Step 15: Delete Networks
    log("\n=== Step 15: Deleting Networks ===")
    networks = mist.orgs.networks.listOrgNetworks(session, org_id=org_id).data
    for network in networks:
        log(f"Deleting network: {network['name']}")
        mist.orgs.networks.deleteOrgNetwork(session, org_id=org_id, network_id=network['id'])
        summary['networks_deleted'] += 1
    
    # Step 16: Delete Applications
    log("\n=== Step 16: Deleting Applications ===")
    apps = mist.orgs.services.listOrgServices(session, org_id=org_id).data
    for app in apps:
        log(f"Deleting application: {app['name']}")
        mist.orgs.services.deleteOrgService(session, org_id=org_id, service_id=app['id'])
        summary['applications_deleted'] += 1
    
    # Step 17: Unassign All Devices
    log("\n=== Step 17: Unassigning All Devices ===")
    aps = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='ap').data
    switches = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='switch').data
    edges = mist.orgs.inventory.getOrgInventory(session, org_id=org_id, type='gateway').data
    
    all_devices = aps + switches + edges
    for device in all_devices:
        if device.get('site_id'):  # Only unassign if assigned
            payload = {
                'op': 'unassign',
                'macs': [device['mac']]
            }
            log(f"Unassigning device: {device.get('name', device['mac'])}")
            mist.orgs.inventory.updateOrgInventoryAssignment(session, org_id=org_id, body=payload)
            summary['devices_unassigned'] += 1
    
    # Step 18: Delete Sites
    log("\n=== Step 18: Deleting Sites ===")
    sites = mist.orgs.sites.listOrgSites(session, org_id=org_id).data
    for site in sites:
        log(f"Deleting site: {site['name']}")
        mist.sites.sites.deleteSite(session, site_id=site['id'])
        summary['sites_deleted'] += 1
    
    # Print summary
    if verbose:
        log("\n" + "="*80)
        log("ZEROIZATION COMPLETE")
        log("="*80)
        log(f"Sites cleaned:           {summary['sites_cleaned']}")
        log(f"PSKs deleted:            {summary['psks_deleted']}")
        log(f"WLAN rules deleted:      {summary['wxrules_deleted']}")
        log(f"Labels deleted:          {summary['wxtags_deleted']}")
        log(f"WLANs deleted:           {summary['wlans_deleted']}")
        log(f"RF templates deleted:    {summary['rf_templates_deleted']}")
        log(f"WLAN templates deleted:  {summary['wlan_templates_deleted']}")
        log(f"NAC rules deleted:       {summary['nac_rules_deleted']}")
        log(f"NAC tags deleted:        {summary['nac_tags_deleted']}")
        log(f"AJMA certs removed:      {summary['ajma_certs_removed']}")
        log(f"Switch templates deleted:{summary['switch_templates_deleted']}")
        log(f"Edge templates deleted:  {summary['edge_templates_deleted']}")
        log(f"Hub profiles deleted:    {summary['hub_profiles_deleted']}")
        log(f"VPNs deleted:            {summary['vpns_deleted']}")
        log(f"Networks deleted:        {summary['networks_deleted']}")
        log(f"Applications deleted:    {summary['applications_deleted']}")
        log(f"Devices unassigned:      {summary['devices_unassigned']}")
        log(f"Sites deleted:           {summary['sites_deleted']}")
        log("="*80)
    
    return summary
