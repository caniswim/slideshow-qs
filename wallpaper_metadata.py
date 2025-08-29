#!/usr/bin/env python3
"""
Metadata manager for wallpaper classification and time-based selection
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, time
import threading


class WallpaperMetadata:
    """Manages wallpaper metadata including luminosity classification and time preferences"""
    
    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = Path.home() / '.config' / 'wallpaper-changer'
        
        self.config_dir = config_dir
        self.metadata_file = config_dir / 'wallpaper_metadata.json'
        self.time_schedules_file = config_dir / 'time_schedules.json'
        
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data
        self.metadata = self.load_metadata()
        self.time_schedules = self.load_time_schedules()
        
        # Thread lock for concurrent access
        self.lock = threading.Lock()
        
        # Cache for time-based filtering
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 60  # Cache TTL in seconds
    
    def get_default_time_schedules(self) -> Dict:
        """Get default time schedules for each luminosity category"""
        return {
            'dark': {
                'enabled': True,
                'time_ranges': [
                    {'start': '20:00', 'end': '06:00'},  # Night
                ]
            },
            'medium': {
                'enabled': True,
                'time_ranges': [
                    {'start': '06:00', 'end': '09:00'},  # Morning transition
                    {'start': '17:00', 'end': '20:00'},  # Evening transition
                ]
            },
            'light': {
                'enabled': True,
                'time_ranges': [
                    {'start': '09:00', 'end': '17:00'},  # Day
                ]
            }
        }
    
    def load_metadata(self) -> Dict:
        """Load wallpaper metadata from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading metadata: {e}")
                return {}
        return {}
    
    def load_time_schedules(self) -> Dict:
        """Load time schedules configuration"""
        if self.time_schedules_file.exists():
            try:
                with open(self.time_schedules_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading time schedules: {e}")
                return self.get_default_time_schedules()
        return self.get_default_time_schedules()
    
    def save_metadata(self):
        """Save wallpaper metadata to file"""
        with self.lock:
            try:
                with open(self.metadata_file, 'w') as f:
                    json.dump(self.metadata, f, indent=2)
            except IOError as e:
                print(f"Error saving metadata: {e}")
    
    def save_time_schedules(self):
        """Save time schedules to file"""
        with self.lock:
            try:
                with open(self.time_schedules_file, 'w') as f:
                    json.dump(self.time_schedules, f, indent=2)
            except IOError as e:
                print(f"Error saving time schedules: {e}")
    
    def update_wallpaper_metadata(self, path: str, data: Dict):
        """Update metadata for a single wallpaper"""
        with self.lock:
            self.metadata[path] = data
            self.save_metadata()
    
    def update_batch_metadata(self, metadata_dict: Dict):
        """Update metadata for multiple wallpapers"""
        with self.lock:
            self.metadata.update(metadata_dict)
            self.save_metadata()
    
    def get_wallpaper_metadata(self, path: str) -> Optional[Dict]:
        """Get metadata for a specific wallpaper"""
        return self.metadata.get(path)
    
    def override_classification(self, path: str, classification: str):
        """Manually override the classification of a wallpaper"""
        if path in self.metadata:
            self.metadata[path]['classification'] = classification
            self.metadata[path]['manual_override'] = True
            self.metadata[path]['override_date'] = datetime.now().isoformat()
            self.save_metadata()
    
    def add_custom_tag(self, path: str, tag: str):
        """Add a custom tag to a wallpaper"""
        if path in self.metadata:
            tags = self.metadata[path].get('custom_tags', [])
            if tag not in tags:
                tags.append(tag)
                self.metadata[path]['custom_tags'] = tags
                self.save_metadata()
    
    def remove_custom_tag(self, path: str, tag: str):
        """Remove a custom tag from a wallpaper"""
        if path in self.metadata:
            tags = self.metadata[path].get('custom_tags', [])
            if tag in tags:
                tags.remove(tag)
                self.metadata[path]['custom_tags'] = tags
                self.save_metadata()
    
    def update_time_schedule(self, classification: str, time_ranges: List[Dict]):
        """Update time schedule for a classification"""
        if classification in self.time_schedules:
            self.time_schedules[classification]['time_ranges'] = time_ranges
            self.save_time_schedules()
    
    def set_schedule_enabled(self, classification: str, enabled: bool):
        """Enable or disable a time schedule"""
        if classification in self.time_schedules:
            self.time_schedules[classification]['enabled'] = enabled
            self.save_time_schedules()
    
    def parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        except:
            return time(0, 0)
    
    def is_time_in_range(self, current_time: time, start_str: str, end_str: str) -> bool:
        """Check if current time is within a time range"""
        start = self.parse_time(start_str)
        end = self.parse_time(end_str)
        
        # Handle ranges that span midnight
        if start <= end:
            return start <= current_time <= end
        else:
            return current_time >= start or current_time <= end
    
    def get_active_classifications(self, current_time: time = None) -> List[str]:
        """Get classifications that are active at the current time"""
        if current_time is None:
            current_time = datetime.now().time()
        
        active = []
        for classification, schedule in self.time_schedules.items():
            if not schedule.get('enabled', True):
                continue
            
            for time_range in schedule.get('time_ranges', []):
                if self.is_time_in_range(current_time, 
                                        time_range['start'], 
                                        time_range['end']):
                    active.append(classification)
                    break
        
        # Return empty list if no classifications are active
        # This means no time-based filtering should be applied
        return active
    
    def _invalidate_cache(self):
        """Invalidate the cache"""
        self._cache = {}
        self._cache_timestamp = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_timestamp:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl
    
    def get_wallpapers_for_current_time(self, current_time: time = None) -> List[str]:
        """Get wallpapers suitable for the current time with caching"""
        if current_time is None:
            current_time = datetime.now().time()
        
        # Check cache
        cache_key = f"{current_time.hour}:{current_time.minute // 15}"  # 15-minute granularity
        
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]
        
        active_classifications = self.get_active_classifications(current_time)
        
        # If no classifications are active, return all wallpapers (no time filtering)
        if not active_classifications:
            result = list(self.metadata.keys())
        else:
            # Filter wallpapers by active classifications
            suitable = []
            for path, data in self.metadata.items():
                classification = data.get('classification', 'medium')
                
                # Check if wallpaper's classification matches active ones
                if classification in active_classifications:
                    suitable.append(path)
            
            result = suitable
        
        # Update cache
        if not self._is_cache_valid():
            self._cache = {}
            self._cache_timestamp = datetime.now()
        
        self._cache[cache_key] = result
        return result
    
    def get_wallpapers_by_classification(self, classification: str) -> List[str]:
        """Get all wallpapers with a specific classification"""
        return [
            path for path, data in self.metadata.items()
            if data.get('classification') == classification
        ]
    
    def get_wallpapers_by_tag(self, tag: str) -> List[str]:
        """Get all wallpapers with a specific custom tag"""
        results = []
        for path, data in self.metadata.items():
            if tag in data.get('custom_tags', []):
                results.append(path)
        return results
    
    def get_statistics(self) -> Dict:
        """Get statistics about metadata"""
        stats = {
            'total': len(self.metadata),
            'classifications': {'dark': 0, 'medium': 0, 'light': 0},
            'manual_overrides': 0,
            'with_custom_tags': 0
        }
        
        for data in self.metadata.values():
            classification = data.get('classification', 'medium')
            if classification in stats['classifications']:
                stats['classifications'][classification] += 1
            
            if data.get('manual_override', False):
                stats['manual_overrides'] += 1
            
            if data.get('custom_tags'):
                stats['with_custom_tags'] += 1
        
        return stats
    
    def clean_missing_wallpapers(self, existing_paths: List[str]):
        """Remove metadata for wallpapers that no longer exist"""
        with self.lock:
            removed = []
            for path in list(self.metadata.keys()):
                if path not in existing_paths:
                    del self.metadata[path]
                    removed.append(path)
            
            if removed:
                self.save_metadata()
                print(f"Removed metadata for {len(removed)} missing wallpapers")
            
            return removed
    
    def needs_analysis(self, path: str, file_hash: str) -> bool:
        """Check if a wallpaper needs (re)analysis"""
        if path not in self.metadata:
            return True
        
        # Check if hash has changed (file modified)
        stored_hash = self.metadata[path].get('hash')
        if stored_hash != file_hash:
            return True
        
        # Don't re-analyze if manually overridden
        if self.metadata[path].get('manual_override', False):
            return False
        
        return False
    
    def validate_schedules(self) -> Dict[str, Any]:
        """Validate time schedules for gaps and overlaps"""
        issues = {
            'gaps': [],
            'overlaps': [],
            'coverage': True
        }
        
        # Collect all time points
        time_points = []
        for classification, schedule in self.time_schedules.items():
            if not schedule.get('enabled', True):
                continue
            
            for time_range in schedule.get('time_ranges', []):
                start = self.parse_time(time_range['start'])
                end = self.parse_time(time_range['end'])
                time_points.append((start, end, classification))
        
        # Check for complete coverage of 24 hours
        minutes_covered = set()
        for start, end, classification in time_points:
            start_minutes = start.hour * 60 + start.minute
            end_minutes = end.hour * 60 + end.minute
            
            if start <= end:
                # Normal range
                for minute in range(start_minutes, end_minutes + 1):
                    minutes_covered.add(minute % (24 * 60))
            else:
                # Range spans midnight
                for minute in range(start_minutes, 24 * 60):
                    minutes_covered.add(minute)
                for minute in range(0, end_minutes + 1):
                    minutes_covered.add(minute)
        
        # Check if all minutes are covered
        total_minutes = 24 * 60
        if len(minutes_covered) < total_minutes:
            issues['coverage'] = False
            missing_minutes = total_minutes - len(minutes_covered)
            issues['gaps'].append(f"Missing {missing_minutes} minutes of coverage")
        
        return issues
    
    def export_schedules_config(self) -> str:
        """Export time schedules as formatted string for display"""
        lines = []
        for classification, schedule in self.time_schedules.items():
            if classification == 'any':
                continue
            
            status = "✓" if schedule.get('enabled', True) else "✗"
            lines.append(f"\n{classification.upper()} [{status}]:")
            
            for time_range in schedule.get('time_ranges', []):
                lines.append(f"  {time_range['start']} - {time_range['end']}")
        
        return '\n'.join(lines)