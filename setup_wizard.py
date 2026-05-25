import json
import os
import sys
import subprocess

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

def get_ids_via_browser(config):
    clear_screen()
    print("=========================================================")
    print("      STEP 2: THE F12 BROWSER TRICK (THE EASY WAY)")
    print("=========================================================")
    print("We need to tell the Sentinel exactly what network and operating system")
    print("to use. The easiest way to get these IDs is directly from the browser.")
    print("\nRead these instructions carefully:")
    print("  1. Go to the Oracle Cloud Web Console -> Create Instance.")
    print("  2. Configure your server exactly how you want it.")
    print("     (e.g., Ubuntu 24.04, Ampere ARM, 4 OCPUs, 24GB RAM).")
    print("  3. BEFORE you click the 'Create' button, press F12 to open Developer Tools.")
    print("  4. Click the 'Network' tab in Developer Tools.")
    print("  5. Now, click the blue 'Create' button on the Oracle webpage.")
    print("     (It will fail with an 'Out of capacity' error. This is normal).")
    print("  6. Look in the Network tab for a red failing request named 'instances'. Click it.")
    print("  7. Look at the 'Payload' or 'Request' section of that network call.")
    print("  8. You will see a block of code containing all your server details.")
    print("=========================================================\n")
    
    # Image ID
    print("Look in the Payload for 'imageId'.")
    img_id = input(f"Paste your Image ID here (Press Enter to keep '{config.get('OCI_IMAGE_ID', '')}'): ").strip()
    if img_id: config["OCI_IMAGE_ID"] = img_id
    while not config.get("OCI_IMAGE_ID"):
        config["OCI_IMAGE_ID"] = input("⚠️ Image ID is required. Paste 'imageId': ").strip()

    # Subnet ID
    print("\nLook in the Payload for 'subnetId'.")
    sub_id = input(f"Paste your Subnet ID here (Press Enter to keep '{config.get('OCI_SUBNET_ID', '')}'): ").strip()
    if sub_id: config["OCI_SUBNET_ID"] = sub_id
    while not config.get("OCI_SUBNET_ID"):
        config["OCI_SUBNET_ID"] = input("⚠️ Subnet ID is required. Paste 'subnetId': ").strip()

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
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    else:
        config = {
            "OCI_SHAPE": "VM.Standard.A1.Flex", "OCI_OCPUS": 4, "OCI_MEMORY_IN_GBS": 24,
            "OCI_MAX_INSTANCES": 1, "OCI_BOOT_VOLUME_SIZE_IN_GBS": 200, "OCI_BOOT_VOLUME_VPUS_PER_GB": 10,
            "RETRY_DELAY_CAPACITY": 180, "RETRY_DELAY_RATE_LIMIT": 300
        }

    # Step 2: Grab SSH Key Automatically
    config["OCI_SSH_PUBLIC_KEY"] = handle_ssh_key()
    
    # Step 3: F12 Trick for OCIDs
    get_ids_via_browser(config)
    
    # Step 4: Configure Timers
    configure_delays(config)
    
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