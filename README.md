# Oracle Capacity Sentinel (OCS)

A robust, cross-platform automation engine designed to securely provision Oracle Cloud "Always Free" Ampere A1 Compute instances by persistently monitoring and bypassing "Out of host capacity" (HTTP 500) data center errors.

## The "Senior Dev" Recommendation: Upgrade to PAYG

Before you spend days or weeks running this script to snipe a server, **you should highly consider upgrading your Oracle Cloud account to "Pay As You Go" (PAYG).**

Oracle prioritizes paying accounts for hardware allocation. PAYG users rarely experience the "Out of host capacity" error.

**The Best Part:** Upgrading to PAYG requires a $100 authorization hold (which is refunded), but as long as you provision resources strictly within the "Always Free" tier limits (4 ARM OCPUs, 24GB RAM, 200GB Boot Volume), **you will never actually be billed.**

*Use this script only if you are strictly unable or unwilling to link a credit card for the PAYG upgrade.*

## The Problem & The Solution

Oracle Cloud's Always Free tier offers an incredible 4-Core ARM instance with 24GB of RAM. However, high-demand data centers (like `ap-hyderabad-1` or `us-ashburn-1`) frequently return an **"Out of host capacity"** error to free-tier users.

**Oracle Capacity Sentinel (OCS)** solves this by automating the provisioning requests. Rather than relying on heavy, outdated PHP stacks or scripts that drain your laptop battery, OCS is built for modern cross-platform environments (including headless mobile via Android Termux).

### Key Features

* **Universal Architecture:** Native support for Windows (CMD), Linux (Bash), and Android (Termux).

* **Smart Rate Limit Defense:** Features a "3-Strike" mitigation engine. If the script hits Oracle's `429 TooManyRequests` firewall three times consecutively, it automatically pauses execution to protect your account.

* **Zero-Touch SSH:** Automatically scans for or generates local RSA keys and injects them directly into your deployment payload. No more manual key juggling.

* **Auto-Cleaning Setup Wizard:** An interactive Python wizard guides you through the setup, verifies your API authentication, and auto-archives setup files to keep your workspace clean.

* **Headless Background Execution:** Linux and Termux environments utilize native `tmux` wrappers, allowing the Sentinel to run indefinitely in the background with near-zero resource/battery drain.

## Installation & Setup

### 1. Clone or Download the Repository

Download and extract this repository to your machine or Android device.

### 2. Run the Environment Installer

The repository includes OS-specific installers that will automatically download dependencies (`oci` SDK, `tmux`, etc.), clean up irrelevant files for other operating systems, and launch the Setup Wizard.

* **Windows:** Double-click `windows_installer.bat`

* **Linux:** Run `bash linux_installer.bash`

* **Android (Termux):** Run `bash termux_installer.bash`

### 3. The Interactive Setup Wizard

The installer will seamlessly hand you off to the `interactive_setup_wizard.py`. The wizard will:

1. Verify that your machine is authenticated with the Oracle CLI (`oci setup config`).

2. Auto-generate your SSH keys.

3. Guide you through the "F12 Browser Trick" to easily grab your `Image ID` and `Subnet ID` directly from the Oracle Web Console without writing complex CLI queries.

4. Configure your API request delay timers.

## Usage (The Control Panel)

Once setup is complete, your workspace will be clean, and your configuration will be saved in `config.json`.

Launch your OS-specific manager to control the Sentinel:

* **Windows:** `windows_manager.bat`

* **Linux:** `./linux_manager.bash`

* **Termux:** `./termux_manager.bash`

### Manager Options:

1. **Start Sentinel:** Spawns the monitor. On Linux/Termux, this runs detached in the background. On Windows, it spawns a dedicated tracking window.

2. **Attach & View Live Logs:** Connects to the running session to view real-time API output. *(On Linux/Termux, press `Ctrl+B`, then `D` to safely detach without killing the script).*

3. **Stop & Kill:** Gracefully terminates the monitoring process.

## Disclaimer & Liability

Automating API requests against Oracle Cloud carries an inherent risk of account suspension or termination. While OCS is designed with conservative rate-limiting and strike-defense mechanisms to mimic organic retry behavior, it is ultimately a brute-force tool.

**You assume all risks associated with the use of this software. The authors are not responsible for any banned accounts, lost data, or revoked Oracle Cloud access.**