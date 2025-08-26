#!/usr/bin/env python3
"""
Wallpaper manager for handling wallpaper operations
"""
import json
import os
import random
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict
try:
    from PIL import Image
except ImportError:
    print("Warning: Pillow not installed. Thumbnail creation disabled.")
    Image = None
from config_manager import ConfigManager
from wallpaper_metadata import WallpaperMetadata
from wallpaper_analyzer import WallpaperAnalyzer
from datetime import datetime


class WallpaperManager:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.current_wallpaper = None
        self.wallpaper_list = []
        self.current_index = -1
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        # Smart random tracking
        self.unused_wallpapers = []  # Wallpapers not yet shown in current cycle
        self.recent_wallpapers = []  # Recently shown wallpapers to avoid
        self.session_history = []    # All wallpapers shown in this session
        
        # Initialize metadata and analyzer
        self.metadata_manager = WallpaperMetadata(self.config.config_dir)
        self.analyzer = WallpaperAnalyzer(num_workers=4)
        
        # Quickshell config path
        config_home = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        self.shell_config_file = Path(config_home) / 'illogical-impulse' / 'config.json'
        
        # Color generation script path
        self.switchwall_script = Path(config_home) / 'quickshell' / 'ii' / 'scripts' / 'colors' / 'switchwall.sh'
        
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
        # Reset unused wallpapers list for smart random
        self.unused_wallpapers = wallpapers.copy()
        return wallpapers
    
    def get_wallpaper_list(self) -> List[Path]:
        """Get current wallpaper list"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        return self.wallpaper_list
    
    def trigger_color_generation(self, wallpaper_path: Path) -> bool:
        """Trigger Material Design color generation from wallpaper"""
        if not self.switchwall_script.exists():
            print(f"Color generation script not found: {self.switchwall_script}")
            return False
        
        # Check if matugen is installed
        if not shutil.which('matugen'):
            print("matugen not found. Color generation requires matugen to be installed.")
            return False
        
        try:
            # Call the switchwall.sh script with the wallpaper path
            # The script expects the wallpaper path as the first argument
            result = subprocess.run(
                [str(self.switchwall_script), str(wallpaper_path)],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout for color generation
            )
            
            if result.returncode == 0:
                print(f"Color scheme generated successfully for {wallpaper_path.name}")
                return True
            else:
                print(f"Error generating color scheme: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Color generation timed out")
            return False
        except Exception as e:
            print(f"Error triggering color generation: {e}")
            return False
    
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
                
                # Trigger color generation if enabled
                if self.config.get('sync_color_scheme', True):
                    self.trigger_color_generation(wallpaper_path)
                
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
    
    def _update_wallpaper_tracking(self, wallpaper: Path):
        """Update tracking lists when a wallpaper is shown"""
        # Add to session history
        if wallpaper not in self.session_history:
            self.session_history.append(wallpaper)
        
        # Remove from unused list
        if wallpaper in self.unused_wallpapers:
            self.unused_wallpapers.remove(wallpaper)
        
        # Update recent wallpapers list
        avoid_percentage = self.config.get('avoid_recent_percentage', 25)
        max_recent = max(1, len(self.wallpaper_list) * avoid_percentage // 100)
        
        if wallpaper in self.recent_wallpapers:
            self.recent_wallpapers.remove(wallpaper)
        self.recent_wallpapers.append(wallpaper)
        
        # Keep recent list within size limit
        if len(self.recent_wallpapers) > max_recent:
            self.recent_wallpapers.pop(0)
    
    def get_smart_random_wallpaper(self) -> Optional[Path]:
        """Get a smart random wallpaper that avoids recent ones"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        # If all wallpapers have been shown, reset the unused list
        if not self.unused_wallpapers:
            self.unused_wallpapers = self.wallpaper_list.copy()
            # Remove current wallpaper from unused
            current = self.get_current_wallpaper()
            if current and current in self.unused_wallpapers:
                self.unused_wallpapers.remove(current)
        
        # Filter out recent wallpapers from unused list
        available = [w for w in self.unused_wallpapers if w not in self.recent_wallpapers]
        
        # If no wallpapers available after filtering, use unused list
        if not available:
            available = self.unused_wallpapers
        
        # If still no wallpapers, use full list minus current
        if not available:
            current = self.get_current_wallpaper()
            available = [w for w in self.wallpaper_list if w != current]
        
        # If only current wallpaper exists, return None
        if not available:
            return None
        
        return random.choice(available)
    
    def get_sequential_shuffle_wallpaper(self) -> Optional[Path]:
        """Get next wallpaper in shuffled sequence, reshuffling when cycle completes"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        # If all wallpapers have been shown, reshuffle
        if not self.unused_wallpapers:
            self.unused_wallpapers = self.wallpaper_list.copy()
            random.shuffle(self.unused_wallpapers)
            # Remove current wallpaper from beginning if it's there
            current = self.get_current_wallpaper()
            if current and self.unused_wallpapers and self.unused_wallpapers[0] == current:
                self.unused_wallpapers.append(self.unused_wallpapers.pop(0))
        
        # Get the next wallpaper from the shuffled list
        if self.unused_wallpapers:
            return self.unused_wallpapers[0]
        
        return None
    
    def get_time_based_wallpaper(self) -> Optional[Path]:
        """Get a wallpaper suitable for current time of day"""
        current_time = datetime.now().time()
        
        # Get wallpapers suitable for current time
        suitable_paths = self.metadata_manager.get_wallpapers_for_current_time(current_time)
        
        if not suitable_paths:
            # Fallback to any wallpaper if no time-based selection available
            return self.get_smart_random_wallpaper()
        
        # Filter to only existing wallpapers in our list
        available = []
        for wallpaper in self.wallpaper_list:
            if str(wallpaper) in suitable_paths:
                # Also check if not in recent
                if wallpaper not in self.recent_wallpapers:
                    available.append(wallpaper)
        
        # If all suitable wallpapers are recent, use all suitable
        if not available:
            available = [w for w in self.wallpaper_list if str(w) in suitable_paths]
        
        if available:
            return random.choice(available)
        
        return None
    
    def random_wallpaper(self) -> Optional[Path]:
        """Set a random wallpaper based on configured mode"""
        mode = self.config.get('random_mode', 'smart')
        time_based = self.config.get('time_based_enabled', False)
        
        # If time-based selection is enabled, use that
        if time_based:
            wallpaper = self.get_time_based_wallpaper()
        elif mode == 'pure':
            # Pure random - original behavior
            if not self.wallpaper_list:
                self.refresh_wallpaper_list()
            
            if not self.wallpaper_list:
                return None
            
            wallpaper = random.choice(self.wallpaper_list)
        
        elif mode == 'sequential':
            # Sequential shuffle - go through all before repeating
            wallpaper = self.get_sequential_shuffle_wallpaper()
        
        else:  # smart mode (default)
            # Smart random - avoid recent wallpapers
            wallpaper = self.get_smart_random_wallpaper()
        
        if wallpaper and self.set_wallpaper(wallpaper):
            self._update_wallpaper_tracking(wallpaper)
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
                # Use higher quality resampling for HD thumbnails
                img.thumbnail((size * 2, size * 2), Image.Resampling.LANCZOS)
                
                # Save thumbnail with maximum quality
                img.save(cache_path, 'PNG', optimize=True)  # PNG for lossless quality
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
    
    def get_session_stats(self) -> dict:
        """Get statistics about current session"""
        return {
            'total_wallpapers': len(self.wallpaper_list),
            'unused_wallpapers': len(self.unused_wallpapers),
            'session_shown': len(self.session_history),
            'recent_avoided': len(self.recent_wallpapers),
            'random_mode': self.config.get('random_mode', 'smart'),
            'avoid_percentage': self.config.get('avoid_recent_percentage', 25)
        }
    
    def reset_session_tracking(self):
        """Reset session tracking for a fresh start"""
        self.unused_wallpapers = self.wallpaper_list.copy()
        self.recent_wallpapers = []
        self.session_history = []
    
    def analyze_wallpapers(self, progress_callback=None) -> Dict:
        """Analyze all wallpapers in the directory"""
        directory = Path(self.config.get('wallpaper_directory', Path.home() / 'Pictures'))
        
        # Analyze wallpapers
        results = self.analyzer.analyze_directory(directory, progress_callback)
        
        # Update metadata
        if results:
            self.metadata_manager.update_batch_metadata(results)
        
        return results
    
    def get_wallpaper_classification(self, wallpaper_path: Path) -> str:
        """Get classification for a specific wallpaper"""
        metadata = self.metadata_manager.get_wallpaper_metadata(str(wallpaper_path))
        if metadata:
            return metadata.get('classification', 'medium')
        
        # Analyze if not in metadata
        result = self.analyzer.analyze_wallpaper(wallpaper_path)
        if result:
            self.metadata_manager.update_wallpaper_metadata(str(wallpaper_path), result)
            return result.get('classification', 'medium')
        
        return 'medium'
    
    def get_metadata_statistics(self) -> Dict:
        """Get statistics about wallpaper metadata"""
        return self.metadata_manager.get_statistics()
    
    def override_wallpaper_classification(self, wallpaper_path: Path, classification: str):
        """Manually override wallpaper classification"""
        self.metadata_manager.override_classification(str(wallpaper_path), classification)
    
    def get_time_schedules(self) -> Dict:
        """Get current time schedules configuration"""
        return self.metadata_manager.time_schedules
    
    def update_time_schedule(self, classification: str, time_ranges: List[Dict]):
        """Update time schedule for a classification"""
        self.metadata_manager.update_time_schedule(classification, time_ranges)