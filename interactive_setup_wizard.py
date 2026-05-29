from datetime import datetime
import json
import os
import sys
import subprocess

try:
    import oci
except ImportError:
    print("⚠️ OCI Python SDK not found. Please run 'pip install oci' first.")
    sys.exit(1)

CONFIG_FILE = "config.json"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def press_enter_to_continue():
    input("\nPress [ENTER] to continue...")

def check_oci_auth():
    oci_config_path = os.path.expanduser("~/.oci/config")
    
    if not os.path.exists(oci_config_path):
        clear_screen()
        print("=========================================================")
        print(" 🛑 STEP 1: ORACLE CLOUD API AUTHENTICATION REQUIRED 🛑")
        print("=========================================================")
        print("I detected that this machine is not connected to your Oracle account yet.")
        print("\nFollow these EXACT steps before we continue:")
        print("  1. Open a NEW terminal window (do not close this one).")
        print("  2. Type this command:  oci setup config")
        print("  3. It will ask for your User OCID and Tenancy OCID. You can find these")
        print("     on the Oracle website under Profile -> Tenancy / User settings.")
        print("  4. It will ask about generating an RSA key pair. Say YES (Y).")
        print("  5. It will tell you the path to your new public key")
        print("     (usually ~/.oci/oci_api_key_public.pem). Open that file and copy the text.")
        print("  6. Go to the Oracle Website -> Profile -> User Settings -> API Keys.")
        print("  7. Click 'Add API Key', select 'Paste Public Key', and paste the text.")
        print("  8. Once added, come back to this window.")
        print("=========================================================")
        
        while not os.path.exists(oci_config_path):
            input("\nPress [ENTER] ONLY when you have completed all 8 steps...")
            if not os.path.exists(oci_config_path):
                print("⚠️ I still can't find ~/.oci/config. Please run 'oci setup config' first.")
        
        print("\n✅ OCI Authentication verified!")
        import time
        time.sleep(2)

def handle_ssh_key():
    """Automatically finds or generates an SSH key for the server."""
    ssh_dir = os.path.expanduser("~/.ssh")
    rsa_pub = os.path.join(ssh_dir, "id_rsa.pub")
    ed_pub = os.path.join(ssh_dir, "id_ed25519.pub")
    
    if os.path.exists(ed_pub):
        with open(ed_pub, "r") as f: return f.read().strip()
    if os.path.exists(rsa_pub):
        with open(rsa_pub, "r") as f: return f.read().strip()
        
    print("\n[INFO] No SSH key found on this system. Generating one automatically...")
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
        
    # Generate RSA key without a passphrase quietly
    try:
        subprocess.run(
            ['ssh-keygen', '-t', 'rsa', '-b', '2048', '-N', '', '-f', os.path.join(ssh_dir, 'id_rsa')],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        with open(rsa_pub, "r") as f: 
            key = f.read().strip()
            print("✅ SSH Key generated successfully!")
            return key
    except Exception as e:
        print(f"⚠️ Could not auto-generate SSH key: {e}")
        return input("Please manually paste your SSH Public Key (ssh-rsa...): ").strip()

def discover_network(config):
    clear_screen()
    print("=========================================================")
    print("      STEP 2: AUTOMATIC NETWORK DISCOVERY")
    print("=========================================================")
    print("Fetching your Virtual Cloud Networks (VCNs)...")
    
    try:
        oci_cfg = oci.config.from_file()
        network_client = oci.core.VirtualNetworkClient(oci_cfg)
        compartment_id = oci_cfg["tenancy"]
        
        vcns = network_client.list_vcns(compartment_id=compartment_id).data
        
        if not vcns:
            print("❌ No VCNs found in your account. Please create one in the Oracle Console first.")
            sys.exit(1)
            
        print("\nSelect a VCN:")
        for i, vcn in enumerate(vcns):
            print(f"  [{i+1}] {vcn.display_name} ({vcn.id})")
            
        vcn_choice = -1
        while vcn_choice < 0 or vcn_choice >= len(vcns):
            try:
                user_input = input(f"\nEnter choice (1-{len(vcns)}): ")
                if not user_input: continue
                vcn_choice = int(user_input) - 1
            except ValueError:
                pass
                
        selected_vcn = vcns[vcn_choice]
        print(f"✅ Selected VCN: {selected_vcn.display_name}")
        
        print("\nFetching subnets for this VCN...")
        subnets = network_client.list_subnets(compartment_id=compartment_id, vcn_id=selected_vcn.id).data
        
        if not subnets:
            print(f"❌ No subnets found in VCN '{selected_vcn.display_name}'.")
            sys.exit(1)
            
        print("\nSelect a Subnet:")
        for i, subnet in enumerate(subnets):
            type_str = "Public" if not subnet.prohibit_public_ip_on_vnic else "Private"
            print(f"  [{i+1}] {subnet.display_name} [{type_str}] ({subnet.id})")
            
        sub_choice = -1
        while sub_choice < 0 or sub_choice >= len(subnets):
            try:
                user_input = input(f"\nEnter choice (1-{len(subnets)}): ")
                if not user_input: continue
                sub_choice = int(user_input) - 1
            except ValueError:
                pass
                
        selected_subnet = subnets[sub_choice]
        config["OCI_SUBNET_ID"] = selected_subnet.id
        print(f"✅ Selected Subnet: {selected_subnet.display_name}")
        
        # Public IP Logic
        if not selected_subnet.prohibit_public_ip_on_vnic:
            choice = input("\nDo you want to assign a Public IP automatically? (y/n) [Default y]: ").lower().strip()
            config["OCI_ASSIGN_PUBLIC_IP"] = False if choice == 'n' else True
        else:
            print("\n⚠️ This is a Private Subnet. Public IP assignment is disabled.")
            config["OCI_ASSIGN_PUBLIC_IP"] = False

    except Exception as e:
        print(f"❌ Error during network discovery: {str(e)}")
        print("\nFalling back to manual entry...")
        config["OCI_SUBNET_ID"] = input("Paste your Subnet OCID: ").strip()

    # Image ID (Kept manual for now)
    print("\n" + "="*55)
    print("Now, we need the Image OCID (Operating System).")
    print("You can still find this using the F12 trick or the Oracle Console.")
    img_id = input(f"Paste Image OCID (Press Enter to keep '{config.get('OCI_IMAGE_ID', '')}'): ").strip()
    if img_id: config["OCI_IMAGE_ID"] = img_id
    while not config.get("OCI_IMAGE_ID"):
        config["OCI_IMAGE_ID"] = input("⚠️ Image OCID is required: ").strip()

    # Display Name
    print("\nWhat should we name the server?")
    def_name = config.get("OCI_DISPLAY_NAME", f"instance-{datetime.now().strftime('%Y%m%d-%H%M')}")
    name = input(f"Server Name [Default {def_name}]: ").strip()
    config["OCI_DISPLAY_NAME"] = name if name else def_name

def configure_delays(config):
    clear_screen()
    print("=========================================================")
    print("             STEP 3: HUNTING DELAYS & TIMERS")
    print("=========================================================")
    print("How aggressive should the Sentinel be? (Leave blank for defaults)")
    
    def_cap = config.get("RETRY_DELAY_CAPACITY", 180)
    cap = input(f"\nCapacity Check Delay (Seconds) [Default {def_cap}]: ").strip()
    config["RETRY_DELAY_CAPACITY"] = int(cap) if cap.isdigit() else def_cap
    
    def_rate = config.get("RETRY_DELAY_RATE_LIMIT", 300)
    rate = input(f"Rate Limit Pause (Seconds) [Default {def_rate}]: ").strip()
    config["RETRY_DELAY_RATE_LIMIT"] = int(rate) if rate.isdigit() else def_rate
    
    def_vol = config.get("OCI_BOOT_VOLUME_SIZE_IN_GBS", 200)
    vol = input(f"Boot Volume Size (GB) [Default {def_vol}]: ").strip()
    config["OCI_BOOT_VOLUME_SIZE_IN_GBS"] = int(vol) if vol.isdigit() else def_vol

def configure_notifications(config):
    clear_screen()
    print("=========================================================")
    print("             STEP 4: NOTIFICATIONS (OPTIONAL)")
    print("=========================================================")
    print("The Sentinel can notify you when a server is created.")
    
    # Discord
    webhook = input(f"\nDiscord Webhook URL (Leave blank to skip): ").strip()
    config["DISCORD_WEBHOOK_URL"] = webhook if webhook else config.get("DISCORD_WEBHOOK_URL", "")
    
    # Telegram
    tg_token = input(f"Telegram Bot Token (Leave blank to skip): ").strip()
    if tg_token:
        config["TELEGRAM_BOT_TOKEN"] = tg_token
        config["TELEGRAM_CHAT_ID"] = input("Telegram Chat ID: ").strip()
    else:
        config["TELEGRAM_BOT_TOKEN"] = config.get("TELEGRAM_BOT_TOKEN", "")
        config["TELEGRAM_CHAT_ID"] = config.get("TELEGRAM_CHAT_ID", "")

def main():
    clear_screen()
    print("=========================================================")
    print("      Oracle Capacity Sentinel - Interactive Setup")
    print("=========================================================")
    print("This wizard will configure your Sentinel to hunt for free servers.\n")
    press_enter_to_continue()
    
    # Step 1: Ensure OCI CLI is configured
    check_oci_auth()
    
    # Load existing config or initialize a new one
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except:
            config = {}
    else:
        config = {
            "OCI_SHAPE": "VM.Standard.A1.Flex", "OCI_OCPUS": 4, "OCI_MEMORY_IN_GBS": 24,
            "OCI_MAX_INSTANCES": 1, "OCI_BOOT_VOLUME_SIZE_IN_GBS": 200, "OCI_BOOT_VOLUME_VPUS_PER_GB": 10,
            "RETRY_DELAY_CAPACITY": 180, "RETRY_DELAY_RATE_LIMIT": 300
        }

    # Step 2: Grab SSH Key Automatically
    config["OCI_SSH_PUBLIC_KEY"] = handle_ssh_key()
    
    # Step 3: Automatic Network Discovery
    discover_network(config)
    
    # Step 4: Configure Timers
    configure_delays(config)

    # Step 5: Notifications
    configure_notifications(config)
    
    # Save Configuration
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    clear_screen()
    print("=========================================================")
    print("                 🎉 SETUP COMPLETE! 🎉")
    print("=========================================================")
    print(f"Your configuration has been saved to '{CONFIG_FILE}'.")
    print("You can now start hunting using your OS-specific manager:")
    print("   Windows: double-click 'windows_manager.bat'")
    print("   Linux/Termux: run './linux_manager.bash' or './termux_manager.bash'")
    print("=========================================================")

if __name__ == "__main__":
    main()
