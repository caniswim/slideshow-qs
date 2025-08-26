#!/usr/bin/env python3
"""
Ultra-fast wallpaper analyzer - optimized for speed
"""
import sys
import json
from pathlib import Path
from PIL import Image, ImageStat
from datetime import datetime
import time

def analyze_batch(image_paths):
    """Analyze a batch of images"""
    results = {}
    for img_path in image_paths:
        try:
            with Image.open(img_path) as img:
                # Ultra-fast grayscale conversion
                gray = img.convert('L')
                # Very small thumbnail for maximum speed
                gray.thumbnail((100, 100), Image.Resampling.NEAREST)
                stat = ImageStat.Stat(gray)
                lum = stat.mean[0] / 255.0
                
                # Simple classification
                if lum < 0.18:
                    cls = 'dark'
                elif lum > 0.36:
                    cls = 'light'
                else:
                    cls = 'medium'
                
                results[str(img_path)] = {
                    'path': str(img_path),
                    'filename': img_path.name,
                    'luminosity': round(lum, 3),
                    'classification': cls,
                    'analyzed_at': datetime.now().isoformat(),
                    'auto_classified': True,
                    'manual_override': False
                }
        except Exception as e:
            print(f"Error with {img_path.name}: {e}")
    
    return results

def main():
    print("="*60)
    print("ULTRA-FAST WALLPAPER ANALYZER")
    print("="*60)
    
    start_time = time.time()
    
    # Get wallpaper directory
    directory = Path('/home/brunno/Imagens/wallpaper')
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return 1
    
    # Get all image files at once
    extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    image_files = [f for f in directory.iterdir() 
                   if f.is_file() and f.suffix.lower() in extensions]
    
    print(f"Found {len(image_files)} wallpapers")
    
    # Process in larger batches
    batch_size = 20
    all_results = {}
    classifications = {'dark': 0, 'medium': 0, 'light': 0}
    
    print("\nAnalyzing...")
    for i in range(0, len(image_files), batch_size):
        batch = image_files[i:i+batch_size]
        batch_results = analyze_batch(batch)
        
        # Count classifications
        for data in batch_results.values():
            classifications[data['classification']] += 1
        
        all_results.update(batch_results)
        
        # Progress
        progress = min(i + batch_size, len(image_files))
        percentage = (progress / len(image_files)) * 100
        bar_length = 40
        filled = int(bar_length * progress // len(image_files))
        bar = '█' * filled + '░' * (bar_length - filled)
        
        print(f'\r[{bar}] {percentage:.1f}% ({progress}/{len(image_files)})', end='', flush=True)
    
    print("\n\nSaving metadata (no formatting for speed)...")
    
    # Save without pretty printing (much faster)
    metadata_file = Path.home() / '.config' / 'wallpaper-changer' / 'wallpaper_metadata.json'
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load existing metadata if any
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                existing = json.load(f)
            existing.update(all_results)
            all_results = existing
    except:
        pass
    
    # Save without indentation (10x faster)
    with open(metadata_file, 'w') as f:
        json.dump(all_results, f, separators=(',', ':'))
    
    elapsed = time.time() - start_time
    
    # Statistics
    total = len(all_results)
    print(f"\n✅ Done in {elapsed:.1f} seconds!")
    print(f"\n📊 Distribution:")
    print(f"  Dark:   {classifications['dark']:3d} ({classifications['dark']/total*100:5.1f}%)")
    print(f"  Medium: {classifications['medium']:3d} ({classifications['medium']/total*100:5.1f}%)")  
    print(f"  Light:  {classifications['light']:3d} ({classifications['light']/total*100:5.1f}%)")
    
    print(f"\n💾 Metadata saved to: {metadata_file}")
    print("\n🎉 Your gallery filters are now ready to use!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())