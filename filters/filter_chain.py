#!/usr/bin/env python3
"""
Filter chain builder and manager
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base_filter import WallpaperFilter
from .time_based_filter import TimeBasedFilter
from .luminosity_filter import LuminosityFilter
from .exclusion_filter import ExclusionFilter
from .recent_filter import RecentFilter
import logging


class FilterChain:
    """Manages and builds filter chains"""
    
    def __init__(self, config_manager, metadata_manager):
        """
        Initialize filter chain builder
        
        Args:
            config_manager: ConfigManager instance
            metadata_manager: WallpaperMetadata instance
        """
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chain_head: Optional[WallpaperFilter] = None
    
    def build_default_chain(self) -> WallpaperFilter:
        """
        Build the default filter chain
        
        Order:
        1. ExclusionFilter - Remove explicitly excluded wallpapers
        2. TimeBasedFilter - Filter by time of day (if enabled)
        3. LuminosityFilter - Filter by luminosity (if specified)
        4. RecentFilter - Remove recent wallpapers (for smart mode)
        
        Returns:
            Head of the filter chain
        """
        # Create filters
        exclusion = ExclusionFilter(self.config_manager)
        time_based = TimeBasedFilter(self.metadata_manager)
        luminosity = LuminosityFilter(self.metadata_manager)
        recent = RecentFilter()
        
        # Chain them together
        exclusion.set_next(time_based).set_next(luminosity).set_next(recent)
        
        self.chain_head = exclusion
        return exclusion
    
    def build_custom_chain(self, filter_order: List[str]) -> Optional[WallpaperFilter]:
        """
        Build a custom filter chain based on specified order
        
        Args:
            filter_order: List of filter names in desired order
        
        Returns:
            Head of the filter chain or None if no valid filters
        """
        filter_map = {
            'exclusion': lambda: ExclusionFilter(self.config_manager),
            'time_based': lambda: TimeBasedFilter(self.metadata_manager),
            'luminosity': lambda: LuminosityFilter(self.metadata_manager),
            'recent': lambda: RecentFilter()
        }
        
        filters = []
        for filter_name in filter_order:
            if filter_name in filter_map:
                filters.append(filter_map[filter_name]())
            else:
                self.logger.warning(f"Unknown filter: {filter_name}")
        
        if not filters:
            return None
        
        # Chain filters together
        for i in range(len(filters) - 1):
            filters[i].set_next(filters[i + 1])
        
        self.chain_head = filters[0]
        return filters[0]
    
    def apply(self, wallpapers: List[Path], context: Dict[str, Any]) -> List[Path]:
        """
        Apply the filter chain to a list of wallpapers
        
        Args:
            wallpapers: List of wallpaper paths
            context: Context for filtering
        
        Returns:
            Filtered list of wallpapers
        """
        if not self.chain_head:
            self.build_default_chain()
        
        if not self.chain_head:
            return wallpapers
        
        initial_count = len(wallpapers)
        filtered = self.chain_head.filter(wallpapers, context)
        final_count = len(filtered)
        
        if final_count < initial_count:
            self.logger.info(
                f"Filter chain: {initial_count} -> {final_count} wallpapers "
                f"({initial_count - final_count} filtered)"
            )
        
        return filtered
    
    def get_chain_info(self) -> List[Dict[str, Any]]:
        """
        Get information about the current filter chain
        
        Returns:
            List of filter information dictionaries
        """
        if not self.chain_head:
            return []
        
        chain_info = []
        current = self.chain_head
        
        while current:
            chain_info.append(current.get_filter_info())
            current = current.next_filter
        
        return chain_info