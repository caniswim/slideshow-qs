"""
Wallpaper filters using Chain of Responsibility pattern
"""
from .base_filter import WallpaperFilter
from .time_based_filter import TimeBasedFilter
from .luminosity_filter import LuminosityFilter
from .exclusion_filter import ExclusionFilter
from .recent_filter import RecentFilter
from .filter_chain import FilterChain

__all__ = [
    'WallpaperFilter',
    'TimeBasedFilter',
    'LuminosityFilter',
    'ExclusionFilter',
    'RecentFilter',
    'FilterChain',
]