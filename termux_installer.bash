#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}==========================================${NC}"
echo -e "     OCS Termux Environment Installer     "
echo -e "${YELLOW}==========================================${NC}"
echo ""

echo "Updating Termux repositories..."
pkg update -y && pkg upgrade -y

echo -e "\n${YELLOW}Installing core system dependencies (python, tmux, termux-api, openssl)...${NC}"
pkg install -y python tmux termux-api openssl

echo -e "\n${YELLOW}Installing Oracle Cloud SDK...${NC}"
python -m pip install --upgrade pip
python -m pip install oci

echo -e "\n${GREEN}[SUCCESS] All dependencies installed!${NC}"
echo "Cleaning up environment files..."

# Clean up OS files
mkdir -p otherOSmanagers
[ -f windows_manager.bat ] && mv windows_manager.bat otherOSmanagers/
[ -f linux_manager.bash ] && mv linux_manager.bash otherOSmanagers/
[ -f windows_installer.bat ] && mv windows_installer.bat otherOSmanagers/
[ -f linux_installer.bash ] && mv linux_installer.bash otherOSmanagers/

read -p "Press Enter to start the Interactive Setup Wizard..."
python interactive_setup_wizard.py

echo -e "\n${GREEN}Setup Complete! You can now use './termux_manager.bash'.${NC}"
echo "Archiving installer..."
# Move itself
mv "$0" otherOSmanagers/