#!/usr/bin/env python3
"""
Recent filter that removes recently shown wallpapers (for smart mode)
"""
from pathlib import Path
from typing import List, Dict, Any
from .base_filter import WallpaperFilter


class RecentFilter(WallpaperFilter):
    """Filter out recently shown wallpapers"""
    
    def __init__(self, next_filter=None):
        """
        Initialize recent filter
        
        Args:
            next_filter: Next filter in chain
        """
        super().__init__(next_filter)
    
    def apply_filter(self, wallpapers: List[Path], context: Dict[str, Any]) -> List[Path]:
        """
        Remove recently shown wallpapers from the list
        
        Args:
            wallpapers: List of wallpaper paths
            context: Should contain 'recent_wallpapers' list and 'filter_recent' flag
        
        Returns:
            Wallpapers with recent ones removed (if smart mode is active)
        """
        # Check if we should filter recent wallpapers
        if not context.get('filter_recent', False):
            return wallpapers
        
        recent_wallpapers = context.get('recent_wallpapers', [])
        
        if not recent_wallpapers:
            # No recent wallpapers to filter
            return wallpapers
        
        # Convert to set for faster lookup
        recent_set = set(recent_wallpapers)
        
        # Filter out recent wallpapers
        filtered = [w for w in wallpapers if w not in recent_set]
        
        if not filtered:
            # If all wallpapers are recent, return original list
            self.logger.info("All wallpapers are recent, using full list")
            return wallpapers
        
        removed_count = len(wallpapers) - len(filtered)
        if removed_count > 0:
            self.logger.debug(f"Filtered {removed_count} recent wallpapers")
        
        return filtered