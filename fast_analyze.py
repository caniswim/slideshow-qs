#!/usr/bin/env python3
"""
Fast wallpaper analyzer with optimized settings
"""
import sys
from pathlib import Path
from PIL import Image, ImageStat
from wallpaper_metadata import WallpaperMetadata
from config_manager import ConfigManager
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import json
import time

def analyze_image_fast(image_path: Path):
    """Fast analysis of a single image"""
    try:
        with Image.open(image_path) as img:
            # Convert to grayscale for luminosity
            gray = img.convert('L')
            # Smaller thumbnail for speed
            gray.thumbnail((200, 200), Image.Resampling.NEAREST)
            stat = ImageStat.Stat(gray)
            luminosity = stat.mean[0] / 255.0
            
            # Classify using optimized thresholds
            if luminosity < 0.18:
                classification = 'dark'
            elif luminosity > 0.36:
                classification = 'light'
            else:
                classification = 'medium'
            
            # Generate hash
            stat_info = image_path.stat()
            hash_str = f"{image_path}_{stat_info.st_size}_{stat_info.st_mtime}"
            file_hash = hashlib.md5(hash_str.encode()).hexdigest()
            
            return {
                'path': str(image_path),
                'filename': image_path.name,
                'hash': file_hash,
                'luminosity': round(luminosity, 3),
                'classification': classification,
                'dominant_colors': [],  # Skip color extraction for speed
                'time_preference': {
                    'dark': ['night', 'evening', 'late_night'],
                    'medium': ['dawn', 'dusk', 'morning', 'afternoon'],
                    'light': ['day', 'morning', 'afternoon']
                }[classification],
                'analyzed_at': datetime.now().isoformat(),
                'auto_classified': True,
                'manual_override': False,
                'custom_tags': []
            }
    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    print("="*60)
    print("FAST WALLPAPER ANALYZER (MULTI-THREADED)")
    print("="*60)
    
    # Initialize
    config = ConfigManager()
    metadata_manager = WallpaperMetadata(config.config_dir)
    
    # Get wallpaper directory
    directory = Path('/home/brunno/Imagens/wallpaper')
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return 1
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    image_files = []
    
    for file in directory.iterdir():
        if file.is_file() and file.suffix.lower() in image_extensions:
            image_files.append(file)
    
    print(f"Found {len(image_files)} wallpapers")
    
    # Use all available CPU threads (you have 20)
    num_threads = min(20, multiprocessing.cpu_count())
    print(f"Using {num_threads} threads for parallel processing")
    print("-"*60)
    
    # Load existing metadata first to check for manual overrides
    metadata_file = config.config_dir / 'wallpaper_metadata.json'
    existing_metadata = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                existing_metadata = json.load(f)
            print(f"Loaded {len(existing_metadata)} existing entries")
        except:
            pass
    
    # Analyze all with ThreadPoolExecutor
    results = {}
    classifications = {'dark': 0, 'medium': 0, 'light': 0}
    completed = 0
    skipped_manual = 0
    
    # Analysis phase with parallel processing
    print("Phase 1: Analyzing images (respecting manual overrides)...")
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit tasks, checking for manual overrides
        future_to_path = {}
        
        for path in image_files:
            path_str = str(path)
            
            # Check if this file has a manual override
            if path_str in existing_metadata and existing_metadata[path_str].get('manual_override', False):
                # Keep existing manual classification
                results[path_str] = existing_metadata[path_str]
                classifications[existing_metadata[path_str]['classification']] += 1
                completed += 1
                skipped_manual += 1
                
                # Update progress
                percentage = (completed / len(image_files)) * 100
                bar_length = 40
                filled = int(bar_length * completed // len(image_files))
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f'\r[{bar}] {percentage:.1f}% ({completed}/{len(image_files)}) - MANUAL: {path.name[:25]}...', 
                      end='', flush=True)
            else:
                # Submit for analysis
                future_to_path[executor.submit(analyze_image_fast, path)] = path
        
        # Process results as they complete
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            completed += 1
            
            try:
                result = future.result()
                if result:
                    results[str(path)] = result
                    classifications[result['classification']] += 1
                    
                    # Progress bar
                    percentage = (completed / len(image_files)) * 100
                    bar_length = 40
                    filled = int(bar_length * completed // len(image_files))
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    print(f'\r[{bar}] {percentage:.1f}% ({completed}/{len(image_files)}) - {path.name[:30]}...', 
                          end='', flush=True)
            except Exception as e:
                print(f"\nError processing {path.name}: {e}")
    
    print()  # New line after progress bar
    
    # Save directly to JSON (much faster)
    if results:
        print("\nPhase 2: Saving metadata...")
        print("-"*60)
        
        # Prepare metadata file path
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Results already contains both manual and auto classifications
        # No need to reload or merge
        
        # Save all at once (fastest method)
        print("Writing to disk...")
        start_time = time.time()
        
        try:
            # Write to temporary file first
            temp_file = metadata_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                # Save without indentation for speed
                json.dump(results, f, separators=(',', ':'))
            
            # Move temp file to final location (atomic operation)
            temp_file.replace(metadata_file)
            
            elapsed = time.time() - start_time
            print(f"[████████████████████████████████████████] 100.0% - Saved in {elapsed:.2f} seconds")
            
        except Exception as e:
            print(f"\nError saving metadata: {e}")
            return 1
    
    # Show statistics
    total = len(results)
    if total > 0:
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print(f"\n📊 Distribution:")
        print(f"  Dark:   {classifications['dark']:3d} ({classifications['dark']/total*100:5.1f}%)")
        print(f"  Medium: {classifications['medium']:3d} ({classifications['medium']/total*100:5.1f}%)")
        print(f"  Light:  {classifications['light']:3d} ({classifications['light']/total*100:5.1f}%)")
        
        if skipped_manual > 0:
            print(f"\n🔒 Manual Classifications Preserved: {skipped_manual}")
            print(f"  Auto-classified: {total - skipped_manual}")
        
        print(f"\n✅ Metadata saved to: {metadata_manager.metadata_file}")
        print("\n📝 Next steps:")
        print("  1. Open the gallery to see luminosity badges")
        print("  2. Right-click wallpapers to manually set luminosity")
        print("  3. Use the Filter dropdown to filter by Dark/Medium/Light")
        print("  4. Configure time schedules in Settings")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())