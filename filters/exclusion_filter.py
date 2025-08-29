#!/usr/bin/env python3
"""
Exclusion filter that removes excluded wallpapers from selection
"""
from pathlib import Path
from typing import List, Dict, Any, Set
from .base_filter import WallpaperFilter


class ExclusionFilter(WallpaperFilter):
    """Filter out excluded wallpapers"""
    
    def __init__(self, config_manager, next_filter=None):
        """
        Initialize exclusion filter
        
        Args:
            config_manager: ConfigManager instance for accessing excluded files
            next_filter: Next filter in chain
        """
        super().__init__(next_filter)
        self.config_manager = config_manager
    
    def apply_filter(self, wallpapers: List[Path], context: Dict[str, Any]) -> List[Path]:
        """
        Remove excluded wallpapers from the list
        
        Args:
            wallpapers: List of wallpaper paths
            context: Context information (not used by this filter)
        
        Returns:
            Wallpapers with excluded files removed
        """
        # Get excluded files from config
        excluded_files = self.config_manager.get('excluded_files', [])
        
        if not excluded_files:
            # No exclusions, return all wallpapers
            return wallpapers
        
        # Convert to set for faster lookup
        excluded_set: Set[str] = set(excluded_files)
        
        # Filter out excluded wallpapers
        filtered = [w for w in wallpapers if str(w) not in excluded_set]
        
        if not filtered:
            # If all wallpapers are excluded, return original list as fallback
            self.logger.warning("All wallpapers are excluded, ignoring exclusions")
            return wallpapers
        
        excluded_count = len(wallpapers) - len(filtered)
        if excluded_count > 0:
            self.logger.info(f"Excluded {excluded_count} wallpapers")
        
        return filtered