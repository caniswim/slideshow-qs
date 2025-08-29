#!/usr/bin/env python3
"""
Base strategy interface for wallpaper selection
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any


class WallpaperSelectionStrategy(ABC):
    """Abstract base class for wallpaper selection strategies"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the strategy with configuration
        
        Args:
            config: Configuration dictionary with strategy-specific settings
        """
        self.config = config or {}
        self.session_history = []
        self.reset()
    
    @abstractmethod
    def select(self, wallpapers: List[Path], context: Dict[str, Any]) -> Optional[Path]:
        """
        Select a wallpaper from the available list
        
        Args:
            wallpapers: List of available wallpaper paths
            context: Additional context for selection (current wallpaper, time, etc.)
        
        Returns:
            Selected wallpaper path or None if no suitable wallpaper found
        """
        pass
    
    @abstractmethod
    def update_tracking(self, wallpaper: Path) -> None:
        """
        Update internal tracking after a wallpaper is selected
        
        Args:
            wallpaper: The wallpaper that was just displayed
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """
        Reset the strategy's internal state
        """
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the strategy for persistence or debugging
        
        Returns:
            Dictionary containing the strategy's current state
        """
        pass
    
    @abstractmethod
    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        Restore the strategy's state from a saved state
        
        Args:
            state: Previously saved state dictionary
        """
        pass
    
    def validate_selection(self, wallpaper: Path) -> bool:
        """
        Validate that a wallpaper selection is valid
        
        Args:
            wallpaper: Path to validate
        
        Returns:
            True if the wallpaper is valid, False otherwise
        """
        return wallpaper and wallpaper.exists() and wallpaper.is_file()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the strategy's performance
        
        Returns:
            Dictionary with strategy statistics
        """
        return {
            'name': self.__class__.__name__,
            'session_history_count': len(self.session_history),
            'config': self.config
        }