#!/usr/bin/env python3
"""
Time-based filter that filters wallpapers by time of day and luminosity
"""
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from .base_filter import WallpaperFilter


class TimeBasedFilter(WallpaperFilter):
    """Filter wallpapers based on time of day and their luminosity classification"""
    
    def __init__(self, metadata_manager, next_filter=None):
        """
        Initialize time-based filter
        
        Args:
            metadata_manager: WallpaperMetadata instance for accessing classifications
            next_filter: Next filter in chain
        """
        super().__init__(next_filter)
        self.metadata_manager = metadata_manager
    
    def apply_filter(self, wallpapers: List[Path], context: Dict[str, Any]) -> List[Path]:
        """
        Filter wallpapers based on current time and luminosity schedules
        
        Args:
            wallpapers: List of wallpaper paths
            context: Should contain 'time_based_enabled' and optionally 'current_time'
        
        Returns:
            Filtered wallpapers suitable for current time
        """
        # Check if time-based filtering is enabled
        if not context.get('time_based_enabled', False):
            self.logger.debug("Time-based filtering is disabled")
            return wallpapers
        
        # Get current time
        current_time = context.get('current_time', datetime.now().time())
        
        # Get active classifications for current time
        active_classifications = self.metadata_manager.get_active_classifications(current_time)
        
        if active_classifications:
            self.logger.info(
                f"Active classifications at {current_time.strftime('%H:%M')}: {', '.join(active_classifications)}"
            )
        else:
            self.logger.info(f"No time restrictions at {current_time.strftime('%H:%M')} - all wallpapers allowed")
        
        # Get wallpapers suitable for current time from metadata manager
        suitable_paths = self.metadata_manager.get_wallpapers_for_current_time(current_time)
        
        if not suitable_paths:
            # If no time-based selection available, return all wallpapers
            self.logger.warning("No wallpapers found for current time, returning all")
            return wallpapers
        
        # Convert suitable paths to a set for faster lookup
        suitable_set = set(suitable_paths)
        
        # Filter wallpapers to only those suitable for current time
        filtered = [w for w in wallpapers if str(w) in suitable_set]
        
        # Count wallpapers by classification for logging
        if active_classifications and filtered:
            classification_counts = {}
            for wallpaper in filtered:
                metadata = self.metadata_manager.get_wallpaper_metadata(str(wallpaper))
                if metadata:
                    classification = metadata.get('classification', 'unknown')
                    classification_counts[classification] = classification_counts.get(classification, 0) + 1
            
            if classification_counts:
                counts_str = ', '.join([f"{cls}: {cnt}" for cls, cnt in classification_counts.items()])
                self.logger.info(f"Wallpapers by classification: {counts_str}")
        
        if not filtered:
            # Fallback: if no wallpapers match after filtering, return original list
            self.logger.warning(
                f"Time filter resulted in empty list at {current_time}, using unfiltered list"
            )
            return wallpapers
        
        self.logger.info(
            f"Time filter at {current_time.strftime('%H:%M')}: {len(wallpapers)} -> {len(filtered)} wallpapers"
        )
        
        return filtered