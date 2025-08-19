#!/usr/bin/env python3
"""
System tray icon for the wallpaper changer
"""
import sys
import json
import random
import subprocess
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer, QTime
from PyQt6.QtGui import QIcon, QAction

class WallpaperTray(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.config_file = Path.home() / '.config' / 'wallpaper-changer' / 'config.json'
        self.last_change_time = datetime.now()
        self.config = self.load_config()
        
        # Create icon (using a standard icon for now)
        self.setIcon(QIcon.fromTheme('preferences-desktop-wallpaper'))
        
        # Create context menu
        self.create_menu()
        
        # Show the tray icon
        self.setVisible(True)
        
        # Set up timer to update menu every second
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_time_display)
        self.update_timer.start(1000)  # Update every second
        
        # Set up timer to track wallpaper changes
        self.wallpaper_timer = QTimer()
        self.wallpaper_timer.timeout.connect(self.on_wallpaper_changed)
        if self.config.get('enabled', False):
            interval_minutes = self.config.get('interval', 5)
            self.wallpaper_timer.start(interval_minutes * 60 * 1000)
        
        # Monitor config file changes
        self.config_timer = QTimer()
        self.config_timer.timeout.connect(self.check_config_changes)
        self.config_timer.start(5000)  # Check every 5 seconds
        
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            'directory': str(Path.home() / 'Pictures'),
            'interval': 5,
            'enabled': False
        }
    
    def save_config(self):
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def create_menu(self):
        """Create the context menu"""
        menu = QMenu()
        
        # Time until next change
        self.time_action = QAction("Next change: Calculating...", self)
        self.time_action.setEnabled(False)
        menu.addAction(self.time_action)
        
        menu.addSeparator()
        
        # Change wallpaper now
        change_action = QAction("Change Wallpaper Now", self)
        change_action.triggered.connect(self.change_wallpaper_now)
        menu.addAction(change_action)
        
        menu.addSeparator()
        
        # Status
        self.status_action = QAction("Status: " + ("Running" if self.config.get('enabled', False) else "Stopped"), self)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        # Enable/Disable
        self.toggle_action = QAction("Disable" if self.config.get('enabled', False) else "Enable", self)
        self.toggle_action.triggered.connect(self.toggle_daemon)
        menu.addAction(self.toggle_action)
        
        menu.addSeparator()
        
        # Open settings
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        # Quit
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
        
    def update_time_display(self):
        """Update the time until next change display"""
        if not self.config.get('enabled', False):
            self.time_action.setText("Next change: Disabled")
            return
            
        interval_minutes = self.config.get('interval', 5)
        next_change = self.last_change_time + timedelta(minutes=interval_minutes)
        now = datetime.now()
        
        if now >= next_change:
            self.time_action.setText("Next change: Any moment...")
        else:
            time_left = next_change - now
            minutes = int(time_left.total_seconds() // 60)
            seconds = int(time_left.total_seconds() % 60)
            
            if minutes > 0:
                self.time_action.setText(f"Next change: {minutes}m {seconds}s")
            else:
                self.time_action.setText(f"Next change: {seconds}s")
    
    def on_wallpaper_changed(self):
        """Called when wallpaper should have changed"""
        self.last_change_time = datetime.now()
    
    def check_config_changes(self):
        """Check if config file has changed"""
        new_config = self.load_config()
        if new_config != self.config:
            self.config = new_config
            self.update_menu_state()
            
            # Restart wallpaper timer if interval changed
            if self.config.get('enabled', False):
                interval_minutes = self.config.get('interval', 5)
                self.wallpaper_timer.stop()
                self.wallpaper_timer.start(interval_minutes * 60 * 1000)
            else:
                self.wallpaper_timer.stop()
    
    def update_menu_state(self):
        """Update menu items based on current state"""
        enabled = self.config.get('enabled', False)
        self.status_action.setText("Status: " + ("Running" if enabled else "Stopped"))
        self.toggle_action.setText("Disable" if enabled else "Enable")
    
    def get_image_files(self):
        """Get list of image files from directory"""
        directory = Path(self.config['directory'])
        if not directory.exists():
            return []
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in image_extensions:
                image_files.append(file)
        
        return image_files
    
    def change_wallpaper_now(self):
        """Change the wallpaper immediately"""
        images = self.get_image_files()
        if not images:
            self.showMessage("Wallpaper Changer", "No images found in directory", QSystemTrayIcon.MessageIcon.Warning)
            return
        
        # Select random image
        image_path = random.choice(images)
        
        # Prepare the shell config file path
        config_home = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        shell_config_file = Path(config_home) / 'illogical-impulse' / 'config.json'
        
        if not shell_config_file.exists():
            self.showMessage("Wallpaper Changer", "Config file not found", QSystemTrayIcon.MessageIcon.Critical)
            return
        
        # Create temporary file path
        temp_file = str(shell_config_file) + '.tmp'
        
        # Build jq command
        cmd = [
            'jq',
            '--arg', 'path', str(image_path),
            '.background.wallpaperPath = $path',
            str(shell_config_file)
        ]
        
        try:
            # Run jq command and write to temp file
            with open(temp_file, 'w') as f:
                result = subprocess.run(cmd, text=True, stdout=f, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                # Move temp file to actual config file
                os.rename(temp_file, shell_config_file)
                self.showMessage("Wallpaper Changer", f"Changed to: {image_path.name}", QSystemTrayIcon.MessageIcon.Information)
                self.last_change_time = datetime.now()
            else:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                self.showMessage("Wallpaper Changer", "Error changing wallpaper", QSystemTrayIcon.MessageIcon.Critical)
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            self.showMessage("Wallpaper Changer", f"Error: {str(e)}", QSystemTrayIcon.MessageIcon.Critical)
    
    def toggle_daemon(self):
        """Enable or disable the daemon"""
        self.config['enabled'] = not self.config.get('enabled', False)
        self.save_config()
        self.update_menu_state()
        
        if self.config['enabled']:
            # Start wallpaper timer
            interval_minutes = self.config.get('interval', 5)
            self.wallpaper_timer.start(interval_minutes * 60 * 1000)
            self.last_change_time = datetime.now()
            self.showMessage("Wallpaper Changer", "Wallpaper changer enabled", QSystemTrayIcon.MessageIcon.Information)
        else:
            # Stop wallpaper timer
            self.wallpaper_timer.stop()
            self.showMessage("Wallpaper Changer", "Wallpaper changer disabled", QSystemTrayIcon.MessageIcon.Information)
    
    def open_settings(self):
        """Open the settings GUI"""
        subprocess.Popen(['python3', str(Path(__file__).parent / 'wallpaper_changer.py')])
    
    def quit_app(self):
        """Quit the application"""
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray
    
    tray = WallpaperTray()
    tray.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()