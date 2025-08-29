#!/usr/bin/env python3
"""
Base filter class for Chain of Responsibility pattern
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging


class WallpaperFilter(ABC):
    """Abstract base class for wallpaper filters"""
    
    def __init__(self, next_filter: Optional['WallpaperFilter'] = None):
        """
        Initialize filter with optional next filter in chain
        
        Args:
            next_filter: Next filter in the chain of responsibility
        """
        self.next_filter = next_filter
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def set_next(self, next_filter: 'WallpaperFilter') -> 'WallpaperFilter':
        """
        Set the next filter in the chain
        
        Args:
            next_filter: The filter to chain after this one
        
        Returns:
            The next filter (for chaining calls)
        """
        self.next_filter = next_filter
        return next_filter
    
    def filter(self, wallpapers: List[Path], context: Dict[str, Any]) -> List[Path]:
        """
        Filter wallpapers and pass to next filter in chain
        
        Args:
            wallpapers: List of wallpaper paths to filter
            context: Context information for filtering
        
        Returns:
            Filtered list of wallpapers
        """
        # Apply this filter's logic
        filtered = self.apply_filter(wallpapers, context)
        
        # Log filtering results
        self.logger.debug(
            f"{self.__class__.__name__}: {len(wallpapers)} -> {len(filtered)} wallpapers"
        )
        
        # Pass to next filter if exists
        if self.next_filter:
            return self.next_filter.filter(filtered, context)
        
        return filtered
    
    @abstractmethod
    def apply_filter(self, wallpapers: List[Path], context: Dict[str, Any]) -> List[Path]:
        """
        Apply this filter's specific logic
        
        Args:
            wallpapers: List of wallpaper paths to filter
            context: Context information for filtering
        
        Returns:
            Filtered list of wallpapers
        """
        pass
    
    def get_filter_info(self) -> Dict[str, Any]:
        """
        Get information about this filter for debugging
        
        Returns:
            Dictionary with filter information
        """
        return {
            'name': self.__class__.__name__,
            'has_next': self.next_filter is not None,
            'next_filter': self.next_filter.__class__.__name__ if self.next_filter else None
        }