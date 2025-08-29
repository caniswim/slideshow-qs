#!/usr/bin/env python3
"""
Luminosity filter that filters wallpapers by their brightness classification
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base_filter import WallpaperFilter


class LuminosityFilter(WallpaperFilter):
    """Filter wallpapers based on luminosity classification"""
    
    def __init__(self, metadata_manager, next_filter=None):
        """
        Initialize luminosity filter
        
        Args:
            metadata_manager: WallpaperMetadata instance for accessing classifications
            next_filter: Next filter in chain
        """
        super().__init__(next_filter)
        self.metadata_manager = metadata_manager
    
    def apply_filter(self, wallpapers: List[Path], context: Dict[str, Any]) -> List[Path]:
        """
        Filter wallpapers based on luminosity classification
        
        Args:
            wallpapers: List of wallpaper paths
            context: Should contain 'luminosity_filter' if filtering by specific classification
        
        Returns:
            Filtered wallpapers matching luminosity criteria
        """
        # Check if luminosity filtering is requested
        luminosity_filter = context.get('luminosity_filter')
        
        if not luminosity_filter or luminosity_filter == 'all':
            # No luminosity filtering requested
            return wallpapers
        
        # Filter wallpapers by classification
        filtered = []
        for wallpaper in wallpapers:
            metadata = self.metadata_manager.get_wallpaper_metadata(str(wallpaper))
            
            if metadata:
                classification = metadata.get('classification', 'medium')
                
                # Check if wallpaper matches the filter
                if classification == luminosity_filter:
                    filtered.append(wallpaper)
            else:
                # No metadata available, include if filter is 'medium' (default)
                if luminosity_filter == 'medium':
                    filtered.append(wallpaper)
        
        if not filtered:
            # Fallback: if no wallpapers match, return original list
            self.logger.warning(
                f"Luminosity filter '{luminosity_filter}' resulted in empty list, using unfiltered"
            )
            return wallpapers
        
        self.logger.info(
            f"Luminosity filter '{luminosity_filter}': {len(wallpapers)} -> {len(filtered)} wallpapers"
        )
        
        return filtered