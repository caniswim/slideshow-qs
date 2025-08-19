#!/usr/bin/env python3
"""
Wallpaper manager for handling wallpaper operations
"""
import json
import os
import random
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
try:
    from PIL import Image
except ImportError:
    print("Warning: Pillow not installed. Thumbnail creation disabled.")
    Image = None
from config_manager import ConfigManager


class WallpaperManager:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.current_wallpaper = None
        self.wallpaper_list = []
        self.current_index = -1
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        # Quickshell config path
        config_home = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        self.shell_config_file = Path(config_home) / 'illogical-impulse' / 'config.json'
        
        # Load initial wallpaper list
        self.refresh_wallpaper_list()
    
    def refresh_wallpaper_list(self) -> List[Path]:
        """Refresh the list of available wallpapers"""
        directory = Path(self.config.get('wallpaper_directory', Path.home() / 'Pictures'))
        
        if not directory.exists():
            self.wallpaper_list = []
            return []
        
        wallpapers = []
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in self.image_extensions:
                if not self.config.is_file_excluded(str(file)):
                    wallpapers.append(file)
        
        # Sort by name or shuffle if enabled
        if self.config.get('shuffle', True):
            random.shuffle(wallpapers)
        else:
            wallpapers.sort(key=lambda x: x.name.lower())
        
        self.wallpaper_list = wallpapers
        return wallpapers
    
    def get_wallpaper_list(self) -> List[Path]:
        """Get current wallpaper list"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        return self.wallpaper_list
    
    def set_wallpaper(self, wallpaper_path: Path) -> bool:
        """Set the wallpaper using jq to modify Quickshell config"""
        if not wallpaper_path.exists():
            return False
        
        if not self.shell_config_file.exists():
            print(f"Quickshell config not found: {self.shell_config_file}")
            return False
        
        # Create temporary file path
        temp_file = str(self.shell_config_file) + '.tmp'
        
        # Build jq command to update wallpaper path
        cmd = [
            'jq',
            '--arg', 'path', str(wallpaper_path),
            '.background.wallpaperPath = $path',
            str(self.shell_config_file)
        ]
        
        try:
            # Run jq command and write to temp file
            with open(temp_file, 'w') as f:
                result = subprocess.run(cmd, text=True, stdout=f, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                # Move temp file to actual config file
                os.rename(temp_file, self.shell_config_file)
                self.current_wallpaper = wallpaper_path
                self.config.add_to_history(str(wallpaper_path))
                
                # Update current index if wallpaper is in list
                if wallpaper_path in self.wallpaper_list:
                    self.current_index = self.wallpaper_list.index(wallpaper_path)
                
                return True
            else:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                print(f"Error running jq: {result.stderr}")
                return False
                
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            print(f"Error changing wallpaper: {e}")
            return False
    
    def next_wallpaper(self) -> Optional[Path]:
        """Set next wallpaper in the list"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        self.current_index = (self.current_index + 1) % len(self.wallpaper_list)
        wallpaper = self.wallpaper_list[self.current_index]
        
        if self.set_wallpaper(wallpaper):
            return wallpaper
        return None
    
    def previous_wallpaper(self) -> Optional[Path]:
        """Set previous wallpaper in the list"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        self.current_index = (self.current_index - 1) % len(self.wallpaper_list)
        wallpaper = self.wallpaper_list[self.current_index]
        
        if self.set_wallpaper(wallpaper):
            return wallpaper
        return None
    
    def random_wallpaper(self) -> Optional[Path]:
        """Set a random wallpaper"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        wallpaper = random.choice(self.wallpaper_list)
        
        if self.set_wallpaper(wallpaper):
            return wallpaper
        return None
    
    def get_current_wallpaper(self) -> Optional[Path]:
        """Get the currently set wallpaper from Quickshell config"""
        if not self.shell_config_file.exists():
            return None
        
        try:
            with open(self.shell_config_file, 'r') as f:
                config = json.load(f)
                wallpaper_path = config.get('background', {}).get('wallpaperPath')
                if wallpaper_path:
                    path = Path(wallpaper_path)
                    if path.exists():
                        self.current_wallpaper = path
                        return path
        except (json.JSONDecodeError, IOError):
            pass
        
        return self.current_wallpaper
    
    def create_thumbnail(self, image_path: Path, size: int = 150) -> Optional[Path]:
        """Create a thumbnail for an image"""
        if Image is None:
            return None
            
        cache_path = self.config.get_cache_path(str(image_path))
        
        # Check if cached thumbnail exists and is newer than source
        if cache_path.exists():
            if cache_path.stat().st_mtime >= image_path.stat().st_mtime:
                return cache_path
        
        try:
            # Open and create thumbnail
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                # Calculate thumbnail size maintaining aspect ratio
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(cache_path, 'JPEG', quality=85, optimize=True)
                return cache_path
                
        except Exception as e:
            print(f"Error creating thumbnail for {image_path}: {e}")
            return None
    
    def get_image_info(self, image_path: Path) -> dict:
        """Get information about an image"""
        info = {
            'path': str(image_path),
            'name': image_path.name,
            'size': 0,
            'dimensions': (0, 0),
            'format': '',
            'modified': 0
        }
        
        try:
            # File info
            stat = image_path.stat()
            info['size'] = stat.st_size
            info['modified'] = stat.st_mtime
            
            # Image info - only if PIL is available
            if Image is not None:
                with Image.open(image_path) as img:
                    info['dimensions'] = img.size
                    info['format'] = img.format
                
        except Exception as e:
            print(f"Error getting image info for {image_path}: {e}")
        
        return info
    
    def search_wallpapers(self, query: str) -> List[Path]:
        """Search wallpapers by name"""
        query = query.lower()
        results = []
        
        for wallpaper in self.get_wallpaper_list():
            if query in wallpaper.name.lower():
                results.append(wallpaper)
        
        return results
    
    def get_recent_wallpapers(self) -> List[Path]:
        """Get recently used wallpapers"""
        recent = []
        for path_str in self.config.history:
            path = Path(path_str)
            if path.exists():
                recent.append(path)
        return recent
    
    def exclude_current_wallpaper(self) -> bool:
        """Exclude the current wallpaper from rotation"""
        current = self.get_current_wallpaper()
        if current:
            self.config.toggle_file_exclusion(str(current))
            self.refresh_wallpaper_list()
            return True
        return False
    
    def clear_excluded_files(self):
        """Clear all excluded files"""
        self.config.set('excluded_files', [])
        self.refresh_wallpaper_list()
    
    def get_wallpaper_count(self) -> int:
        """Get total number of available wallpapers"""
        return len(self.wallpaper_list)
    
    def get_directory_size(self) -> int:
        """Get total size of wallpaper directory in bytes"""
        directory = Path(self.config.get('wallpaper_directory', Path.home() / 'Pictures'))
        total = 0
        
        if directory.exists():
            for file in directory.iterdir():
                if file.is_file() and file.suffix.lower() in self.image_extensions:
                    total += file.stat().st_size
        
        return total