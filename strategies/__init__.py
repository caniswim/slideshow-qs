"""
Wallpaper selection strategies using Strategy Pattern
"""
from .base_strategy import WallpaperSelectionStrategy
from .smart_random_strategy import SmartRandomStrategy
from .pure_random_strategy import PureRandomStrategy
from .sequential_shuffle_strategy import SequentialShuffleStrategy
from .time_based_strategy import TimeBasedStrategy

__all__ = [
    'WallpaperSelectionStrategy',
    'SmartRandomStrategy',
    'PureRandomStrategy',
    'SequentialShuffleStrategy',
    'TimeBasedStrategy',
]