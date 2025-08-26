#!/usr/bin/env python3
"""
Script to configure time schedules for wallpaper categories
"""
import json
from pathlib import Path
from wallpaper_metadata import WallpaperMetadata
from config_manager import ConfigManager

def print_current_schedules(metadata):
    """Print current time schedules"""
    print("\n" + "="*60)
    print("CURRENT TIME SCHEDULES")
    print("="*60)
    
    schedules = metadata.time_schedules
    for classification in ['dark', 'medium', 'light']:
        schedule = schedules.get(classification, {})
        status = "✓ Enabled" if schedule.get('enabled', True) else "✗ Disabled"
        print(f"\n{classification.upper()} [{status}]:")
        
        for time_range in schedule.get('time_ranges', []):
            print(f"  {time_range['start']} - {time_range['end']}")

def edit_schedule(metadata, classification):
    """Edit schedule for a classification"""
    print(f"\nEditing {classification.upper()} schedule")
    print("-"*40)
    
    # Get current schedule
    current = metadata.time_schedules.get(classification, {})
    time_ranges = current.get('time_ranges', [])
    
    print("\nCurrent time ranges:")
    if time_ranges:
        for i, tr in enumerate(time_ranges, 1):
            print(f"  {i}. {tr['start']} - {tr['end']}")
    else:
        print("  No time ranges defined")
    
    print("\nOptions:")
    print("  1. Add new time range")
    print("  2. Remove time range")
    print("  3. Clear all ranges")
    print("  4. Set default ranges")
    print("  0. Back")
    
    choice = input("\nChoice: ").strip()
    
    if choice == '1':
        start = input("Start time (HH:MM): ").strip()
        end = input("End time (HH:MM): ").strip()
        
        # Validate format
        try:
            h, m = map(int, start.split(':'))
            if 0 <= h <= 23 and 0 <= m <= 59:
                h, m = map(int, end.split(':'))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    time_ranges.append({'start': start, 'end': end})
                    metadata.update_time_schedule(classification, time_ranges)
                    print(f"✓ Added time range: {start} - {end}")
                else:
                    print("✗ Invalid end time format")
            else:
                print("✗ Invalid start time format")
        except:
            print("✗ Invalid time format. Use HH:MM")
    
    elif choice == '2':
        if time_ranges:
            try:
                idx = int(input(f"Range to remove (1-{len(time_ranges)}): ")) - 1
                if 0 <= idx < len(time_ranges):
                    removed = time_ranges.pop(idx)
                    metadata.update_time_schedule(classification, time_ranges)
                    print(f"✓ Removed: {removed['start']} - {removed['end']}")
                else:
                    print("✗ Invalid range number")
            except:
                print("✗ Invalid input")
        else:
            print("No ranges to remove")
    
    elif choice == '3':
        metadata.update_time_schedule(classification, [])
        print("✓ Cleared all time ranges")
    
    elif choice == '4':
        defaults = {
            'dark': [{'start': '20:00', 'end': '06:00'}],
            'medium': [
                {'start': '06:00', 'end': '09:00'},
                {'start': '17:00', 'end': '20:00'}
            ],
            'light': [{'start': '09:00', 'end': '17:00'}]
        }
        metadata.update_time_schedule(classification, defaults.get(classification, []))
        print("✓ Set default ranges")

def toggle_schedule(metadata, classification):
    """Enable/disable a schedule"""
    current = metadata.time_schedules.get(classification, {})
    enabled = current.get('enabled', True)
    metadata.set_schedule_enabled(classification, not enabled)
    
    status = "disabled" if enabled else "enabled"
    print(f"✓ {classification.upper()} schedule {status}")

def main():
    print("="*60)
    print("TIME-BASED WALLPAPER SCHEDULE CONFIGURATOR")
    print("="*60)
    
    # Initialize
    config = ConfigManager()
    metadata = WallpaperMetadata(config.config_dir)
    
    while True:
        print_current_schedules(metadata)
        
        print("\n" + "="*60)
        print("OPTIONS")
        print("="*60)
        print("\n1. Edit DARK schedule")
        print("2. Edit MEDIUM schedule") 
        print("3. Edit LIGHT schedule")
        print("4. Toggle DARK enabled/disabled")
        print("5. Toggle MEDIUM enabled/disabled")
        print("6. Toggle LIGHT enabled/disabled")
        print("7. Set recommended schedules")
        print("8. Enable time-based selection in config")
        print("0. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            edit_schedule(metadata, 'dark')
        elif choice == '2':
            edit_schedule(metadata, 'medium')
        elif choice == '3':
            edit_schedule(metadata, 'light')
        elif choice == '4':
            toggle_schedule(metadata, 'dark')
        elif choice == '5':
            toggle_schedule(metadata, 'medium')
        elif choice == '6':
            toggle_schedule(metadata, 'light')
        elif choice == '7':
            # Set recommended schedules
            metadata.update_time_schedule('dark', [
                {'start': '20:00', 'end': '06:00'}
            ])
            metadata.update_time_schedule('medium', [
                {'start': '06:00', 'end': '09:00'},
                {'start': '17:00', 'end': '20:00'}
            ])
            metadata.update_time_schedule('light', [
                {'start': '09:00', 'end': '17:00'}
            ])
            print("\n✓ Set recommended schedules:")
            print("  DARK: 20:00 - 06:00 (night)")
            print("  MEDIUM: 06:00 - 09:00, 17:00 - 20:00 (transitions)")
            print("  LIGHT: 09:00 - 17:00 (day)")
        elif choice == '8':
            config.set('time_based_enabled', True)
            print("\n✓ Time-based selection enabled in config")
            print("  Wallpapers will now change based on time of day")
        else:
            print("Invalid choice")
    
    print("\n✓ Configuration saved!")
    print("  Restart the wallpaper app for changes to take effect")

if __name__ == "__main__":
    main()