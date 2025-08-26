#!/usr/bin/env python3
"""
Quick wallpaper analyzer - analyzes wallpapers without heavy UI
"""
import sys
from pathlib import Path
from wallpaper_analyzer import WallpaperAnalyzer
from wallpaper_metadata import WallpaperMetadata
from config_manager import ConfigManager

def main():
    print("Quick Wallpaper Analyzer")
    print("-" * 40)
    
    # Initialize
    config = ConfigManager()
    analyzer = WallpaperAnalyzer(num_workers=6)  # Use more workers for speed
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
            # Check if already analyzed
            existing = metadata_manager.get_wallpaper_metadata(str(file))
            if not existing:
                image_files.append(file)
    
    if not image_files:
        print("All wallpapers already analyzed!")
        stats = metadata_manager.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total: {stats['total']}")
        print(f"  Dark: {stats['classifications']['dark']}")
        print(f"  Medium: {stats['classifications']['medium']}")
        print(f"  Light: {stats['classifications']['light']}")
        return 0
    
    print(f"Found {len(image_files)} new wallpapers to analyze")
    
    # Analyze each
    for i, img in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] Analyzing {img.name}...", end="")
        try:
            result = analyzer.analyze_wallpaper(img)
            metadata_manager.update_wallpaper_metadata(str(img), result)
            print(f" {result['classification']}")
        except Exception as e:
            print(f" ERROR: {e}")
    
    # Show final statistics
    stats = metadata_manager.get_statistics()
    print(f"\nFinal Statistics:")
    print(f"  Total: {stats['total']}")
    print(f"  Dark: {stats['classifications']['dark']}")
    print(f"  Medium: {stats['classifications']['medium']}")
    print(f"  Light: {stats['classifications']['light']}")
    
    print("\nDone! Metadata saved.")
    return 0

if __name__ == "__main__":
    sys.exit(main())