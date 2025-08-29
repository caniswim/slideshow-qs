#!/usr/bin/env python3
"""
Smart random strategy that avoids recently shown wallpapers
"""
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base_strategy import WallpaperSelectionStrategy


class SmartRandomStrategy(WallpaperSelectionStrategy):
    """
    Smart random selection that tracks and avoids recent wallpapers
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.avoid_percentage = self.config.get('avoid_recent_percentage', 25)
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.unused_wallpapers = []
        self.recent_wallpapers = []
        self.session_history = []
        self.max_recent = 0
    
    def select(self, wallpapers: List[Path], context: Dict[str, Any]) -> Optional[Path]:
        """
        Select a wallpaper avoiding recent ones
        
        Args:
            wallpapers: Available wallpapers after filtering
            context: Contains 'current_wallpaper' and other context
        
        Returns:
            Selected wallpaper or None
        """
        if not wallpapers:
            return None
        
        # Initialize unused list if empty or wallpaper list changed
        if not self.unused_wallpapers or set(self.unused_wallpapers) != set(wallpapers):
            self.unused_wallpapers = wallpapers.copy()
            # Remove current wallpaper from unused
            current = context.get('current_wallpaper')
            if current and current in self.unused_wallpapers:
                self.unused_wallpapers.remove(current)
        
        # Calculate max recent based on percentage
        self.max_recent = max(1, len(wallpapers) * self.avoid_percentage // 100)
        
        # Filter out recent wallpapers from unused list
        available = [w for w in self.unused_wallpapers if w not in self.recent_wallpapers]
        
        # If no wallpapers available after filtering, use unused list
        if not available:
            available = self.unused_wallpapers
        
        # If still no wallpapers, use full list minus current
        if not available:
            current = context.get('current_wallpaper')
            available = [w for w in wallpapers if w != current]
        
        # If only current wallpaper exists, return None
        if not available:
            return None
        
        selected = random.choice(available)
        
        if self.validate_selection(selected):
            return selected
        
        # If invalid, remove from lists and try again
        if selected in self.unused_wallpapers:
            self.unused_wallpapers.remove(selected)
        if selected in available:
            available.remove(selected)
        
        # Recursive retry with cleaned list
        return self.select(wallpapers, context) if available else None
    
    def update_tracking(self, wallpaper: Path) -> None:
        """Update tracking lists after wallpaper selection"""
        # Add to session history
        if wallpaper not in self.session_history:
            self.session_history.append(wallpaper)
        
        # Remove from unused list
        if wallpaper in self.unused_wallpapers:
            self.unused_wallpapers.remove(wallpaper)
        
        # Update recent wallpapers list
        if wallpaper in self.recent_wallpapers:
            self.recent_wallpapers.remove(wallpaper)
        self.recent_wallpapers.append(wallpaper)
        
        # Keep recent list within size limit
        if len(self.recent_wallpapers) > self.max_recent:
            self.recent_wallpapers.pop(0)
        
        # Reset unused if all wallpapers have been shown
        if not self.unused_wallpapers and self.session_history:
            # Get current wallpaper list from last selection context
            # This will be updated on next select() call
            self.unused_wallpapers = []
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            'unused_wallpapers': [str(p) for p in self.unused_wallpapers],
            'recent_wallpapers': [str(p) for p in self.recent_wallpapers],
            'session_history': [str(p) for p in self.session_history],
            'max_recent': self.max_recent,
            'avoid_percentage': self.avoid_percentage
        }
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore from saved state"""
        self.unused_wallpapers = [Path(p) for p in state.get('unused_wallpapers', [])]
        self.recent_wallpapers = [Path(p) for p in state.get('recent_wallpapers', [])]
        self.session_history = [Path(p) for p in state.get('session_history', [])]
        self.max_recent = state.get('max_recent', 0)
        self.avoid_percentage = state.get('avoid_percentage', 25)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_stats()
        stats.update({
            'unused_count': len(self.unused_wallpapers),
            'recent_count': len(self.recent_wallpapers),
            'max_recent': self.max_recent,
            'avoid_percentage': self.avoid_percentage
        })
        return stats