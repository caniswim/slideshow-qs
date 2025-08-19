# Quickshell Wallpaper Changer

A GTK4 wallpaper changer application for Quickshell/illogical-impulse setup on Arch Linux.

## Features

- 🎨 Modern GTK4/Adwaita interface
- ⏱️ Configurable intervals (1, 5, 10, 15, 30 minutes)
- 📁 Custom wallpaper directory selection
- 🔄 Random wallpaper selection
- 🎯 Direct integration with Quickshell config
- 🚀 Systemd service for background operation
- 📸 Supports multiple image formats (jpg, jpeg, png, gif, bmp, webp)

## Requirements

- Arch Linux
- Python 3.8+
- GTK4 and libadwaita
- jq (for JSON manipulation)
- Quickshell/illogical-impulse setup

## Installation

### Quick Install

```bash
./install.sh
```

### Manual Installation

1. Install system dependencies:
```bash
sudo pacman -S python python-gobject gtk4 libadwaita jq
```

2. Install Python dependencies:
```bash
pip install --user -r requirements.txt
```

3. Copy files to appropriate locations:
```bash
# Main application
cp wallpaper_changer.py ~/.local/bin/
chmod +x ~/.local/bin/wallpaper_changer.py

# Daemon
cp wallpaper_changer_daemon.py ~/.local/bin/wallpaper-changer-daemon
chmod +x ~/.local/bin/wallpaper-changer-daemon

# Desktop entry
cp wallpaper-changer.desktop ~/.local/share/applications/

# Systemd service
cp wallpaper-changer.service ~/.config/systemd/user/
systemctl --user daemon-reload
```

## Usage

### GUI Application

Run the application:
```bash
python3 ~/.local/bin/wallpaper_changer.py
```

Or find "Wallpaper Changer" in your application menu.

### Background Service (Optional)

Enable the systemd service for automatic wallpaper changes:
```bash
systemctl --user enable --now wallpaper-changer.service
```

Check service status:
```bash
systemctl --user status wallpaper-changer.service
```

Stop the service:
```bash
systemctl --user stop wallpaper-changer.service
```

## Configuration

The application stores its configuration in:
```
~/.config/wallpaper-changer/config.json
```

Example configuration:
```json
{
  "directory": "/home/username/Pictures/wallpapers",
  "interval": 5,
  "enabled": true
}
```

## How It Works

The application modifies the Quickshell configuration file at `~/.config/illogical-impulse/config.json` using the `jq` command to update the `background.wallpaperPath` property.

## License

MIT License

## Author

Created for the Quickshell/Hyprland community