#!/usr/bin/env python3
"""
Daemon version of the wallpaper changer that runs in background
"""
import json
import random
import subprocess
import time
import os
from pathlib import Path
import signal
import sys

class WallpaperChangerDaemon:
    def __init__(self):
        self.config_file = Path.home() / '.config' / 'wallpaper-changer' / 'config.json'
        self.running = True
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle termination signals"""
        print("Wallpaper changer daemon stopping...")
        self.running = False
        sys.exit(0)
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_image_files(self, directory):
        """Get list of image files from directory"""
        directory = Path(directory)
        if not directory.exists():
            return []
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in image_extensions:
                image_files.append(file)
        
        return image_files
    
    def change_wallpaper(self, directory):
        """Change the wallpaper using jq command"""
        images = self.get_image_files(directory)
        if not images:
            return
        
        # Select random image
        image_path = random.choice(images)
        
        # Prepare the shell config file path
        config_home = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        shell_config_file = Path(config_home) / 'illogical-impulse' / 'config.json'
        
        if not shell_config_file.exists():
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
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def run(self):
        """Main daemon loop"""
        print("Wallpaper changer daemon started")
        
        while self.running:
            config = self.load_config()
            
            if config and config.get('enabled', False):
                directory = config.get('directory')
                interval = config.get('interval', 5)
                
                if directory:
                    self.change_wallpaper(directory)
                
                # Sleep for the interval, checking config every minute
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(60)
                    
                    # Reload config to check if settings changed
                    new_config = self.load_config()
                    if new_config != config:
                        break
            else:
                # If not enabled, check config every 10 seconds
                time.sleep(10)

if __name__ == '__main__':
    daemon = WallpaperChangerDaemon()
    daemon.run()