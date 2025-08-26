#!/bin/bash
# Initialize wallpaper metadata with luminosity analysis

echo "======================================"
echo "Wallpaper Metadata Initialization"
echo "======================================"
echo ""
echo "This script will analyze all wallpapers in your directory"
echo "and classify them as Dark, Medium, or Light for time-based selection."
echo ""

# Check if Python and required modules are installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if PIL is installed
python3 -c "import PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required Python packages..."
    pip3 install --user Pillow
fi

# Run the fast analyzer
echo "Starting wallpaper analysis..."
echo ""
python3 fast_analyze.py

echo ""
echo "Initialization complete!"
echo ""
echo "Next steps:"
echo "1. Run './wallpaper-changer' to start the application"
echo "2. Open Settings (Ctrl+S) to configure time-based schedules"
echo "3. Enable 'Time-based Selection' in Settings > Time-Based tab"
echo ""