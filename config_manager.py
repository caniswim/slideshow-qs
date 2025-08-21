#!/usr/bin/env python3
"""
Configuration manager for the wallpaper changer application
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'wallpaper-changer'
        self.config_file = self.config_dir / 'config.json'
        self.cache_dir = self.config_dir / 'cache'
        self.history_file = self.config_dir / 'history.json'
        
        self._ensure_directories()
        self.config = self.load_config()
        self.history = self.load_history()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self.get_default_config()
        return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'wallpaper_directory': str(Path.home() / 'Pictures'),
            'change_interval': 30,  # minutes
            'auto_change_enabled': False,
            'shuffle': True,
            'show_notifications': True,
            'thumbnail_size': 150,
            'gallery_columns': 4,
            'cache_thumbnails': True,
            'recent_wallpapers_limit': 20,
            'excluded_files': [],
            'sync_color_scheme': True,  # Enable Material Design color generation from wallpaper
            'random_mode': 'smart',  # 'pure' (pure random), 'smart' (avoid recent), 'sequential' (shuffle all)
            'avoid_recent_percentage': 25,  # Percentage of wallpapers to avoid repeating in smart mode
            'window_geometry': {
                'x': 100,
                'y': 100,
                'width': 1200,
                'height': 800
            },
            'shortcuts': {
                'next_wallpaper': 'Ctrl+Right',
                'previous_wallpaper': 'Ctrl+Left',
                'random_wallpaper': 'Ctrl+R',
                'open_gallery': 'Ctrl+G',
                'toggle_auto_change': 'Ctrl+Space',
                'exclude_current': 'Ctrl+X'
            }
        }
    
    def save_config(self, config: Dict[str, Any] = None):
        """Save configuration to file"""
        if config:
            self.config = config
        
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values"""
        self.config.update(updates)
        self.save_config()
    
    def load_history(self) -> List[str]:
        """Load wallpaper history"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    return data.get('recent_wallpapers', [])
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def save_history(self):
        """Save wallpaper history"""
        with open(self.history_file, 'w') as f:
            json.dump({'recent_wallpapers': self.history}, f, indent=2)
    
    def add_to_history(self, wallpaper_path: str):
        """Add wallpaper to history"""
        # Remove if already exists
        if wallpaper_path in self.history:
            self.history.remove(wallpaper_path)
        
        # Add to beginning
        self.history.insert(0, wallpaper_path)
        
        # Limit history size
        limit = self.get('recent_wallpapers_limit', 20)
        self.history = self.history[:limit]
        
        self.save_history()
    
    def clear_history(self):
        """Clear wallpaper history"""
        self.history = []
        self.save_history()
    
    def get_cache_path(self, image_path: str) -> Path:
        """Get cache path for thumbnail"""
        image_path = Path(image_path)
        cache_name = f"{image_path.stem}_{image_path.stat().st_mtime:.0f}.jpg"
        return self.cache_dir / cache_name
    
    def clear_cache(self):
        """Clear thumbnail cache"""
        if self.cache_dir.exists():
            for file in self.cache_dir.glob('*.jpg'):
                try:
                    file.unlink()
                except OSError:
                    pass
    
    def get_cache_size(self) -> int:
        """Get total size of cache in bytes"""
        total = 0
        if self.cache_dir.exists():
            for file in self.cache_dir.glob('*.jpg'):
                total += file.stat().st_size
        return total
    
    def is_file_excluded(self, file_path: str) -> bool:
        """Check if file is in excluded list"""
        excluded = self.get('excluded_files', [])
        return str(file_path) in excluded
    
    def toggle_file_exclusion(self, file_path: str):
        """Toggle file exclusion status"""
        excluded = self.get('excluded_files', [])
        file_str = str(file_path)
        
        if file_str in excluded:
            excluded.remove(file_str)
        else:
            excluded.append(file_str)
        
        self.set('excluded_files', excluded)