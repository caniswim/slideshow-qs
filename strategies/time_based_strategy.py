#!/usr/bin/env python3
"""
Time-based strategy that selects wallpapers based on time of day and luminosity
"""
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base_strategy import WallpaperSelectionStrategy


class TimeBasedStrategy(WallpaperSelectionStrategy):
    """
    Time-based selection that considers wallpaper luminosity and time of day
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.metadata_manager = config.get('metadata_manager') if config else None
        self.inner_strategy = config.get('inner_strategy') if config else None
        super().__init__(config)
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.session_history = []
        self.time_filtered_cache = {}
        self.cache_timestamp = None
        if self.inner_strategy:
            self.inner_strategy.reset()
    
    def select(self, wallpapers: List[Path], context: Dict[str, Any]) -> Optional[Path]:
        """
        Select a wallpaper based on current time and luminosity
        
        Args:
            wallpapers: Available wallpapers (already filtered by time if time-based is enabled)
            context: Contains 'current_wallpaper', 'current_time', etc.
        
        Returns:
            Selected wallpaper appropriate for current time or None
        """
        if not wallpapers:
            return None
        
        # If we have an inner strategy (like smart random), delegate to it
        # The wallpapers list should already be filtered by time
        if self.inner_strategy:
            selected = self.inner_strategy.select(wallpapers, context)
        else:
            # Fallback to simple random selection from time-filtered wallpapers
            selected = random.choice(wallpapers) if wallpapers else None
        
        if selected and self.validate_selection(selected):
            return selected
        
        return None
    
    def update_tracking(self, wallpaper: Path) -> None:
        """Update tracking after wallpaper selection"""
        if wallpaper not in self.session_history:
            self.session_history.append(wallpaper)
        
        # Also update inner strategy if present
        if self.inner_strategy:
            self.inner_strategy.update_tracking(wallpaper)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        state = {
            'session_history': [str(p) for p in self.session_history],
            'cache_timestamp': self.cache_timestamp.isoformat() if self.cache_timestamp else None
        }
        
        # Include inner strategy state if present
        if self.inner_strategy:
            state['inner_strategy_state'] = self.inner_strategy.get_state()
        
        return state
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore from saved state"""
        self.session_history = [Path(p) for p in state.get('session_history', [])]
        
        cache_ts = state.get('cache_timestamp')
        self.cache_timestamp = datetime.fromisoformat(cache_ts) if cache_ts else None
        
        # Restore inner strategy state if present
        if self.inner_strategy and 'inner_strategy_state' in state:
            self.inner_strategy.restore_state(state['inner_strategy_state'])
    
    def invalidate_cache(self) -> None:
        """Invalidate the time-filtered cache"""
        self.time_filtered_cache = {}
        self.cache_timestamp = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_stats()
        stats.update({
            'mode': 'time_based',
            'has_inner_strategy': self.inner_strategy is not None,
            'cache_valid': self.cache_timestamp is not None
        })
        
        if self.inner_strategy:
            stats['inner_strategy_stats'] = self.inner_strategy.get_stats()
        
        return stats