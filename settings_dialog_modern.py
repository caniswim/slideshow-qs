#!/usr/bin/env python3
"""
Modern Settings Dialog - Premium UI/UX design
Consistent with gallery window design principles
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QPushButton, QSlider, QSpinBox,
    QCheckBox, QGroupBox, QGridLayout, QComboBox,
    QTimeEdit, QListWidget, QListWidgetItem, QFileDialog,
    QFrame, QScrollArea, QGraphicsDropShadowEffect,
    QSizePolicy, QDialogButtonBox, QButtonGroup,
    QRadioButton, QProgressBar, QTextEdit
)
from PyQt6.QtCore import (
    Qt, QTime, pyqtSignal, QPropertyAnimation, 
    QEasingCurve, QRect, pyqtProperty, QTimer,
    QParallelAnimationGroup, QSize
)
from PyQt6.QtGui import (
    QPalette, QGuiApplication, QFont, QIcon,
    QPainter, QColor, QLinearGradient, QPen,
    QBrush, QPixmap
)
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

# Import ThemeManager from gallery
try:
    from gallery_window_modern import ThemeManager
except ImportError:
    # Fallback ThemeManager if gallery not available
    class ThemeManager:
        @staticmethod
        def is_dark_mode():
            palette = QGuiApplication.palette()
            window_color = palette.color(QPalette.ColorRole.Window)
            luminance = (0.299 * window_color.red() + 
                        0.587 * window_color.green() + 
                        0.114 * window_color.blue())
            return luminance < 128
        
        @staticmethod
        def get_colors():
            if ThemeManager.is_dark_mode():
                return {
                    'background': '#000000',
                    'surface': '#121212',
                    'surface_variant': '#1e1e1e',
                    'card': '#1a1a1a',
                    'card_hover': '#252525',
                    'text_primary': '#ffffff',
                    'text_secondary': '#b0b0b0',
                    'text_disabled': '#606060',
                    'border': '#2a2a2a',
                    'primary': '#2196f3',
                    'secondary': '#4caf50',
                    'error': '#f44336',
                    'input_bg': '#1a1a1a',
                    'input_border': '#333333',
                }
            else:
                return {
                    'background': '#fafafa',
                    'surface': '#ffffff',
                    'surface_variant': '#f5f5f5',
                    'card': '#ffffff',
                    'card_hover': '#f8f8f8',
                    'text_primary': '#212121',
                    'text_secondary': '#666666',
                    'text_disabled': '#9e9e9e',
                    'border': '#e0e0e0',
                    'primary': '#2196f3',
                    'secondary': '#4caf50',
                    'error': '#f44336',
                    'input_bg': '#f5f5f5',
                    'input_border': '#e0e0e0',
                }


class ModernToggle(QFrame):
    """iOS-style animated toggle switch"""
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked = False
        self.animation = None
        self._position = 0
        self.colors = ThemeManager.get_colors()
        
        self.setFixedSize(50, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def isChecked(self):
        return self.checked
    
    def setChecked(self, checked):
        if self.checked != checked:
            self.checked = checked
            self.animate_toggle()
            self.toggled.emit(checked)
    
    @pyqtProperty(int)
    def position(self):
        return self._position
    
    @position.setter
    def position(self, value):
        self._position = value
        self.update()
    
    def animate_toggle(self):
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        if self.checked:
            self.animation.setEndValue(24)
        else:
            self.animation.setEndValue(0)
        
        self.animation.start()
    
    def mousePressEvent(self, event):
        self.setChecked(not self.checked)
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw track
        track_color = self.colors['primary'] if self.checked else self.colors['border']
        painter.setBrush(QBrush(QColor(track_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 50, 26, 13, 13)
        
        # Draw handle
        painter.setBrush(QBrush(QColor('#ffffff')))
        painter.drawEllipse(self._position + 2, 2, 22, 22)


class TimeRangeWidget(QWidget):
    """Widget for editing a time range"""
    changed = pyqtSignal()
    removed = pyqtSignal()
    
    def __init__(self, start_time="00:00", end_time="23:59", parent=None):
        super().__init__(parent)
        self.colors = ThemeManager.get_colors()
        self.setup_ui(start_time, end_time)
    
    def setup_ui(self, start_time, end_time):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Start time
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime.fromString(start_time, "HH:mm"))
        self.start_time.setStyleSheet(self.get_time_edit_style())
        self.start_time.timeChanged.connect(self.changed.emit)
        
        # To label
        to_label = QLabel("to")
        to_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        
        # End time
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(QTime.fromString(end_time, "HH:mm"))
        self.end_time.setStyleSheet(self.get_time_edit_style())
        self.end_time.timeChanged.connect(self.changed.emit)
        
        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['error']};
                color: white;
                border-radius: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #d32f2f;
            }}
        """)
        remove_btn.clicked.connect(self.removed.emit)
        
        layout.addWidget(self.start_time)
        layout.addWidget(to_label)
        layout.addWidget(self.end_time)
        layout.addWidget(remove_btn)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def get_time_edit_style(self):
        return f"""
            QTimeEdit {{
                background-color: {self.colors['input_bg']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {self.colors['text_primary']};
                font-size: 14px;
            }}
            QTimeEdit:focus {{
                border-color: {self.colors['primary']};
            }}
        """
    
    def get_time_range(self) -> Dict[str, str]:
        return {
            'start': self.start_time.time().toString("HH:mm"),
            'end': self.end_time.time().toString("HH:mm")
        }


class LuminosityCard(QFrame):
    """Card for luminosity category settings"""
    
    def __init__(self, category: str, icon: str, description: str, parent=None):
        super().__init__(parent)
        self.category = category
        self.icon = icon
        self.colors = ThemeManager.get_colors()
        self.time_ranges = []
        self.setup_ui(description)
    
    def setup_ui(self, description):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 8px;
                border: 1px solid {self.colors['border']};
            }}
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Icon and title
        title_layout = QHBoxLayout()
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet("font-size: 24px;")
        title_label = QLabel(self.category.capitalize())
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.colors['text_primary']};
        """)
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Enable toggle
        self.enable_toggle = ModernToggle()
        self.enable_toggle.setChecked(True)
        self.enable_toggle.toggled.connect(self.on_toggle_changed)
        
        header_layout.addLayout(title_layout)
        header_layout.addWidget(self.enable_toggle)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 12px;
            padding: 8px 0;
        """)
        layout.addWidget(desc_label)
        
        # Time ranges container
        self.ranges_container = QWidget()
        self.ranges_layout = QVBoxLayout()
        self.ranges_layout.setContentsMargins(0, 0, 0, 0)
        self.ranges_container.setLayout(self.ranges_layout)
        layout.addWidget(self.ranges_container)
        
        # Add time range button
        self.add_range_btn = QPushButton("+ Add Time Range")
        self.add_range_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors['secondary']};
            }}
        """)
        self.add_range_btn.clicked.connect(self.add_time_range)
        layout.addWidget(self.add_range_btn)
        
        self.setLayout(layout)
    
    def on_toggle_changed(self, checked):
        self.ranges_container.setEnabled(checked)
        self.add_range_btn.setEnabled(checked)
        
        # Update visual feedback
        opacity = "1.0" if checked else "0.5"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 8px;
                border: 1px solid {self.colors['border']};
                opacity: {opacity};
            }}
        """)
    
    def add_time_range(self, start="00:00", end="23:59"):
        time_range = TimeRangeWidget(start, end)
        time_range.removed.connect(lambda: self.remove_time_range(time_range))
        self.ranges_layout.addWidget(time_range)
        self.time_ranges.append(time_range)
    
    def remove_time_range(self, widget):
        self.ranges_layout.removeWidget(widget)
        widget.deleteLater()
        self.time_ranges.remove(widget)
    
    def load_schedule(self, schedule: Dict):
        """Load schedule data"""
        self.enable_toggle.setChecked(schedule.get('enabled', True))
        
        # Clear existing ranges
        for range_widget in self.time_ranges[:]:
            self.remove_time_range(range_widget)
        
        # Add ranges from schedule
        for time_range in schedule.get('time_ranges', []):
            self.add_time_range(time_range['start'], time_range['end'])
    
    def get_schedule(self) -> Dict:
        """Get current schedule configuration"""
        return {
            'enabled': self.enable_toggle.isChecked(),
            'time_ranges': [r.get_time_range() for r in self.time_ranges]
        }


class GeneralSettingsTab(QWidget):
    """General settings tab"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.colors = ThemeManager.get_colors()
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        # Main layout with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.colors['background']};
                border: none;
            }}
        """)
        
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Wallpaper Directory Card
        dir_card = self.create_card("Wallpaper Directory", [
            self.create_directory_selector()
        ])
        layout.addWidget(dir_card)
        
        # Auto-change Settings Card
        auto_card = self.create_card("Automatic Change", [
            self.create_auto_change_controls()
        ])
        layout.addWidget(auto_card)
        
        # Features Card
        features_card = self.create_card("Features", [
            self.create_feature_toggles()
        ])
        layout.addWidget(features_card)
        
        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def create_card(self, title: str, widgets: List[QWidget]) -> QFrame:
        """Create a styled card container"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 8px;
                border: 1px solid {self.colors['border']};
            }}
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {self.colors['text_primary']};
            padding-bottom: 12px;
        """)
        layout.addWidget(title_label)
        
        # Add widgets
        for widget in widgets:
            layout.addWidget(widget)
        
        card.setLayout(layout)
        return card
    
    def create_directory_selector(self) -> QWidget:
        """Create directory selector widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.dir_label = QLabel()
        self.dir_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.colors['input_bg']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                padding: 8px;
                color: {self.colors['text_primary']};
            }}
        """)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1976d2;
            }}
        """)
        browse_btn.clicked.connect(self.browse_directory)
        
        layout.addWidget(self.dir_label, 1)
        layout.addWidget(browse_btn)
        widget.setLayout(layout)
        return widget
    
    def create_auto_change_controls(self) -> QWidget:
        """Create auto-change controls"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Enable toggle
        toggle_layout = QHBoxLayout()
        label = QLabel("Enable automatic wallpaper change")
        label.setStyleSheet(f"color: {self.colors['text_primary']};")
        self.auto_change_toggle = ModernToggle()
        toggle_layout.addWidget(label)
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.auto_change_toggle)
        layout.addLayout(toggle_layout)
        
        # Interval slider
        interval_widget = QWidget()
        interval_layout = QVBoxLayout()
        
        self.interval_label = QLabel("Change interval: 30 minutes")
        self.interval_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            padding-top: 12px;
        """)
        interval_layout.addWidget(self.interval_label)
        
        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setMinimum(1)
        self.interval_slider.setMaximum(120)
        self.interval_slider.setValue(30)
        self.interval_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.interval_slider.setTickInterval(30)
        self.interval_slider.valueChanged.connect(self.on_interval_changed)
        self.interval_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {self.colors['border']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                background: {self.colors['primary']};
                border-radius: 8px;
                margin-top: -6px;
                margin-bottom: -6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.colors['primary']};
                border-radius: 2px;
            }}
        """)
        interval_layout.addWidget(self.interval_slider)
        
        interval_widget.setLayout(interval_layout)
        layout.addWidget(interval_widget)
        
        # Connect toggle to enable/disable interval
        self.auto_change_toggle.toggled.connect(interval_widget.setEnabled)
        
        widget.setLayout(layout)
        return widget
    
    def create_feature_toggles(self) -> QWidget:
        """Create feature toggle switches"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Shuffle
        self.shuffle_toggle = self.create_toggle_row(
            "Shuffle wallpapers",
            "Randomize wallpaper order"
        )
        layout.addWidget(self.shuffle_toggle['widget'])
        
        # Notifications
        self.notifications_toggle = self.create_toggle_row(
            "Show notifications",
            "Display notifications when wallpaper changes"
        )
        layout.addWidget(self.notifications_toggle['widget'])
        
        # Color sync
        self.color_sync_toggle = self.create_toggle_row(
            "Sync color scheme",
            "Generate Material Design colors from wallpaper (requires matugen)"
        )
        layout.addWidget(self.color_sync_toggle['widget'])
        
        widget.setLayout(layout)
        return widget
    
    def create_toggle_row(self, title: str, description: str) -> Dict:
        """Create a toggle row with title and description"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_primary']};
            font-size: 14px;
        """)
        text_layout.addWidget(title_label)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"""
                color: {self.colors['text_secondary']};
                font-size: 12px;
            """)
            text_layout.addWidget(desc_label)
        
        # Toggle
        toggle = ModernToggle()
        
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(toggle)
        
        widget.setLayout(layout)
        return {'widget': widget, 'toggle': toggle}
    
    def on_interval_changed(self, value):
        self.interval_label.setText(f"Change interval: {value} minutes")
    
    def browse_directory(self):
        current = self.config.get('wallpaper_directory', str(Path.home()))
        directory = QFileDialog.getExistingDirectory(
            self, "Select Wallpaper Directory", current
        )
        if directory:
            self.dir_label.setText(directory)
    
    def load_settings(self):
        self.dir_label.setText(self.config.get('wallpaper_directory', ''))
        self.auto_change_toggle.setChecked(self.config.get('auto_change_enabled', False))
        self.interval_slider.setValue(self.config.get('change_interval', 30))
        self.shuffle_toggle['toggle'].setChecked(self.config.get('shuffle', True))
        self.notifications_toggle['toggle'].setChecked(self.config.get('show_notifications', True))
        self.color_sync_toggle['toggle'].setChecked(self.config.get('sync_color_scheme', True))
    
    def save_settings(self):
        return {
            'wallpaper_directory': self.dir_label.text(),
            'auto_change_enabled': self.auto_change_toggle.isChecked(),
            'change_interval': self.interval_slider.value(),
            'shuffle': self.shuffle_toggle['toggle'].isChecked(),
            'show_notifications': self.notifications_toggle['toggle'].isChecked(),
            'sync_color_scheme': self.color_sync_toggle['toggle'].isChecked(),
        }


class RandomModeTab(QWidget):
    """Random mode settings tab"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.colors = ThemeManager.get_colors()
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Mode selection
        mode_group = QGroupBox("Random Mode Selection")
        mode_group.setStyleSheet(self.get_group_style())
        mode_layout = QVBoxLayout()
        
        # Radio buttons for modes
        self.mode_group = QButtonGroup()
        
        modes = [
            ("smart", "Smart Random", "Avoids recently shown wallpapers for variety"),
            ("pure", "Pure Random", "Completely random selection every time"),
            ("sequential", "Sequential Shuffle", "Shows all wallpapers before repeating")
        ]
        
        for i, (key, title, desc) in enumerate(modes):
            radio = QRadioButton(title)
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {self.colors['text_primary']};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px;
                }}
                QRadioButton::indicator {{
                    width: 20px;
                    height: 20px;
                }}
            """)
            self.mode_group.addButton(radio, i)
            mode_layout.addWidget(radio)
            
            # Description
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"""
                color: {self.colors['text_secondary']};
                font-size: 12px;
                padding-left: 28px;
                padding-bottom: 12px;
            """)
            mode_layout.addWidget(desc_label)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Smart mode settings
        self.smart_settings = QGroupBox("Smart Mode Settings")
        self.smart_settings.setStyleSheet(self.get_group_style())
        smart_layout = QVBoxLayout()
        
        self.avoid_label = QLabel("Avoid Recent: 25%")
        self.avoid_label.setStyleSheet(f"""
            color: {self.colors['text_primary']};
            font-size: 14px;
        """)
        smart_layout.addWidget(self.avoid_label)
        
        self.avoid_slider = QSlider(Qt.Orientation.Horizontal)
        self.avoid_slider.setMinimum(10)
        self.avoid_slider.setMaximum(50)
        self.avoid_slider.setValue(25)
        self.avoid_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.avoid_slider.setTickInterval(10)
        self.avoid_slider.valueChanged.connect(self.on_avoid_changed)
        self.avoid_slider.setStyleSheet(self.get_slider_style())
        smart_layout.addWidget(self.avoid_slider)
        
        desc = QLabel("Percentage of wallpapers to avoid repeating in Smart Random mode")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 12px;
            padding-top: 8px;
        """)
        smart_layout.addWidget(desc)
        
        self.smart_settings.setLayout(smart_layout)
        layout.addWidget(self.smart_settings)
        
        # Connect mode selection to enable/disable smart settings
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def get_group_style(self):
        return f"""
            QGroupBox {{
                background-color: {self.colors['card']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding-top: 16px;
                font-size: 16px;
                font-weight: bold;
                color: {self.colors['text_primary']};
            }}
            QGroupBox::title {{
                padding: 0 8px;
                color: {self.colors['text_primary']};
            }}
        """
    
    def get_slider_style(self):
        return f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {self.colors['border']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                background: {self.colors['primary']};
                border-radius: 8px;
                margin-top: -6px;
                margin-bottom: -6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.colors['primary']};
                border-radius: 2px;
            }}
        """
    
    def on_mode_changed(self, button):
        # Enable smart settings only for smart mode
        is_smart = self.mode_group.id(button) == 0
        self.smart_settings.setEnabled(is_smart)
    
    def on_avoid_changed(self, value):
        self.avoid_label.setText(f"Avoid Recent: {value}%")
    
    def load_settings(self):
        mode = self.config.get('random_mode', 'smart')
        mode_index = {'smart': 0, 'pure': 1, 'sequential': 2}.get(mode, 0)
        self.mode_group.button(mode_index).setChecked(True)
        
        avoid = self.config.get('avoid_recent_percentage', 25)
        self.avoid_slider.setValue(avoid)
        
        # Enable/disable smart settings
        self.smart_settings.setEnabled(mode_index == 0)
    
    def save_settings(self):
        mode_map = {0: 'smart', 1: 'pure', 2: 'sequential'}
        mode_id = self.mode_group.checkedId()
        
        return {
            'random_mode': mode_map.get(mode_id, 'smart'),
            'avoid_recent_percentage': self.avoid_slider.value()
        }


class TimeBasedTab(QWidget):
    """Time-based selection settings tab"""
    
    def __init__(self, config_manager, wallpaper_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.wallpaper_manager = wallpaper_manager
        self.colors = ThemeManager.get_colors()
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.colors['background']};
                border: none;
            }}
        """)
        
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Enable toggle
        enable_layout = QHBoxLayout()
        enable_label = QLabel("Enable Time-Based Selection")
        enable_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {self.colors['text_primary']};
        """)
        self.time_based_toggle = ModernToggle()
        self.time_based_toggle.toggled.connect(self.on_time_based_toggled)
        
        enable_layout.addWidget(enable_label)
        enable_layout.addStretch()
        enable_layout.addWidget(self.time_based_toggle)
        layout.addLayout(enable_layout)
        
        # Description
        desc = QLabel(
            "Automatically select wallpapers based on their luminosity and the time of day. "
            "Dark wallpapers for night, light wallpapers for day, and medium for transitions."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 12px;
            padding-bottom: 12px;
        """)
        layout.addWidget(desc)
        
        # Container for luminosity cards
        self.cards_container = QWidget()
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(16)
        
        # Create luminosity cards
        self.dark_card = LuminosityCard(
            "dark", "🌙", 
            "Dark wallpapers for nighttime (low luminosity < 0.18)"
        )
        cards_layout.addWidget(self.dark_card)
        
        self.medium_card = LuminosityCard(
            "medium", "◐",
            "Medium wallpapers for transitions (0.18 ≤ luminosity ≤ 0.36)"
        )
        cards_layout.addWidget(self.medium_card)
        
        self.light_card = LuminosityCard(
            "light", "☀",
            "Light wallpapers for daytime (luminosity > 0.36)"
        )
        cards_layout.addWidget(self.light_card)
        
        self.cards_container.setLayout(cards_layout)
        layout.addWidget(self.cards_container)
        
        # Statistics
        if self.wallpaper_manager:
            stats_card = self.create_statistics_card()
            layout.addWidget(stats_card)
        
        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def create_statistics_card(self) -> QFrame:
        """Create statistics card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 8px;
                border: 1px solid {self.colors['border']};
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        title = QLabel("Wallpaper Statistics")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {self.colors['text_primary']};
        """)
        layout.addWidget(title)
        
        # Get statistics
        stats = self.wallpaper_manager.get_metadata_statistics()
        
        if stats and stats['total'] > 0:
            total = stats['total']
            dark = stats['classifications']['dark']
            medium = stats['classifications']['medium']
            light = stats['classifications']['light']
            
            stats_text = f"""
            Total wallpapers analyzed: {total}
            Dark: {dark} ({dark/total*100:.1f}%)
            Medium: {medium} ({medium/total*100:.1f}%)
            Light: {light} ({light/total*100:.1f}%)
            """
        else:
            stats_text = """
            No wallpapers analyzed yet.
            Run 'python3 fast_analyze.py' to analyze your wallpapers.
            """
        
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 12px;
            padding: 8px 0;
        """)
        layout.addWidget(stats_label)
        
        card.setLayout(layout)
        return card
    
    def on_time_based_toggled(self, checked):
        self.cards_container.setEnabled(checked)
    
    def load_settings(self):
        # Load time-based enabled state
        self.time_based_toggle.setChecked(
            self.config.get('time_based_enabled', False)
        )
        
        # Load schedules from metadata manager if available
        if self.wallpaper_manager:
            schedules = self.wallpaper_manager.metadata_manager.time_schedules
            
            self.dark_card.load_schedule(schedules.get('dark', {}))
            self.medium_card.load_schedule(schedules.get('medium', {}))
            self.light_card.load_schedule(schedules.get('light', {}))
        else:
            # Load defaults
            self.dark_card.add_time_range("20:00", "06:00")
            self.medium_card.add_time_range("06:00", "09:00")
            self.medium_card.add_time_range("17:00", "20:00")
            self.light_card.add_time_range("09:00", "17:00")
    
    def save_settings(self):
        settings = {
            'time_based_enabled': self.time_based_toggle.isChecked()
        }
        
        # Save schedules if wallpaper manager available
        if self.wallpaper_manager:
            metadata = self.wallpaper_manager.metadata_manager
            
            # Update each schedule
            for card, category in [
                (self.dark_card, 'dark'),
                (self.medium_card, 'medium'),
                (self.light_card, 'light')
            ]:
                schedule = card.get_schedule()
                metadata.time_schedules[category] = schedule
            
            # Save to file
            metadata.save_time_schedules()
        
        return settings


class ModernSettingsDialog(QDialog):
    """Modern settings dialog with tabs and premium UI"""
    
    def __init__(self, config_manager, wallpaper_manager=None, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.wallpaper_manager = wallpaper_manager
        self.colors = ThemeManager.get_colors()
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self.get_tab_style())
        
        # Create tabs
        self.general_tab = GeneralSettingsTab(self.config)
        self.random_tab = RandomModeTab(self.config)
        self.time_tab = TimeBasedTab(self.config, self.wallpaper_manager)
        
        # Add tabs
        self.tabs.addTab(self.general_tab, "⚙️ General")
        self.tabs.addTab(self.random_tab, "🎲 Random Mode")
        self.tabs.addTab(self.time_tab, "🕐 Time-Based")
        
        layout.addWidget(self.tabs)
        
        # Button bar
        button_bar = QFrame()
        button_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['surface']};
                border-top: 1px solid {self.colors['border']};
            }}
        """)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 12, 20, 12)
        
        # Analyze button
        analyze_btn = QPushButton("🔍 Analyze Wallpapers")
        analyze_btn.setToolTip("Run wallpaper luminosity analysis")
        analyze_btn.setStyleSheet(self.get_button_style(secondary=True))
        analyze_btn.clicked.connect(self.run_analysis)
        button_layout.addWidget(analyze_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self.get_button_style())
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Save button
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(self.get_button_style(primary=True))
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        button_bar.setLayout(button_layout)
        layout.addWidget(button_bar)
        
        self.setLayout(layout)
    
    def get_tab_style(self):
        return f"""
            QTabWidget::pane {{
                background-color: {self.colors['background']};
                border: none;
            }}
            QTabBar::tab {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_secondary']};
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colors['primary']};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {self.colors['card_hover']};
            }}
        """
    
    def get_button_style(self, primary=False, secondary=False):
        if primary:
            bg = self.colors['primary']
            hover = '#1976d2'
            text = 'white'
        elif secondary:
            bg = self.colors['secondary']
            hover = '#45a049'
            text = 'white'
        else:
            bg = self.colors['surface_variant']
            hover = self.colors['card_hover']
            text = self.colors['text_primary']
        
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """
    
    def apply_theme(self):
        """Apply dark/light theme to dialog"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['background']};
            }}
        """)
    
    def save_settings(self):
        """Save all settings and close"""
        settings = {}
        
        # Collect settings from all tabs
        settings.update(self.general_tab.save_settings())
        settings.update(self.random_tab.save_settings())
        settings.update(self.time_tab.save_settings())
        
        # Save to config
        self.config.update(settings)
        
        self.accept()
    
    def run_analysis(self):
        """Run wallpaper analysis script"""
        import subprocess
        from pathlib import Path
        
        script = Path(__file__).parent / 'fast_analyze.py'
        if script.exists():
            try:
                subprocess.Popen(['python3', str(script)])
                
                # Show notification
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setWindowTitle("Analysis Started")
                msg.setText("Wallpaper analysis started in background.\nCheck terminal for progress.")
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setWindowTitle("Error")
                msg.setText(f"Failed to start analysis: {e}")
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.exec()