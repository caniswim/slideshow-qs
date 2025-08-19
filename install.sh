#!/bin/bash

# Wallpaper Changer Installation Script for Arch Linux

echo "Installing Quickshell Wallpaper Changer..."

# Check if running on Arch Linux
if [ ! -f /etc/arch-release ]; then
    echo "Warning: This script is designed for Arch Linux"
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo pacman -S --needed python python-gobject gtk4 libadwaita jq

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --user -r requirements.txt

# Create local bin directory if it doesn't exist
mkdir -p ~/.local/bin

# Copy main application
echo "Installing application files..."
cp wallpaper_changer.py ~/.local/bin/
chmod +x ~/.local/bin/wallpaper_changer.py

# Copy daemon
cp wallpaper_changer_daemon.py ~/.local/bin/wallpaper-changer-daemon
chmod +x ~/.local/bin/wallpaper-changer-daemon

# Install systemd service
echo "Installing systemd service..."
mkdir -p ~/.config/systemd/user/
cp wallpaper-changer.service ~/.config/systemd/user/
systemctl --user daemon-reload

# Install desktop entry
echo "Installing desktop entry..."
mkdir -p ~/.local/share/applications/
cp wallpaper-changer.desktop ~/.local/share/applications/

# Update desktop database
update-desktop-database ~/.local/share/applications/

echo "Installation complete!"
echo ""
echo "You can now:"
echo "1. Run the GUI: python3 ~/.local/bin/wallpaper_changer.py"
echo "2. Or find 'Wallpaper Changer' in your application menu"
echo ""
echo "To enable the background service:"
echo "  systemctl --user enable --now wallpaper-changer.service"
echo ""
echo "To check service status:"
echo "  systemctl --user status wallpaper-changer.service"