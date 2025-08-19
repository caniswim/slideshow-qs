#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
import os
import json
import random
import subprocess
from pathlib import Path
import threading
import time

class WallpaperChanger(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.quickshell.wallpaperchanger',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.config_file = Path.home() / '.config' / 'wallpaper-changer' / 'config.json'
        self.config = self.load_config()
        self.running = False
        self.thread = None
        
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
    
    def do_activate(self):
        """Called when the application is activated"""
        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_title("Wallpaper Changer")
        self.win.set_default_size(500, 400)
        
        # Create main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        # AdwApplicationWindow has built-in header bar
        
        # Title
        title_label = Gtk.Label(label="Quickshell Wallpaper Changer")
        title_label.set_markup("<b><big>Quickshell Wallpaper Changer</big></b>")
        title_label.set_margin_bottom(10)
        main_box.append(title_label)
        
        # Directory selection
        dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        dir_label = Gtk.Label(label="Wallpaper Directory:")
        dir_label.set_size_request(150, -1)
        dir_label.set_xalign(0)
        dir_box.append(dir_label)
        
        self.dir_entry = Gtk.Entry()
        self.dir_entry.set_text(self.config['directory'])
        self.dir_entry.set_hexpand(True)
        dir_box.append(self.dir_entry)
        
        browse_button = Gtk.Button(label="Browse")
        browse_button.connect('clicked', self.on_browse_clicked)
        dir_box.append(browse_button)
        
        main_box.append(dir_box)
        
        # Interval selection
        interval_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        interval_label = Gtk.Label(label="Change Interval:")
        interval_label.set_size_request(150, -1)
        interval_label.set_xalign(0)
        interval_box.append(interval_label)
        
        self.interval_combo = Gtk.ComboBoxText()
        intervals = [
            ("1", "1 minute"),
            ("5", "5 minutes"),
            ("10", "10 minutes"),
            ("15", "15 minutes"),
            ("30", "30 minutes")
        ]
        
        for _, text in intervals:
            self.interval_combo.append_text(text)
        
        # Set current interval
        interval_map = {"1": 0, "5": 1, "10": 2, "15": 3, "30": 4}
        current_interval = str(self.config['interval'])
        if current_interval in interval_map:
            self.interval_combo.set_active(interval_map[current_interval])
        self.interval_combo.connect('changed', self.on_interval_changed)
        interval_box.append(self.interval_combo)
        
        main_box.append(interval_box)
        
        # Enable/Disable switch
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        switch_label = Gtk.Label(label="Enable Wallpaper Changer:")
        switch_label.set_size_request(150, -1)
        switch_label.set_xalign(0)
        switch_box.append(switch_label)
        
        self.enable_switch = Gtk.Switch()
        self.enable_switch.set_active(self.config['enabled'])
        self.enable_switch.connect('notify::active', self.on_switch_toggled)
        switch_box.append(self.enable_switch)
        
        main_box.append(switch_box)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.set_margin_top(20)
        self.update_status()
        main_box.append(self.status_label)
        
        # Change Now button
        change_now_button = Gtk.Button(label="Change Wallpaper Now")
        change_now_button.connect('clicked', self.on_change_now_clicked)
        change_now_button.set_margin_top(10)
        main_box.append(change_now_button)
        
        # Info box
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        info_box.set_margin_top(20)
        
        info_label = Gtk.Label()
        info_label.set_markup("<small><i>This application changes wallpapers for quickshell/illogical-impulse setup.</i></small>")
        info_label.set_wrap(True)
        info_box.append(info_label)
        
        main_box.append(info_box)
        
        # Add main box to window
        self.win.set_content(main_box)
        self.win.present()
        
        # Start wallpaper changer if enabled
        if self.config['enabled']:
            self.start_wallpaper_changer()
    
    def on_browse_clicked(self, widget):
        """Handle browse button click"""
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Wallpaper Directory")
        dialog.set_initial_folder(Gio.File.new_for_path(self.config['directory']))
        
        dialog.select_folder(self.win, None, self.on_folder_selected)
    
    def on_folder_selected(self, dialog, result):
        """Handle folder selection"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.dir_entry.set_text(path)
                self.config['directory'] = path
                self.save_config()
        except GLib.Error:
            pass
    
    def on_interval_changed(self, combo):
        """Handle interval change"""
        intervals = [1, 5, 10, 15, 30]
        active = combo.get_active()
        if active >= 0:
            self.config['interval'] = intervals[active]
            self.save_config()
            if self.running:
                self.stop_wallpaper_changer()
                self.start_wallpaper_changer()
    
    def on_switch_toggled(self, switch, gparam):
        """Handle enable/disable switch toggle"""
        enabled = switch.get_active()
        self.config['enabled'] = enabled
        self.save_config()
        
        if enabled:
            self.start_wallpaper_changer()
        else:
            self.stop_wallpaper_changer()
        
        self.update_status()
    
    def on_change_now_clicked(self, widget):
        """Handle change now button click"""
        self.change_wallpaper()
        self.show_notification("Wallpaper changed successfully!")
    
    def update_status(self):
        """Update status label"""
        if self.config['enabled']:
            status = f"<span foreground='green'>● Running</span> - Changing every {self.config['interval']} minute(s)"
        else:
            status = "<span foreground='red'>● Stopped</span>"
        self.status_label.set_markup(status)
    
    def start_wallpaper_changer(self):
        """Start the wallpaper changer thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.wallpaper_loop, daemon=True)
            self.thread.start()
    
    def stop_wallpaper_changer(self):
        """Stop the wallpaper changer thread"""
        self.running = False
        if self.thread:
            self.thread = None
    
    def wallpaper_loop(self):
        """Main wallpaper changing loop"""
        while self.running:
            self.change_wallpaper()
            # Sleep in small intervals to allow quick stopping
            for _ in range(self.config['interval'] * 60):
                if not self.running:
                    break
                time.sleep(1)
    
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
    
    def change_wallpaper(self):
        """Change the wallpaper using jq command"""
        images = self.get_image_files()
        if not images:
            print("No images found in directory")
            return
        
        # Select random image
        image_path = random.choice(images)
        
        # Prepare the shell config file path
        config_home = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        shell_config_file = Path(config_home) / 'illogical-impulse' / 'config.json'
        
        if not shell_config_file.exists():
            print(f"Config file not found: {shell_config_file}")
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
                print(f"Wallpaper changed to: {image_path}")
            else:
                print(f"Error running jq: {result.stderr}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        except Exception as e:
            print(f"Error changing wallpaper: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def show_notification(self, message):
        """Show a notification"""
        notification = Gio.Notification.new("Wallpaper Changer")
        notification.set_body(message)
        self.send_notification(None, notification)

def main():
    app = WallpaperChanger()
    app.run(None)

if __name__ == '__main__':
    main()