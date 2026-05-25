#!/bin/bash

# Configuration Map Fix
SESSION_NAME="oci_sentinel"
SCRIPT_NAME="Scripts/desktop_engine.py"

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}Error: 'tmux' is not installed.${NC}"
    echo "Please install it using your package manager."
    exit 1
fi

# Function to check if tmux session exists
is_running() {
    tmux has-session -t $SESSION_NAME 2>/dev/null
    return $?
}

show_menu() {
    clear
    echo -e "${YELLOW}==========================================${NC}"
    echo -e "   Oracle Cloud Control Panel (LINUX)     "
    echo -e "${YELLOW}==========================================${NC}"
    
    if is_running; then
        echo -e "Status: [ ${GREEN}RUNNING${NC} ]"
    else
        echo -e "Status: [ ${RED}STOPPED${NC} ]"
    fi
    echo "------------------------------------------"
    echo "1. Start Sentinel (Runs in background)"
    echo "2. Attach & View Live Logs"
    echo "3. Stop & Kill Sentinel"
    echo "4. Exit Menu"
    echo "------------------------------------------"
    echo -n "Select an option [1-4]: "
}

while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            if is_running; then
                echo -e "\n${YELLOW}Sentinel is already running!${NC}"
                sleep 2
            else
                echo -e "\n${GREEN}Starting Sentinel in the background...${NC}"
                tmux new-session -d -s $SESSION_NAME "python3 $SCRIPT_NAME; read -p 'Press Enter to exit...'"
                echo "Done!"
                sleep 2
            fi
            ;;
        2)
            if is_running; then
                echo -e "\n${YELLOW}Attaching to session...${NC}"
                echo -e "${RED}IMPORTANT: To detach and keep it running, press Ctrl+B, then let go and press D!${NC}"
                sleep 4
                tmux attach-session -t $SESSION_NAME
            else
                echo -e "\n${RED}Sentinel is not running. Start it first.${NC}"
                sleep 2
            fi
            ;;
        3)
            if is_running; then
                echo -e "\n${RED}Killing the Sentinel session...${NC}"
                tmux kill-session -t $SESSION_NAME
                echo "Stopped."
                sleep 2
            else
                echo -e "\n${YELLOW}Sentinel is not running.${NC}"
                sleep 2
            fi
            ;;
        4)
            echo -e "\nExiting Control Panel..."
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid option.${NC}"
            sleep 1
            ;;
    esac
done