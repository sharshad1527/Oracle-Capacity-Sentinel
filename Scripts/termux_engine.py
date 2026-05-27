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
SESSION_NAME = "oci_sentinel" # Unified tmux targeting

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


# Delay Control Variables - Enhanced for Range/Fixed support
delay_raw = cfg.get('RETRY_DELAY_CAPACITY', 180)
if isinstance(delay_raw, list) and len(delay_raw) >= 2:
    DELAY_MIN = int(delay_raw[0])
    DELAY_MAX = int(delay_raw[1])
    USE_RANGE = True
else:
    DELAY_FIXED = int(delay_raw)
    USE_RANGE = False

DELAY_RATE_LIMIT = int(cfg.get('RETRY_DELAY_RATE_LIMIT', 300))

def get_sleep_time():
    if USE_RANGE:
        return random.randint(DELAY_MIN, DELAY_MAX)
    return DELAY_FIXED


# Persistence & Analytics Initialization
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sentinel_stats.json')
stats = {'total_attempts': 0, 'capacity_errors': 0, 'rate_limits': 0}
last_save_time = time.time()

def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                stats = json.load(f)
        except: pass

def save_stats():
    global last_save_time
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
        last_save_time = time.time()
    except: pass

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Include attempt count if available
    prefix = f"[#{stats['total_attempts']}] " if stats['total_attempts'] > 0 else ""
    print(f"[{timestamp}] {prefix}{message}")
    sys.stdout.flush()

def send_notifications(server_name, server_id):
    # Discord
    if DISCORD_WEBHOOK:
        payload = {
            "content": "🎉 **Oracle Cloud Server Created! (Termux)**",
            "embeds": [{
                "title": "Sentinel Success",
                "color": 5763719,
                "fields": [
                    {"name": "Server Name", "value": server_name, "inline": True},
                    {"name": "OCID", "value": f"`{server_id}`", "inline": False},
                    {"name": "Shape", "value": OCI_SHAPE, "inline": True},
                    {"name": "Resources", "value": f"{OCI_OCPUS} OCPU / {OCI_MEMORY}GB RAM", "inline": True}
                ],
                "footer": {"text": "Oracle Capacity Sentinel (Mobile)"}
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
            f"🎉 *Oracle Cloud Server Created! (Termux)*\n\n"
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
    log("Initializing OCS (Termux Edition)...")
    os.system("termux-wake-lock") # Prevents Android CPU Deep Sleep
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

    load_stats()
    log("Stats loaded. Starting hunt loop...")
    
    try:
        while True:
            stats['total_attempts'] += 1
            capacity_error_hit = False
            rate_limit_hit_in_loop = False
            
            # Periodic Save (Hourly)
            if time.time() - last_save_time > 3600:
                save_stats()
                log("Analytics auto-saved to disk.")

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
                os.system('termux-notification --title "SENTINEL SUCCESS!" --content "Your Server is ready." --priority high --vibrate 1000')
                sys.stdout.write('\a'); sys.stdout.flush()
                return # Exits script entirely upon success
                
            except oci.exceptions.ServiceError as e:
                if e.status == 500 or "Out of host capacity" in str(e.message):
                    log(f"Capacity full in {ad}.")
                    capacity_error_hit = True; stats["capacity_errors"] += 1
                    consecutive_rate_limits = 0 # Reset strikes on successful capacity check
                    continue # Try next AD instantly without sleeping
                    
                elif e.status == 429 or "TooManyRequests" in str(e.code):
                    consecutive_rate_limits += 1
                    log(f"API Rate Limit Hit in {ad} (Strike {consecutive_rate_limits}).")
                    rate_limit_hit_in_loop = True; stats["rate_limits"] += 1
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
                log("WARNING: 3 Strikes. Pausing script. Awaiting your command via Notification...")
                
                lock_file = os.path.expanduser("~/.sentinel_paused")
                os.system(f"touch {lock_file}")
                
                action_continue = f"rm {lock_file}"
                action_kill = f"tmux kill-session -t {SESSION_NAME}" # Unified targeting
                
                noti_cmd = (
                    f'termux-notification --id "sentinel_alert" --title "⚠️ Sentinel Paused" '
                    f'--content "Hit limit 3 times. What should I do?" --priority high --vibrate 500,500 '
                    f'--button1 "Continue" --button1-action "{action_continue}" '
                    f'--button2 "Kill" --button2-action "{action_kill}" '
                    f'--on-delete "{action_continue}"'
                )
                os.system(noti_cmd)
                
                while os.path.exists(lock_file):
                    time.sleep(2)
                    
                log("Lock file removed via notification. Resuming Sentinel operation...")
                consecutive_rate_limits = 0 
            else:
                jitter_delay = random.randint(DELAY_RATE_LIMIT, int(DELAY_RATE_LIMIT * 1.5))
                log(f"Rate limited. Cycling queue in {jitter_delay}s (Jitter applied)...")
                time.sleep(jitter_delay)
                
        elif capacity_error_hit:
            sleep_time = get_sleep_time()
            log(f"All queried domains are full. Cycling queue in {sleep_time}s...")
            time.sleep(sleep_time)
        else:
            time.sleep(get_sleep_time())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[SENTINEL] Shutdown signal received. Saving analytics...")
        save_stats()
        print("[SENTINEL] Session saved. Goodbye!")
        sys.exit(0)
    except Exception as e:
        save_stats()
        print(f"\n[CRITICAL] Unexpected error: {e}")
        sys.exit(1)
