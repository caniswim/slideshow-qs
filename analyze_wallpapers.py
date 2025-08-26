#!/usr/bin/env python3
"""
Script to analyze and classify all wallpapers in the collection
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from config_manager import ConfigManager
from wallpaper_manager import WallpaperManager
from wallpaper_analyzer import WallpaperAnalyzer
from wallpaper_metadata import WallpaperMetadata


def print_progress(completed: int, total: int, filename: str):
    """Print progress bar"""
    percentage = (completed / total) * 100 if total > 0 else 0
    bar_length = 40
    filled = int(bar_length * completed // total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_length - filled)
    
    # Clear line and print progress
    print(f'\r[{bar}] {percentage:.1f}% ({completed}/{total}) - {filename[:30]}...', end='', flush=True)
    
    if completed == total:
        print()  # New line when complete


def main():
    """Main analysis function"""
    print("="*60)
    print("WALLPAPER LUMINOSITY ANALYZER")
    print("="*60)
    
    # Initialize configuration
    config = ConfigManager()
    wallpaper_manager = WallpaperManager(config)
    
    # Get wallpaper directory
    directory = Path(config.get('wallpaper_directory', Path.home() / 'Imagens/wallpaper'))
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return 1
    
    print(f"\nDirectory: {directory}")
    print(f"Analyzing wallpapers for luminosity classification...")
    print("-"*60)
    
    # Analyze wallpapers
    start_time = datetime.now()
    results = wallpaper_manager.analyze_wallpapers(progress_callback=print_progress)
    end_time = datetime.now()
    
    if not results:
        print("\nNo wallpapers found to analyze.")
        return 1
    
    # Get statistics
    stats = wallpaper_manager.get_metadata_statistics()
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    
    print(f"\n📊 Statistics:")
    print(f"  Total wallpapers: {stats['total']}")
    print(f"  Dark wallpapers: {stats['classifications']['dark']} ({stats['classifications']['dark']/stats['total']*100:.1f}%)")
    print(f"  Medium wallpapers: {stats['classifications']['medium']} ({stats['classifications']['medium']/stats['total']*100:.1f}%)")
    print(f"  Light wallpapers: {stats['classifications']['light']} ({stats['classifications']['light']/stats['total']*100:.1f}%)")
    
    print(f"\n⏱️  Time taken: {(end_time - start_time).total_seconds():.2f} seconds")
    
    # Show time schedules
    print("\n📅 Default Time Schedules:")
    print(wallpaper_manager.metadata_manager.export_schedules_config())
    
    # Save analysis results
    metadata_file = config.config_dir / 'wallpaper_metadata.json'
    print(f"\n💾 Metadata saved to: {metadata_file}")
    
    print("\n✅ Analysis complete! The wallpaper system will now use time-based selection.")
    print("   To enable time-based selection, set 'time_based_enabled' to true in settings.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())