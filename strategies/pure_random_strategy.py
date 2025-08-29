#!/usr/bin/env python3
"""
Pure random strategy with no tracking or avoidance
"""
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base_strategy import WallpaperSelectionStrategy


class PureRandomStrategy(WallpaperSelectionStrategy):
    """
    Pure random selection without any tracking or avoidance
    """
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.session_history = []
    
    def select(self, wallpapers: List[Path], context: Dict[str, Any]) -> Optional[Path]:
        """
        Select a random wallpaper from the available list
        
        Args:
            wallpapers: Available wallpapers after filtering
            context: Additional context (ignored in pure random)
        
        Returns:
            Randomly selected wallpaper or None
        """
        if not wallpapers:
            return None
        
        # Pure random selection
        selected = random.choice(wallpapers)
        
        if self.validate_selection(selected):
            return selected
        
        # If invalid, remove and retry
        wallpapers = [w for w in wallpapers if w != selected]
        return self.select(wallpapers, context) if wallpapers else None
    
    def update_tracking(self, wallpaper: Path) -> None:
        """Update tracking (minimal for pure random)"""
        if wallpaper not in self.session_history:
            self.session_history.append(wallpaper)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            'session_history': [str(p) for p in self.session_history]
        }
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore from saved state"""
        self.session_history = [Path(p) for p in state.get('session_history', [])]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_stats()
        stats.update({
            'mode': 'pure_random',
            'tracking': 'minimal'
        })
        return stats