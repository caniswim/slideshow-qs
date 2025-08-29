#!/usr/bin/env python3
"""
Wallpaper manager for handling wallpaper operations
"""
import json
import os
import random
import subprocess
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
try:
    from PIL import Image
except ImportError:
    print("Warning: Pillow not installed. Thumbnail creation disabled.")
    Image = None
from config_manager import ConfigManager
from wallpaper_metadata import WallpaperMetadata
from wallpaper_analyzer import WallpaperAnalyzer
from datetime import datetime
from strategies import (
    WallpaperSelectionStrategy,
    SmartRandomStrategy,
    PureRandomStrategy,
    SequentialShuffleStrategy,
    TimeBasedStrategy
)
from filters import FilterChain


class WallpaperManager:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.current_wallpaper = None
        self.wallpaper_list = []
        self.current_index = -1
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize metadata and analyzer
        self.metadata_manager = WallpaperMetadata(self.config.config_dir)
        self.analyzer = WallpaperAnalyzer(num_workers=4)
        
        # Initialize filter chain
        self.filter_chain = FilterChain(self.config, self.metadata_manager)
        self.filter_chain.build_default_chain()
        
        # Initialize strategies
        self.strategies = self._initialize_strategies()
        self.current_strategy: Optional[WallpaperSelectionStrategy] = None
        self._update_strategy()
        
        # Quickshell config path
        config_home = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        self.shell_config_file = Path(config_home) / 'illogical-impulse' / 'config.json'
        
        # Color generation script path
        self.switchwall_script = Path(config_home) / 'quickshell' / 'ii' / 'scripts' / 'colors' / 'switchwall.sh'
        
        # Load initial wallpaper list
        self.refresh_wallpaper_list()
    
    def _initialize_strategies(self) -> Dict[str, WallpaperSelectionStrategy]:
        """Initialize all available strategies"""
        strategies = {
            'smart': SmartRandomStrategy({
                'avoid_recent_percentage': self.config.get('avoid_recent_percentage', 25)
            }),
            'pure': PureRandomStrategy(),
            'sequential': SequentialShuffleStrategy()
        }
        
        # Time-based strategy wraps the appropriate inner strategy
        for mode in ['smart', 'pure', 'sequential']:
            strategies[f'time_{mode}'] = TimeBasedStrategy({
                'metadata_manager': self.metadata_manager,
                'inner_strategy': strategies[mode]
            })
        
        return strategies
    
    def _update_strategy(self):
        """Update the current strategy based on configuration"""
        mode = self.config.get('random_mode', 'smart')
        time_based = self.config.get('time_based_enabled', False)
        
        if time_based:
            strategy_key = f'time_{mode}'
        else:
            strategy_key = mode
        
        if strategy_key in self.strategies:
            self.current_strategy = self.strategies[strategy_key]
            self.logger.info(f"Using strategy: {strategy_key}")
        else:
            self.current_strategy = self.strategies['smart']
            self.logger.warning(f"Unknown strategy {strategy_key}, using smart")
    
    def refresh_wallpaper_list(self) -> List[Path]:
        """Refresh the list of available wallpapers"""
        directory = Path(self.config.get('wallpaper_directory', Path.home() / 'Pictures'))
        
        if not directory.exists():
            self.wallpaper_list = []
            return []
        
        wallpapers = []
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in self.image_extensions:
                wallpapers.append(file)
        
        # Sort by name
        wallpapers.sort(key=lambda x: x.name.lower())
        
        self.wallpaper_list = wallpapers
        self.logger.info(f"Refreshed wallpaper list: {len(wallpapers)} wallpapers found")
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
    
    def next_wallpaper(self, respect_filters: bool = True) -> Optional[Path]:
        """Set next wallpaper in the list"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        if respect_filters:
            # Apply filters and get next from filtered list
            context = self._get_filter_context()
            filtered = self.filter_chain.apply(self.wallpaper_list, context)
            
            if not filtered:
                self.logger.warning("No wallpapers after filtering, using unfiltered list")
                filtered = self.wallpaper_list
            
            # Find current wallpaper in filtered list
            current = self.get_current_wallpaper()
            if current in filtered:
                current_idx = filtered.index(current)
                next_idx = (current_idx + 1) % len(filtered)
                wallpaper = filtered[next_idx]
            else:
                # Current not in filtered, pick first from filtered
                wallpaper = filtered[0] if filtered else None
        else:
            # Simple next without filters
            self.current_index = (self.current_index + 1) % len(self.wallpaper_list)
            wallpaper = self.wallpaper_list[self.current_index]
        
        if wallpaper and self.set_wallpaper(wallpaper):
            if self.current_strategy:
                self.current_strategy.update_tracking(wallpaper)
            return wallpaper
        return None
    
    def previous_wallpaper(self, respect_filters: bool = True) -> Optional[Path]:
        """Set previous wallpaper in the list"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        if respect_filters:
            # Apply filters and get previous from filtered list
            context = self._get_filter_context()
            filtered = self.filter_chain.apply(self.wallpaper_list, context)
            
            if not filtered:
                self.logger.warning("No wallpapers after filtering, using unfiltered list")
                filtered = self.wallpaper_list
            
            # Find current wallpaper in filtered list
            current = self.get_current_wallpaper()
            if current in filtered:
                current_idx = filtered.index(current)
                prev_idx = (current_idx - 1) % len(filtered)
                wallpaper = filtered[prev_idx]
            else:
                # Current not in filtered, pick last from filtered
                wallpaper = filtered[-1] if filtered else None
        else:
            # Simple previous without filters
            self.current_index = (self.current_index - 1) % len(self.wallpaper_list)
            wallpaper = self.wallpaper_list[self.current_index]
        
        if wallpaper and self.set_wallpaper(wallpaper):
            if self.current_strategy:
                self.current_strategy.update_tracking(wallpaper)
            return wallpaper
        return None
    
    def _get_filter_context(self) -> Dict[str, Any]:
        """Get context for filter chain"""
        context = {
            'time_based_enabled': self.config.get('time_based_enabled', False),
            'current_time': datetime.now().time(),
            'current_wallpaper': self.get_current_wallpaper(),
            'luminosity_filter': None,  # Can be set for specific filtering
            'filter_recent': False,  # Will be set based on mode
            'recent_wallpapers': []
        }
        
        # Add recent wallpapers if using smart mode
        mode = self.config.get('random_mode', 'smart')
        if mode == 'smart' and self.current_strategy:
            if hasattr(self.current_strategy, 'recent_wallpapers'):
                context['filter_recent'] = True
                context['recent_wallpapers'] = self.current_strategy.recent_wallpapers
        
        return context
    
    def random_wallpaper(self) -> Optional[Path]:
        """Set a random wallpaper based on configured mode"""
        if not self.wallpaper_list:
            self.refresh_wallpaper_list()
        
        if not self.wallpaper_list:
            return None
        
        # Update strategy based on current config
        self._update_strategy()
        
        # Get filter context
        context = self._get_filter_context()
        
        # Apply filters
        filtered = self.filter_chain.apply(self.wallpaper_list, context)
        
        if not filtered:
            self.logger.warning("No wallpapers after filtering, using unfiltered list")
            filtered = self.wallpaper_list
        
        # Use strategy to select wallpaper
        if self.current_strategy:
            wallpaper = self.current_strategy.select(filtered, context)
        else:
            # Fallback to random if no strategy
            wallpaper = random.choice(filtered) if filtered else None
        
        if wallpaper and self.set_wallpaper(wallpaper):
            if self.current_strategy:
                self.current_strategy.update_tracking(wallpaper)
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
        stats = {
            'total_wallpapers': len(self.wallpaper_list),
            'random_mode': self.config.get('random_mode', 'smart'),
            'time_based_enabled': self.config.get('time_based_enabled', False),
            'avoid_percentage': self.config.get('avoid_recent_percentage', 25)
        }
        
        # Add strategy-specific stats
        if self.current_strategy:
            stats.update(self.current_strategy.get_stats())
        
        return stats
    
    def reset_session_tracking(self):
        """Reset session tracking for a fresh start"""
        # Reset all strategies
        for strategy in self.strategies.values():
            strategy.reset()
        
        self.logger.info("Session tracking reset")
    
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