#!/usr/bin/env python3
"""
Wallpaper analyzer for luminosity and color analysis
"""
import json
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib

try:
    from PIL import Image, ImageStat
    HAS_PIL = True
except ImportError:
    print("Warning: Pillow not installed. Wallpaper analysis disabled.")
    HAS_PIL = False


class WallpaperAnalyzer:
    """Analyzes wallpapers for luminosity and dominant colors"""
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        # Optimized thresholds for balanced distribution (1/3 each category)
        self.luminosity_thresholds = {
            'dark': 0.18,   # Images with luminosity < 0.18 are dark
            'light': 0.36   # Images with luminosity > 0.36 are light
        }
        
    def get_image_hash(self, image_path: Path) -> str:
        """Generate hash for image file to detect changes"""
        stat = image_path.stat()
        hash_input = f"{image_path}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def calculate_luminosity(self, image_path: Path) -> float:
        """Calculate average luminosity of an image (0=black, 1=white)"""
        if not HAS_PIL:
            return 0.5
            
        try:
            with Image.open(image_path) as img:
                # Method 1: Convert to grayscale and get mean
                # This is more accurate as PIL uses proper luminance conversion
                gray_img = img.convert('L')  # Convert to grayscale
                
                # Resize for faster processing
                gray_img.thumbnail((500, 500), Image.Resampling.LANCZOS)
                
                # Calculate statistics
                stat = ImageStat.Stat(gray_img)
                
                # Get mean brightness (0-255)
                mean_brightness = stat.mean[0]
                
                # Alternative: Use RMS for more accurate perception
                # rms_brightness = stat.rms[0]
                
                # Normalize to 0-1 range
                luminosity = mean_brightness / 255.0
                
                return luminosity
                
        except Exception as e:
            print(f"Error calculating luminosity for {image_path}: {e}")
            return 0.5
    
    def get_dominant_colors(self, image_path: Path, num_colors: int = 5) -> List[str]:
        """Extract dominant colors from image"""
        if not HAS_PIL:
            return []
            
        try:
            with Image.open(image_path) as img:
                # Convert to RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize for faster processing
                img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                
                # Get colors using quantization
                img = img.quantize(colors=num_colors)
                palette = img.getpalette()
                
                colors = []
                for i in range(num_colors):
                    if palette:
                        r = palette[i * 3]
                        g = palette[i * 3 + 1]
                        b = palette[i * 3 + 2]
                        colors.append(f"#{r:02x}{g:02x}{b:02x}")
                
                return colors
                
        except Exception as e:
            print(f"Error extracting colors from {image_path}: {e}")
            return []
    
    def classify_luminosity(self, luminosity: float) -> str:
        """Classify luminosity into dark/medium/light"""
        if luminosity < self.luminosity_thresholds['dark']:
            return 'dark'
        elif luminosity > self.luminosity_thresholds['light']:
            return 'light'
        else:
            return 'medium'
    
    def get_time_preference(self, classification: str) -> List[str]:
        """Get recommended time periods for wallpaper classification"""
        time_map = {
            'dark': ['night', 'evening', 'late_night'],
            'medium': ['dawn', 'dusk', 'morning', 'afternoon'],
            'light': ['day', 'morning', 'afternoon']
        }
        return time_map.get(classification, ['any'])
    
    def analyze_wallpaper(self, image_path: Path) -> Dict:
        """Analyze a single wallpaper"""
        luminosity = self.calculate_luminosity(image_path)
        classification = self.classify_luminosity(luminosity)
        
        return {
            'path': str(image_path),
            'filename': image_path.name,
            'hash': self.get_image_hash(image_path),
            'luminosity': round(luminosity, 3),
            'classification': classification,
            'dominant_colors': self.get_dominant_colors(image_path),
            'time_preference': self.get_time_preference(classification),
            'analyzed_at': datetime.now().isoformat(),
            'auto_classified': True,
            'manual_override': False,
            'custom_tags': []
        }
    
    def analyze_directory(self, directory: Path, progress_callback=None, existing_metadata: Dict = None) -> Dict[str, Dict]:
        """Analyze all wallpapers in a directory
        
        Args:
            directory: Path to wallpaper directory
            progress_callback: Callback for progress updates
            existing_metadata: Existing metadata to preserve manual overrides
        """
        if not HAS_PIL:
            print("Pillow not installed. Cannot analyze wallpapers.")
            return {}
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in image_extensions:
                image_files.append(file)
        
        if not image_files:
            return {}
        
        results = {}
        total = len(image_files)
        completed = 0
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit tasks, skipping files with manual overrides
            future_to_path = {}
            skipped = []
            
            for path in image_files:
                path_str = str(path)
                
                # Check if this file has a manual override
                if existing_metadata and path_str in existing_metadata:
                    existing = existing_metadata[path_str]
                    if existing.get('manual_override', False):
                        # Preserve existing manual classification
                        results[path_str] = existing
                        skipped.append(path.name)
                        completed += 1
                        if progress_callback:
                            progress_callback(completed, total, f"Skipped (manual): {path.name}")
                        continue
                
                # Submit for analysis
                future_to_path[executor.submit(self.analyze_wallpaper, path)] = path
            
            # Process results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    results[str(path)] = result
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, total, path.name)
                        
                except Exception as e:
                    print(f"Error analyzing {path}: {e}")
                    completed += 1
        
        if skipped:
            print(f"Skipped {len(skipped)} files with manual classifications")
        
        return results
    
    def get_wallpapers_for_time(self, metadata: Dict, current_hour: int) -> List[str]:
        """Get wallpapers suitable for current time"""
        # Define time periods
        time_periods = {
            'late_night': (0, 5),
            'dawn': (5, 7),
            'morning': (7, 12),
            'afternoon': (12, 17),
            'dusk': (17, 19),
            'evening': (19, 22),
            'night': (22, 24)
        }
        
        # Find current period
        current_periods = []
        for period, (start, end) in time_periods.items():
            if start <= current_hour < end:
                current_periods.append(period)
        
        # Filter wallpapers
        suitable = []
        for path, data in metadata.items():
            time_prefs = data.get('time_preference', ['any'])
            if 'any' in time_prefs or any(p in time_prefs for p in current_periods):
                suitable.append(path)
        
        return suitable
    
    def get_statistics(self, metadata: Dict) -> Dict:
        """Get statistics about analyzed wallpapers"""
        if not metadata:
            return {}
        
        classifications = {'dark': 0, 'medium': 0, 'light': 0}
        luminosities = []
        
        for data in metadata.values():
            classification = data.get('classification', 'medium')
            classifications[classification] += 1
            luminosities.append(data.get('luminosity', 0.5))
        
        return {
            'total': len(metadata),
            'classifications': classifications,
            'average_luminosity': round(np.mean(luminosities), 3) if luminosities else 0.5,
            'min_luminosity': round(min(luminosities), 3) if luminosities else 0,
            'max_luminosity': round(max(luminosities), 3) if luminosities else 1
        }