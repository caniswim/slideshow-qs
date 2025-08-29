#!/usr/bin/env python3
"""
Main application with system tray for wallpaper changer
"""
import sys
import os
import logging
from pathlib import Path

# Set environment variable to avoid conflicts
os.environ['QT_QPA_PLATFORM'] = 'xcb'

# Enable high-DPI scaling for better quality
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QFileDialog, QCheckBox, QDialogButtonBox,
    QMessageBox, QComboBox, QGroupBox, QSlider,
    QTabWidget, QTimeEdit, QListWidget, QListWidgetItem, 
    QGridLayout, QWidget
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPixmap

from config_manager import ConfigManager
from wallpaper_manager import WallpaperManager
from gallery_window_modern import ModernGalleryWindow
from logging_config import setup_logging
from settings_dialog_modern import ModernSettingsDialog


# Legacy SettingsDialog - replaced by ModernSettingsDialog
# Kept for reference but not used
'''
class SettingsDialog(QDialog):
    """Settings dialog for quick configuration"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the settings dialog UI"""
        self.setWindowTitle("Wallpaper Changer Settings")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Wallpaper directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Wallpaper Directory:"))
        self.dir_label = QLabel()
        dir_layout.addWidget(self.dir_label)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_button)
        layout.addLayout(dir_layout)
        
        # Change interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Change Interval (minutes):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(1440)  # Max 24 hours
        interval_layout.addWidget(self.interval_spin)
        layout.addLayout(interval_layout)
        
        # Auto change checkbox
        self.auto_change_check = QCheckBox("Enable automatic wallpaper change")
        layout.addWidget(self.auto_change_check)
        
        # Shuffle checkbox
        self.shuffle_check = QCheckBox("Shuffle wallpapers")
        layout.addWidget(self.shuffle_check)
        
        # Notifications checkbox
        self.notifications_check = QCheckBox("Show notifications")
        layout.addWidget(self.notifications_check)
        
        # Color sync checkbox
        self.color_sync_check = QCheckBox("Sync color scheme with wallpaper")
        self.color_sync_check.setToolTip("Generate Material Design colors from wallpaper (requires matugen)")
        layout.addWidget(self.color_sync_check)
        
        # Random mode settings group
        random_group = QGroupBox("Random Mode Settings")
        random_layout = QVBoxLayout()
        
        # Random mode selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Random Mode:"))
        self.random_mode_combo = QComboBox()
        self.random_mode_combo.addItems([
            "Smart Random (Avoid Recent)",
            "Pure Random",
            "Sequential Shuffle"
        ])
        self.random_mode_combo.setToolTip(
            "Smart: Avoids recently shown wallpapers\n"
            "Pure: Completely random selection\n"
            "Sequential: Shows all wallpapers before repeating"
        )
        mode_layout.addWidget(self.random_mode_combo)
        random_layout.addLayout(mode_layout)
        
        # Avoid recent percentage slider
        self.avoid_label = QLabel("Avoid Recent: 25%")
        random_layout.addWidget(self.avoid_label)
        
        self.avoid_slider = QSlider(Qt.Orientation.Horizontal)
        self.avoid_slider.setMinimum(10)
        self.avoid_slider.setMaximum(50)
        self.avoid_slider.setValue(25)
        self.avoid_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.avoid_slider.setTickInterval(10)
        self.avoid_slider.valueChanged.connect(self.on_avoid_slider_changed)
        self.avoid_slider.setToolTip("Percentage of wallpapers to avoid repeating in Smart Random mode")
        random_layout.addWidget(self.avoid_slider)
        
        random_group.setLayout(random_layout)
        layout.addWidget(random_group)
        
        # Connect combo box change to enable/disable slider
        self.random_mode_combo.currentIndexChanged.connect(self.on_random_mode_changed)
        
        layout.addStretch()
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def on_avoid_slider_changed(self, value):
        """Update label when slider changes"""
        self.avoid_label.setText(f"Avoid Recent: {value}%")
    
    def on_random_mode_changed(self, index):
        """Enable/disable slider based on random mode"""
        # Enable slider only for Smart Random mode (index 0)
        self.avoid_slider.setEnabled(index == 0)
        self.avoid_label.setEnabled(index == 0)
    
    def load_settings(self):
        """Load current settings"""
        self.dir_label.setText(self.config.get('wallpaper_directory', ''))
        self.interval_spin.setValue(self.config.get('change_interval', 30))
        self.auto_change_check.setChecked(self.config.get('auto_change_enabled', False))
        self.shuffle_check.setChecked(self.config.get('shuffle', True))
        self.notifications_check.setChecked(self.config.get('show_notifications', True))
        self.color_sync_check.setChecked(self.config.get('sync_color_scheme', True))
        
        # Load random mode settings
        mode = self.config.get('random_mode', 'smart')
        mode_index = {'smart': 0, 'pure': 1, 'sequential': 2}.get(mode, 0)
        self.random_mode_combo.setCurrentIndex(mode_index)
        
        avoid_percentage = self.config.get('avoid_recent_percentage', 25)
        self.avoid_slider.setValue(avoid_percentage)
        self.avoid_label.setText(f"Avoid Recent: {avoid_percentage}%")
        
        # Enable/disable slider based on mode
        self.avoid_slider.setEnabled(mode_index == 0)
        self.avoid_label.setEnabled(mode_index == 0)
    
    def browse_directory(self):
        """Browse for wallpaper directory"""
        current_dir = self.config.get('wallpaper_directory', str(Path.home()))
        directory = QFileDialog.getExistingDirectory(
            self, "Select Wallpaper Directory", current_dir
        )
        if directory:
            self.dir_label.setText(directory)
    
    def save_settings(self):
        """Save settings and close"""
        # Map combo box index to mode string
        mode_map = {0: 'smart', 1: 'pure', 2: 'sequential'}
        random_mode = mode_map.get(self.random_mode_combo.currentIndex(), 'smart')
        
        self.config.update({
            'wallpaper_directory': self.dir_label.text(),
            'change_interval': self.interval_spin.value(),
            'auto_change_enabled': self.auto_change_check.isChecked(),
            'shuffle': self.shuffle_check.isChecked(),
            'show_notifications': self.notifications_check.isChecked(),
            'sync_color_scheme': self.color_sync_check.isChecked(),
            'random_mode': random_mode,
            'avoid_recent_percentage': self.avoid_slider.value()
        })
        self.accept()
'''


class WallpaperChangerApp(QApplication):
    """Main application class"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # Don't quit when last window closes
        self.setQuitOnLastWindowClosed(False)
        
        # Initialize managers
        self.config_manager = ConfigManager()
        self.wallpaper_manager = WallpaperManager(self.config_manager)
        
        # Initialize UI components
        self.gallery_window = None
        self.settings_dialog = None
        
        # Create system tray
        self.create_tray_icon()
        
        # Setup auto-change timer
        self.auto_change_timer = QTimer()
        self.auto_change_timer.timeout.connect(self.auto_change_wallpaper)
        self.update_auto_change_timer()
        
        # Setup time display timer
        self.time_display_timer = QTimer()
        self.time_display_timer.timeout.connect(self.update_time_display)
        self.time_display_timer.start(1000)  # Update every second
        
        self.last_change_time = 0
        self.time_until_next = 0
        
        # Check for command line arguments via environment
        self.check_startup_actions()
    
    def create_tray_icon(self):
        """Create system tray icon and menu"""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Try to load custom icon, fallback to theme icon
        icon_path = Path(__file__).parent / 'assets' / 'icon.png'
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback to theme icon
            icon = QIcon.fromTheme('preferences-desktop-wallpaper')
            if icon.isNull():
                # Create a simple colored icon as last resort
                pixmap = QPixmap(64, 64)
                pixmap.fill(Qt.GlobalColor.darkBlue)
                icon = QIcon(pixmap)
            self.tray_icon.setIcon(icon)
        
        # Create context menu
        self.create_tray_menu()
        
        # Connect double-click
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
    
    def create_tray_menu(self):
        """Create tray icon context menu"""
        menu = QMenu()
        
        # Time until next change
        self.time_action = QAction("Next change: Disabled", menu)
        self.time_action.setEnabled(False)
        menu.addAction(self.time_action)
        
        menu.addSeparator()
        
        # Change wallpaper now
        change_now_action = QAction("🔄 Change Wallpaper Now", menu)
        change_now_action.triggered.connect(self.change_wallpaper_now)
        menu.addAction(change_now_action)
        
        # Next wallpaper
        next_action = QAction("⏭️ Next Wallpaper", menu)
        next_action.triggered.connect(self.next_wallpaper)
        menu.addAction(next_action)
        
        # Previous wallpaper
        prev_action = QAction("⏮️ Previous Wallpaper", menu)
        prev_action.triggered.connect(self.previous_wallpaper)
        menu.addAction(prev_action)
        
        menu.addSeparator()
        
        # Exclude current wallpaper
        exclude_action = QAction("🚫 Exclude Current Wallpaper", menu)
        exclude_action.setToolTip("Remove current wallpaper from rotation")
        exclude_action.triggered.connect(self.exclude_current_wallpaper)
        menu.addAction(exclude_action)
        
        menu.addSeparator()
        
        # Open gallery
        gallery_action = QAction("🖼️ Open Gallery", menu)
        gallery_action.triggered.connect(self.show_gallery)
        menu.addAction(gallery_action)
        
        menu.addSeparator()
        
        # Auto-change toggle
        self.auto_change_action = QAction("▶️ Enable Auto-Change", menu)
        self.auto_change_action.setCheckable(True)
        self.auto_change_action.setChecked(self.config_manager.get('auto_change_enabled', False))
        self.auto_change_action.triggered.connect(self.toggle_auto_change)
        self.update_auto_change_action()
        menu.addAction(self.auto_change_action)
        
        # Settings
        settings_action = QAction("⚙️ Settings", menu)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        # Session stats
        stats_action = QAction("📊 Session Statistics", menu)
        stats_action.triggered.connect(self.show_session_stats)
        menu.addAction(stats_action)
        
        # Reset session tracking
        reset_action = QAction("🔄 Reset Session Tracking", menu)
        reset_action.setToolTip("Start fresh with wallpaper randomization")
        reset_action.triggered.connect(self.reset_session_tracking)
        menu.addAction(reset_action)
        
        menu.addSeparator()
        
        # Recent wallpapers submenu
        recent_menu = menu.addMenu("📜 Recent Wallpapers")
        self.update_recent_menu(recent_menu)
        
        # Excluded wallpapers submenu
        excluded_menu = menu.addMenu("🚫 Excluded Wallpapers")
        self.update_excluded_menu(excluded_menu)
        
        menu.addSeparator()
        
        # About
        about_action = QAction("ℹ️ About", menu)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
        # Quit
        quit_action = QAction("❌ Quit", menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_menu = menu
    
    def update_recent_menu(self, recent_menu):
        """Update recent wallpapers menu"""
        recent_menu.clear()
        
        recent = self.wallpaper_manager.get_recent_wallpapers()
        if not recent:
            action = QAction("No recent wallpapers", recent_menu)
            action.setEnabled(False)
            recent_menu.addAction(action)
        else:
            for wallpaper in recent[:10]:  # Show last 10
                action = QAction(wallpaper.name, recent_menu)
                action.triggered.connect(lambda checked, p=wallpaper: self.set_wallpaper(p))
                recent_menu.addAction(action)
            
            if recent:
                recent_menu.addSeparator()
                clear_action = QAction("Clear History", recent_menu)
                clear_action.triggered.connect(self.clear_history)
                recent_menu.addAction(clear_action)
    
    def update_excluded_menu(self, excluded_menu):
        """Update excluded wallpapers menu"""
        excluded_menu.clear()
        
        excluded = self.config_manager.get('excluded_files', [])
        if not excluded:
            action = QAction("No excluded wallpapers", excluded_menu)
            action.setEnabled(False)
            excluded_menu.addAction(action)
        else:
            for file_path in excluded[:10]:  # Show first 10
                path = Path(file_path)
                action = QAction(f"✓ {path.name}", excluded_menu)
                action.setToolTip("Click to restore this wallpaper")
                action.triggered.connect(lambda checked, p=file_path: self.restore_wallpaper(p))
                excluded_menu.addAction(action)
            
            if len(excluded) > 10:
                excluded_menu.addSeparator()
                more_action = QAction(f"... and {len(excluded) - 10} more", excluded_menu)
                more_action.setEnabled(False)
                excluded_menu.addAction(more_action)
            
            if excluded:
                excluded_menu.addSeparator()
                clear_action = QAction("Restore All", excluded_menu)
                clear_action.triggered.connect(self.clear_excluded)
                excluded_menu.addAction(clear_action)
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_gallery()
    
    def show_gallery(self):
        """Show gallery window"""
        if not self.gallery_window:
            self.gallery_window = ModernGalleryWindow(self.config_manager, self.wallpaper_manager)
            self.gallery_window.wallpaper_selected.connect(self.on_wallpaper_selected)
        
        self.gallery_window.show()
        self.gallery_window.raise_()
        self.gallery_window.activateWindow()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = ModernSettingsDialog(self.config_manager, self.wallpaper_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update wallpaper list if directory changed
            self.wallpaper_manager.refresh_wallpaper_list()
            # Update auto-change timer
            self.update_auto_change_timer()
            self.update_auto_change_action()
    
    def show_session_stats(self):
        """Show session statistics dialog"""
        stats = self.wallpaper_manager.get_session_stats()
        
        mode_names = {
            'smart': 'Smart Random',
            'pure': 'Pure Random',
            'sequential': 'Sequential Shuffle'
        }
        
        message = (
            f"<h3>Session Statistics</h3>"
            f"<p><b>Random Mode:</b> {mode_names.get(stats['random_mode'], stats['random_mode'])}</p>"
            f"<p><b>Total Wallpapers:</b> {stats['total_wallpapers']}</p>"
            f"<p><b>Shown This Session:</b> {stats['session_shown']}</p>"
            f"<p><b>Not Yet Shown:</b> {stats['unused_wallpapers']}</p>"
            f"<p><b>Recently Avoided:</b> {stats['recent_avoided']}</p>"
            f"<p><b>Avoid Percentage:</b> {stats['avoid_percentage']}%</p>"
        )
        
        if stats['random_mode'] == 'sequential' and stats['unused_wallpapers'] == 0:
            message += "<p><i>All wallpapers shown! Will reshuffle on next change.</i></p>"
        elif stats['random_mode'] == 'smart' and stats['unused_wallpapers'] < 5:
            message += f"<p><i>Only {stats['unused_wallpapers']} new wallpapers left!</i></p>"
        
        QMessageBox.information(None, "Session Statistics", message)
    
    def reset_session_tracking(self):
        """Reset session tracking for fresh randomization"""
        reply = QMessageBox.question(
            None,
            "Reset Session Tracking",
            "This will reset the tracking of shown wallpapers.\n"
            "All wallpapers will be considered 'unshown' again.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.wallpaper_manager.reset_session_tracking()
            self.show_notification("Session tracking reset successfully")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            None,
            "About Wallpaper Changer",
            "<h3>Wallpaper Changer</h3>"
            "<p>A modern wallpaper manager for Quickshell/illogical-impulse.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>System tray integration</li>"
            "<li>Visual gallery with preview</li>"
            "<li>Automatic wallpaper changes</li>"
            "<li>Smart randomization modes</li>"
            "<li>Material Design color generation</li>"
            "<li>Thumbnail caching</li>"
            "</ul>"
            "<p>Version 2.1</p>"
        )
    
    def change_wallpaper_now(self):
        """Change to random wallpaper"""
        wallpaper = self.wallpaper_manager.random_wallpaper()
        if wallpaper:
            self.show_notification(f"Wallpaper changed to: {wallpaper.name}")
            self.last_change_time = QTimer().remainingTime()
            self.update_recent_menu_in_tray()
        else:
            self.show_notification("No wallpapers found")
    
    def next_wallpaper(self):
        """Change to next wallpaper"""
        wallpaper = self.wallpaper_manager.next_wallpaper()
        if wallpaper:
            self.show_notification(f"Wallpaper changed to: {wallpaper.name}")
            self.update_recent_menu_in_tray()
    
    def previous_wallpaper(self):
        """Change to previous wallpaper"""
        wallpaper = self.wallpaper_manager.previous_wallpaper()
        if wallpaper:
            self.show_notification(f"Wallpaper changed to: {wallpaper.name}")
            self.update_recent_menu_in_tray()
    
    def exclude_current_wallpaper(self):
        """Exclude current wallpaper from rotation"""
        current = self.wallpaper_manager.get_current_wallpaper()
        if current:
            if self.wallpaper_manager.exclude_current_wallpaper():
                self.show_notification(f"Excluded: {current.name}")
                # Change to next wallpaper after excluding
                self.next_wallpaper()
            else:
                self.show_notification("Failed to exclude wallpaper")
        else:
            self.show_notification("No wallpaper currently set")
    
    def set_wallpaper(self, wallpaper_path):
        """Set specific wallpaper"""
        if self.wallpaper_manager.set_wallpaper(wallpaper_path):
            self.show_notification(f"Wallpaper changed to: {wallpaper_path.name}")
            self.update_recent_menu_in_tray()
    
    def on_wallpaper_selected(self, wallpaper_path):
        """Handle wallpaper selection from gallery"""
        self.update_recent_menu_in_tray()
    
    def toggle_auto_change(self):
        """Toggle automatic wallpaper change"""
        enabled = self.auto_change_action.isChecked()
        self.config_manager.set('auto_change_enabled', enabled)
        self.update_auto_change_timer()
        self.update_auto_change_action()
        
        if enabled:
            self.show_notification("Automatic wallpaper change enabled")
        else:
            self.show_notification("Automatic wallpaper change disabled")
    
    def update_auto_change_action(self):
        """Update auto-change action text"""
        if self.config_manager.get('auto_change_enabled', False):
            self.auto_change_action.setText("⏸️ Disable Auto-Change")
        else:
            self.auto_change_action.setText("▶️ Enable Auto-Change")
    
    def update_auto_change_timer(self):
        """Update auto-change timer based on settings"""
        if self.config_manager.get('auto_change_enabled', False):
            interval = self.config_manager.get('change_interval', 30)
            self.auto_change_timer.start(interval * 60 * 1000)  # Convert to milliseconds
        else:
            self.auto_change_timer.stop()
    
    def auto_change_wallpaper(self):
        """Automatically change wallpaper"""
        wallpaper = self.wallpaper_manager.random_wallpaper()
        if wallpaper:
            self.show_notification(f"Wallpaper changed to: {wallpaper.name}")
            self.update_recent_menu_in_tray()
    
    def update_time_display(self):
        """Update time until next change display"""
        if not self.config_manager.get('auto_change_enabled', False):
            self.time_action.setText("Next change: Disabled")
            return
        
        remaining = self.auto_change_timer.remainingTime()
        if remaining > 0:
            minutes = remaining // 60000
            seconds = (remaining % 60000) // 1000
            
            if minutes > 0:
                self.time_action.setText(f"Next change: {minutes}m {seconds}s")
            else:
                self.time_action.setText(f"Next change: {seconds}s")
        else:
            self.time_action.setText("Next change: Any moment...")
    
    def update_recent_menu_in_tray(self):
        """Update the recent wallpapers menu in tray"""
        # Find the recent menu and update it
        for action in self.tray_menu.actions():
            if action.menu() and action.text() == "📜 Recent Wallpapers":
                self.update_recent_menu(action.menu())
                break
    
    def update_excluded_menu_in_tray(self):
        """Update the excluded wallpapers menu in tray"""
        # Find the excluded menu and update it
        for action in self.tray_menu.actions():
            if action.menu() and action.text() == "🚫 Excluded Wallpapers":
                self.update_excluded_menu(action.menu())
                break
    
    def restore_wallpaper(self, file_path: str):
        """Restore an excluded wallpaper"""
        self.config_manager.toggle_file_exclusion(file_path)
        self.wallpaper_manager.refresh_wallpaper_list()
        path = Path(file_path)
        self.show_notification(f"Restored: {path.name}")
        self.update_excluded_menu_in_tray()
    
    def clear_excluded(self):
        """Clear all excluded wallpapers"""
        self.wallpaper_manager.clear_excluded_files()
        self.update_excluded_menu_in_tray()
        self.show_notification("All wallpapers restored")
    
    def clear_history(self):
        """Clear wallpaper history"""
        self.config_manager.clear_history()
        self.update_recent_menu_in_tray()
        self.show_notification("Wallpaper history cleared")
    
    def show_notification(self, message):
        """Show system tray notification"""
        if self.config_manager.get('show_notifications', True):
            self.tray_icon.showMessage(
                "Wallpaper Changer",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
    
    def check_startup_actions(self):
        """Check for startup actions from environment variables"""
        if os.environ.get('WALLPAPER_CHANGER_OPEN_GALLERY'):
            QTimer.singleShot(100, self.show_gallery)
            del os.environ['WALLPAPER_CHANGER_OPEN_GALLERY']
        elif os.environ.get('WALLPAPER_CHANGER_OPEN_SETTINGS'):
            QTimer.singleShot(100, self.show_settings)
            del os.environ['WALLPAPER_CHANGER_OPEN_SETTINGS']
        elif os.environ.get('WALLPAPER_CHANGER_CHANGE_NOW'):
            QTimer.singleShot(100, self.change_wallpaper_now)
            del os.environ['WALLPAPER_CHANGER_CHANGE_NOW']
    
    def quit_app(self):
        """Quit the application"""
        # Save any pending configuration
        self.config_manager.save_config()
        
        # Close windows
        if self.gallery_window:
            self.gallery_window.close()
        
        # Quit application
        self.quit()


def main():
    """Main entry point"""
    try:
        # Setup logging
        log_dir = Path.home() / '.config' / 'wallpaper-changer' / 'logs'
        log_file = log_dir / 'wallpaper-changer.log'
        setup_logging(
            log_level=logging.INFO,
            log_file=str(log_file)
        )
        
        logger = logging.getLogger('Main')
        logger.info("Starting Wallpaper Changer application")
        
        # Enable high-DPI support before creating the app
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        # Create application first
        app = WallpaperChangerApp(sys.argv)
        app.setApplicationName("Wallpaper Changer")
        app.setApplicationDisplayName("Wallpaper Changer")
        
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray is not available on this system")
            sys.exit(1)
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()