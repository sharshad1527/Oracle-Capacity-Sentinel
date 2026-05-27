import os
import json
import time
import sys
import oci
import urllib.request
import random
from datetime import datetime

# =========================================================================
#  CONFIGURATION & MEMORY INITIALIZATION
# =========================================================================
# Resolves path to config.json in the parent (root) directory
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')

try:
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
except FileNotFoundError:
    print(f"ERROR: {CONFIG_FILE} not found. Please run the setup wizard first.")
    sys.exit(1)

# Load variables into memory once to prevent disk I/O in the loop
OCI_SHAPE = cfg.get('OCI_SHAPE', 'VM.Standard.A1.Flex')
OCI_OCPUS = float(cfg.get('OCI_OCPUS', 4))
OCI_MEMORY = float(cfg.get('OCI_MEMORY_IN_GBS', 24))
OCI_MAX_INSTANCES = int(cfg.get('OCI_MAX_INSTANCES', 1))
OCI_SUBNET_ID = cfg['OCI_SUBNET_ID']
OCI_IMAGE_ID = cfg['OCI_IMAGE_ID']
OCI_SSH_KEY = cfg['OCI_SSH_PUBLIC_KEY']
BOOT_VOL_SIZE = int(cfg.get('OCI_BOOT_VOLUME_SIZE_IN_GBS', 200))
BOOT_VOL_VPUS = int(cfg.get('OCI_BOOT_VOLUME_VPUS_PER_GB', 10))
OCI_DISPLAY_NAME = cfg.get('OCI_DISPLAY_NAME', 'HAIVA')
OCI_ASSIGN_PUBLIC_IP = cfg.get('OCI_ASSIGN_PUBLIC_IP', True)
OCI_ASSIGN_IPV6_IP = cfg.get('OCI_ASSIGN_IPV6_IP', False)
DISCORD_WEBHOOK = cfg.get('DISCORD_WEBHOOK_URL', '')
TG_TOKEN = cfg.get('TELEGRAM_BOT_TOKEN', '')
TG_CHAT_ID = cfg.get('TELEGRAM_CHAT_ID', '')

# Delay Control Variables
DELAY_CAPACITY = int(cfg.get('RETRY_DELAY_CAPACITY', 180))
DELAY_RATE_LIMIT = int(cfg.get('RETRY_DELAY_RATE_LIMIT', 300))

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def send_notifications(server_name, server_id):
    # Discord
    if DISCORD_WEBHOOK:
        payload = {
            "content": "🎉 **Oracle Cloud Server Created!**",
            "embeds": [{
                "title": "Sentinel Success",
                "color": 5763719,
                "fields": [
                    {"name": "Server Name", "value": server_name, "inline": True},
                    {"name": "OCID", "value": f"`{server_id}`", "inline": False},
                    {"name": "Shape", "value": OCI_SHAPE, "inline": True},
                    {"name": "Resources", "value": f"{OCI_OCPUS} OCPU / {OCI_MEMORY}GB RAM", "inline": True}
                ],
                "footer": {"text": "Oracle Capacity Sentinel"}
            }]
        }
        try:
            req = urllib.request.Request(DISCORD_WEBHOOK, data=json.dumps(payload).encode('utf-8'), 
                                       headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response: pass
        except Exception as e: log(f"Discord Notification Error: {str(e)}")

    # Telegram
    if TG_TOKEN and TG_CHAT_ID:
        text = (
            f"🎉 *Oracle Cloud Server Created!*\n\n"
            f"*Name:* {server_name}\n"
            f"*OCID:* `{server_id}`\n"
            f"*Shape:* {OCI_SHAPE}\n"
            f"*Resources:* {OCI_OCPUS} OCPU / {OCI_MEMORY}GB RAM"
        )
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), 
                                       headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response: pass
        except Exception as e: log(f"Telegram Notification Error: {str(e)}")

def main():
    log("Initializing OCS (Desktop Edition)...")
    try:
        oci_config = oci.config.from_file()
        compartment_id = oci_config["tenancy"]
    except Exception as e:
        log(f"Config Initialization Error: {str(e)}")
        return

    compute_client = oci.core.ComputeClient(oci_config)
    identity_client = oci.identity.IdentityClient(oci_config)

    log(f"Verifying target resource status for shape {OCI_SHAPE}...")
    try:
        instances_data = compute_client.list_instances(compartment_id=compartment_id).data
        active_instances = [i for i in instances_data if i.lifecycle_state != "TERMINATED" and i.shape == OCI_SHAPE]
        if len(active_instances) >= OCI_MAX_INSTANCES:
            log(f"HALT: Limit met. Already have {len(active_instances)} instance(s) running.")
            return
    except Exception as e:
        log(f"Failed to query account instances: {str(e)}")
        return

    try:
        ad_data = identity_client.list_availability_domains(compartment_id=compartment_id).data
        availability_domains = [ad.name for ad in ad_data]
    except Exception as e:
        log(f"Failed to query Availability Domains: {str(e)}")
        return

    shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=OCI_OCPUS, memory_in_gbs=OCI_MEMORY)
    create_vnic_details = oci.core.models.CreateVnicDetails(
        subnet_id=OCI_SUBNET_ID, 
        assign_public_ip=OCI_ASSIGN_PUBLIC_IP, 
        assign_private_dns_record=True,
        assign_ipv6_ip=OCI_ASSIGN_IPV6_IP
    )
    source_details = oci.core.models.InstanceSourceViaImageDetails(
        source_type="image", image_id=OCI_IMAGE_ID, boot_volume_size_in_gbs=BOOT_VOL_SIZE, boot_volume_vpus_per_gb=BOOT_VOL_VPUS
    )

    log("Deployment structure compiled securely in memory. Starting hunt loop.")
    consecutive_rate_limits = 0

    while True:
        capacity_error_hit = False
        rate_limit_hit_in_loop = False

        for ad in availability_domains:
            launch_blueprint = oci.core.models.LaunchInstanceDetails(
                compartment_id=compartment_id, display_name=OCI_DISPLAY_NAME,
                shape=OCI_SHAPE, shape_config=shape_config, source_details=source_details, 
                create_vnic_details=create_vnic_details, metadata={"ssh_authorized_keys": OCI_SSH_KEY}, 
                availability_domain=ad
            )
            
            try:
                log(f"Attempting launch in domain {ad}...")
                response = compute_client.launch_instance(launch_instance_details=launch_blueprint)
                server = response.data
                
                log("\n" + "="*55 + f"\nSUCCESS: SERVER CREATED!\nName: {server.display_name}\nOCID: {server.id}\n" + "="*55)
                send_notifications(server.display_name, server.id)
                sys.stdout.write('\a'); sys.stdout.flush() # Terminal Beep
                return # Exits script entirely upon success
                
            except oci.exceptions.ServiceError as e:
                if e.status == 500 or "Out of host capacity" in str(e.message):
                    log(f"Capacity full in {ad}.")
                    capacity_error_hit = True
                    consecutive_rate_limits = 0 # Reset strikes on successful capacity check
                    continue # Try next AD instantly without sleeping
                    
                elif e.status == 429 or "TooManyRequests" in str(e.code):
                    consecutive_rate_limits += 1
                    log(f"API Rate Limit Hit in {ad} (Strike {consecutive_rate_limits}).")
                    rate_limit_hit_in_loop = True
                    break # Stop checking ADs, go straight to sleep/pause
                else:
                    log(f"CRITICAL API EXCEPTION [{e.status}]: {e.message.strip()}")
                    return
            except Exception as e:
                log(f"Network transport drop: {str(e)}")
                capacity_error_hit = True
                continue

        # Post-AD Loop Delay & Notification Handling
        if rate_limit_hit_in_loop:
            if consecutive_rate_limits >= 3:
                log("\n=======================================================")
                log("⚠️ WARNING: 3 Consecutive Rate Limits Hit.")
                log("=======================================================")
                input("Press [ENTER] to resume hunting, or press [Ctrl+C] to quit...")
                log("Resuming Sentinel operation...")
                consecutive_rate_limits = 0 
            else:
                jitter_delay = random.randint(DELAY_RATE_LIMIT, int(DELAY_RATE_LIMIT * 1.5))
                log(f"Rate limited. Cycling queue in {jitter_delay}s (Jitter applied)...")
                time.sleep(jitter_delay)
                
        elif capacity_error_hit:
            jitter_delay = random.randint(DELAY_CAPACITY, int(DELAY_CAPACITY * 1.5))
            log(f"All queried domains are full. Cycling queue in {jitter_delay}s (Jitter applied)...")
            time.sleep(jitter_delay)
        else:
            jitter_delay = random.randint(DELAY_CAPACITY, int(DELAY_CAPACITY * 1.5))
            time.sleep(jitter_delay)

if __name__ == "__main__":
    main()
