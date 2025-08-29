#!/usr/bin/env python3
"""
Sequential shuffle strategy that goes through all wallpapers before repeating
"""
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base_strategy import WallpaperSelectionStrategy


class SequentialShuffleStrategy(WallpaperSelectionStrategy):
    """
    Sequential selection through a shuffled list, reshuffling after completion
    """
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.shuffled_queue = []
        self.session_history = []
        self.current_cycle = []
    
    def select(self, wallpapers: List[Path], context: Dict[str, Any]) -> Optional[Path]:
        """
        Select next wallpaper in shuffled sequence
        
        Args:
            wallpapers: Available wallpapers after filtering
            context: Contains 'current_wallpaper' and other context
        
        Returns:
            Next wallpaper in sequence or None
        """
        if not wallpapers:
            return None
        
        # Check if wallpaper list changed
        if set(self.current_cycle) != set(wallpapers):
            # Wallpaper list changed, need to reshuffle
            self.shuffled_queue = wallpapers.copy()
            random.shuffle(self.shuffled_queue)
            self.current_cycle = wallpapers.copy()
            
            # Ensure current wallpaper isn't first in new shuffle
            current = context.get('current_wallpaper')
            if current and self.shuffled_queue and self.shuffled_queue[0] == current:
                # Move current to end if it's first
                self.shuffled_queue.append(self.shuffled_queue.pop(0))
        
        # If queue is empty, reshuffle
        if not self.shuffled_queue:
            self.shuffled_queue = wallpapers.copy()
            random.shuffle(self.shuffled_queue)
            self.current_cycle = wallpapers.copy()
            
            # Avoid immediate repeat of last shown wallpaper
            if self.session_history and self.shuffled_queue:
                last_shown = self.session_history[-1]
                if self.shuffled_queue[0] == last_shown:
                    # Move to end to avoid immediate repeat
                    self.shuffled_queue.append(self.shuffled_queue.pop(0))
        
        # Get next wallpaper from queue
        while self.shuffled_queue:
            selected = self.shuffled_queue[0]
            
            if self.validate_selection(selected):
                return selected
            
            # Remove invalid wallpaper and continue
            self.shuffled_queue.pop(0)
        
        return None
    
    def update_tracking(self, wallpaper: Path) -> None:
        """Update tracking after wallpaper selection"""
        # Remove from queue since it was shown
        if wallpaper in self.shuffled_queue:
            self.shuffled_queue.remove(wallpaper)
        
        # Add to session history
        if wallpaper not in self.session_history:
            self.session_history.append(wallpaper)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            'shuffled_queue': [str(p) for p in self.shuffled_queue],
            'session_history': [str(p) for p in self.session_history],
            'current_cycle': [str(p) for p in self.current_cycle]
        }
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore from saved state"""
        self.shuffled_queue = [Path(p) for p in state.get('shuffled_queue', [])]
        self.session_history = [Path(p) for p in state.get('session_history', [])]
        self.current_cycle = [Path(p) for p in state.get('current_cycle', [])]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_stats()
        stats.update({
            'queue_remaining': len(self.shuffled_queue),
            'cycle_size': len(self.current_cycle),
            'mode': 'sequential_shuffle'
        })
        return stats