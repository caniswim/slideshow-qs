#!/usr/bin/env python3
"""
Metadata manager for wallpaper classification and time-based selection
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
            },
            'any': {
                'enabled': True,
                'time_ranges': [
                    {'start': '00:00', 'end': '23:59'},  # All day
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
        
        return active if active else ['any']
    
    def get_wallpapers_for_current_time(self, current_time: time = None) -> List[str]:
        """Get wallpapers suitable for the current time"""
        active_classifications = self.get_active_classifications(current_time)
        
        suitable = []
        for path, data in self.metadata.items():
            classification = data.get('classification', 'medium')
            
            # Check if wallpaper's classification matches active ones
            if classification in active_classifications or 'any' in active_classifications:
                suitable.append(path)
        
        return suitable
    
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