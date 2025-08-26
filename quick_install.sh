#!/bin/bash
# Quick install script to copy missing modules

INSTALL_DIR="/usr/local/share/wallpaper-changer"

echo "Quick install of missing modules..."
echo "This script requires sudo. Run it manually:"
echo ""
echo "sudo cp wallpaper_metadata.py $INSTALL_DIR/"
echo "sudo cp wallpaper_analyzer.py $INSTALL_DIR/"
echo "sudo cp settings_dialog_modern.py $INSTALL_DIR/"
echo ""
echo "Or run the full installation:"
echo "sudo bash install.sh"