# Quickshell Wallpaper Changer

A modern wallpaper manager with system tray integration and visual gallery for Quickshell/illogical-impulse setup on Arch Linux.

## Features

### System Tray Integration
- 🔄 Quick wallpaper changes from tray menu
- ⏭️ Next/Previous wallpaper navigation
- ⏱️ Real-time countdown to next auto-change
- 📜 Recent wallpapers history
- 🔔 Desktop notifications

### Visual Gallery
- 🖼️ Grid view with thumbnails
- 🔍 Live preview of selected wallpapers
- 🔎 Search and filter wallpapers by name
- 📊 Sort by name, date, or random
- 💾 Cached thumbnails for fast loading
- 📏 Adjustable thumbnail sizes

### Advanced Features
- ⚡ Application runs in background (doesn't close with window)
- ⚙️ Quick settings dialog
- 🎯 Direct integration with Quickshell config
- 📸 Supports multiple image formats (jpg, jpeg, png, gif, bmp, webp)
- 🔀 Shuffle mode for random wallpapers
- 🚫 Exclude specific wallpapers

## Requirements

- Arch Linux
- Python 3.8+
- PyQt6
- Pillow (for image processing)
- jq (for JSON manipulation)
- Quickshell/illogical-impulse setup

## Installation

### Install Dependencies

1. Install system dependencies:
```bash
sudo pacman -S python python-pyqt6 python-pillow jq
```

2. Or install via pip:
```bash
pip install --user -r requirements.txt
```

## Usage

### Running the Application

Start the wallpaper changer:
```bash
python3 main.py
```

The application will:
- Start minimized to system tray
- Show an icon in your system tray area
- Continue running even when windows are closed

### System Tray Controls

**Right-click** the tray icon for quick actions:
- Change wallpaper immediately
- Navigate to next/previous wallpaper
- Open the visual gallery
- Access settings
- View recent wallpapers

**Double-click** the tray icon to open the gallery window.

### Gallery Window

The gallery provides:
- Visual grid of all wallpapers
- Click to preview in large format
- Double-click to apply wallpaper
- Search bar for filtering by name
- Sort options (name, date, random)
- Thumbnail size adjustment

### Keyboard Shortcuts

- `Ctrl+G` - Open gallery window
- `Ctrl+R` - Random wallpaper
- `Ctrl+Right` - Next wallpaper
- `Ctrl+Left` - Previous wallpaper
- `Ctrl+Space` - Toggle auto-change
- `Escape` - Close gallery window
- `Enter` - Apply selected wallpaper (in gallery)

## Configuration

The application stores its configuration in:
```
~/.config/wallpaper-changer/config.json
~/.config/wallpaper-changer/history.json
~/.config/wallpaper-changer/cache/
```

### Configuration Options

```json
{
  "wallpaper_directory": "/home/username/Pictures/wallpapers",
  "change_interval": 30,
  "auto_change_enabled": false,
  "shuffle": true,
  "show_notifications": true,
  "thumbnail_size": 150,
  "gallery_columns": 4,
  "cache_thumbnails": true,
  "recent_wallpapers_limit": 20,
  "excluded_files": []
}
```

## File Structure

```
slideshow-qs/
├── main.py                 # Main application with system tray
├── gallery_window.py       # Visual gallery window
├── wallpaper_manager.py    # Wallpaper management logic
├── config_manager.py       # Configuration handling
├── requirements.txt        # Python dependencies
├── assets/
│   └── icon.png           # Tray icon (optional)
└── README.md
```

## How It Works

The application modifies the Quickshell configuration file at `~/.config/illogical-impulse/config.json` using the `jq` command to update the `background.wallpaperPath` property.

## Troubleshooting

### System tray icon not appearing
- Ensure your desktop environment supports system tray icons
- Check if you have a system tray/notification area enabled

### Wallpapers not changing
- Verify the Quickshell config file exists at `~/.config/illogical-impulse/config.json`
- Check that `jq` is installed: `which jq`
- Ensure wallpaper directory contains valid image files

### Gallery not loading thumbnails
- Check if Pillow is properly installed
- Clear cache from the toolbar menu
- Verify image files are readable

## License

MIT License

## Author

Created for the Quickshell/Hyprland community