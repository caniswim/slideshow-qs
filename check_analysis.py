#!/usr/bin/env python3
import json
from pathlib import Path
from wallpaper_metadata import WallpaperMetadata
from config_manager import ConfigManager

# Initialize
config = ConfigManager()
metadata = WallpaperMetadata(config.config_dir)

# Check if metadata file exists
metadata_file = config.config_dir / 'wallpaper_metadata.json'
schedules_file = config.config_dir / 'time_schedules.json'

print("="*60)
print("WALLPAPER ANALYSIS RESULTS")
print("="*60)

if metadata_file.exists():
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    
    # Count classifications
    dark = sum(1 for v in data.values() if v.get('classification') == 'dark')
    medium = sum(1 for v in data.values() if v.get('classification') == 'medium')
    light = sum(1 for v in data.values() if v.get('classification') == 'light')
    total = len(data)
    
    print(f"\n📊 Statistics:")
    print(f"  Total wallpapers analyzed: {total}")
    print(f"  Dark wallpapers: {dark} ({dark/total*100:.1f}%)")
    print(f"  Medium wallpapers: {medium} ({medium/total*100:.1f}%)")
    print(f"  Light wallpapers: {light} ({light/total*100:.1f}%)")
    
    # Show sample wallpapers
    print("\n📝 Sample Classifications:")
    for i, (path, info) in enumerate(list(data.items())[:5]):
        name = Path(path).name[:30]
        classification = info.get('classification', 'unknown')
        luminosity = info.get('luminosity', 0)
        print(f"  {name}: {classification} (luminosity: {luminosity:.2f})")
else:
    print("\n❌ No metadata file found. Run analyze_wallpapers.py first.")

print("\n📅 Time Schedules:")
if schedules_file.exists():
    with open(schedules_file, 'r') as f:
        schedules = json.load(f)
    
    for classification, schedule in schedules.items():
        if classification == 'any':
            continue
        status = "✓" if schedule.get('enabled', True) else "✗"
        print(f"\n{classification.upper()} [{status}]:")
        for time_range in schedule.get('time_ranges', []):
            print(f"  {time_range['start']} - {time_range['end']}")
else:
    print("  Using default schedules")

print("\n✅ To enable time-based selection:")
print("  1. Open settings in the app")
print("  2. Enable 'Time-based selection' option")
print("  3. Wallpapers will change based on time of day")