#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}==========================================${NC}"
echo -e "      OCS Linux Environment Installer     "
echo -e "${YELLOW}==========================================${NC}"
echo ""

echo "Detecting package manager and installing system dependencies (tmux, python3, openssl)..."

if command -v apt &> /dev/null; then
    sudo apt update
    sudo apt install -y python3 python3-pip tmux openssl
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3 python3-pip tmux openssl
elif command -v yum &> /dev/null; then
    sudo yum install -y python3 python3-pip tmux openssl
else
    echo "Could not detect apt, dnf, or yum. Please install python3, pip, tmux, and openssl manually."
fi

echo -e "\n${YELLOW}Installing Oracle Cloud SDK...${NC}"
python3 -m pip install --user --upgrade pip
python3 -m pip install --user oci

echo -e "\n${GREEN}[SUCCESS] All dependencies installed!${NC}"
echo "Cleaning up environment files..."

# Clean up OS files
mkdir -p otherOSmanagers
[ -f windows_manager.bat ] && mv windows_manager.bat otherOSmanagers/
[ -f termux_manager.bash ] && mv termux_manager.bash otherOSmanagers/
[ -f windows_installer.bat ] && mv windows_installer.bat otherOSmanagers/
[ -f termux_installer.bash ] && mv termux_installer.bash otherOSmanagers/

read -p "Press Enter to start the Interactive Setup Wizard..."
python3 interactive_setup_wizard.py

echo -e "\n${GREEN}Setup Complete! You can now use './linux_manager.bash'.${NC}"
echo "Archiving installer..."
# Move itself
mv "$0" otherOSmanagers/