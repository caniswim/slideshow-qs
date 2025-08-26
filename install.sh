#!/bin/bash
#
# Wallpaper Changer Installation Script for Arch Linux
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation directories
INSTALL_DIR="/usr/local/share/wallpaper-changer"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo -e "${GREEN}===================================${NC}"
echo -e "${GREEN}Wallpaper Changer Installation${NC}"
echo -e "${GREEN}===================================${NC}"
echo

# Check if running on Arch Linux
if [ ! -f /etc/arch-release ]; then
    echo -e "${YELLOW}Warning: This script is designed for Arch Linux${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for required dependencies
echo -e "${GREEN}Checking dependencies...${NC}"
MISSING_DEPS=""

# Check Python
if ! command -v python3 &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS python"
fi

# Check jq
if ! command -v jq &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS jq"
fi

# Check PyQt6
if ! python3 -c "import PyQt6" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS python-pyqt6"
fi

# Check Pillow
if ! python3 -c "import PIL" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS python-pillow"
fi

# Check numpy (optional, for better statistics)
if ! python3 -c "import numpy" 2>/dev/null; then
    echo -e "${YELLOW}Note: python-numpy not installed (optional for statistics)${NC}"
fi

if [ ! -z "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}Missing dependencies:${MISSING_DEPS}${NC}"
    echo -e "${GREEN}Installing dependencies...${NC}"
    sudo pacman -S --needed $MISSING_DEPS
fi

# Create installation directory
echo -e "${GREEN}Creating installation directories...${NC}"
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR/assets"

# Copy application files
echo -e "${GREEN}Installing application files...${NC}"
sudo cp main.py "$INSTALL_DIR/"
sudo cp gallery_window.py "$INSTALL_DIR/"
sudo cp gallery_window_modern.py "$INSTALL_DIR/"
sudo cp wallpaper_manager.py "$INSTALL_DIR/"
sudo cp config_manager.py "$INSTALL_DIR/"
sudo cp wallpaper_metadata.py "$INSTALL_DIR/"
sudo cp wallpaper_analyzer.py "$INSTALL_DIR/"
sudo cp settings_dialog_modern.py "$INSTALL_DIR/"

# Copy assets if they exist
if [ -d "assets" ]; then
    sudo cp -r assets/* "$INSTALL_DIR/assets/" 2>/dev/null || true
fi

# Install launcher script
echo -e "${GREEN}Installing launcher script...${NC}"
sudo cp wallpaper-changer "$BIN_DIR/"
sudo chmod +x "$BIN_DIR/wallpaper-changer"

# Install desktop entry
echo -e "${GREEN}Installing desktop entry...${NC}"
sudo cp wallpaper-changer.desktop "$DESKTOP_DIR/"
sudo chmod 644 "$DESKTOP_DIR/wallpaper-changer.desktop"

# Update desktop database
echo -e "${GREEN}Updating desktop database...${NC}"
if command -v update-desktop-database &> /dev/null; then
    sudo update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# Create systemd service for autostart (optional)
echo
read -p "Do you want to enable autostart on login? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Creating systemd user service...${NC}"
    
    mkdir -p "$SYSTEMD_USER_DIR"
    
    cat > "$SYSTEMD_USER_DIR/wallpaper-changer.service" << EOF
[Unit]
Description=Wallpaper Changer System Tray Application
After=graphical-session.target

[Service]
Type=simple
ExecStart=$BIN_DIR/wallpaper-changer
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable wallpaper-changer.service
    echo -e "${GREEN}Autostart enabled!${NC}"
    echo -e "To start now: ${YELLOW}systemctl --user start wallpaper-changer.service${NC}"
fi

echo
echo -e "${GREEN}===================================${NC}"
echo -e "${GREEN}Installation completed!${NC}"
echo -e "${GREEN}===================================${NC}"
echo
echo -e "You can now:"
echo -e "1. Find 'Wallpaper Changer' in your application launcher"
echo -e "2. Run ${YELLOW}wallpaper-changer${NC} from terminal"
echo -e "3. Right-click on the desktop entry for quick actions"
echo
echo -e "The application will run in the system tray."
echo -e "${YELLOW}Note: You may need to log out and back in for the launcher to detect the app.${NC}"