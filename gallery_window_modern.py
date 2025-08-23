#!/usr/bin/env python3
"""
Modern Gallery Window - Redesigned for better UX/UI
Focused on elegant thumbnail grid display
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QLineEdit,
    QComboBox, QGridLayout, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QStatusBar, QMenu, QApplication,
    QStyle, QStyleOption, QDialog, QCheckBox, QButtonGroup,
    QStyleFactory, QLayout, QLayoutItem
)
from PyQt6.QtCore import (
    Qt, QSize, pyqtSignal, QThread, QTimer, QRunnable,
    QPropertyAnimation, QEasingCurve, QRect, QPoint,
    QParallelAnimationGroup, QSequentialAnimationGroup,
    pyqtProperty, QThreadPool, pyqtSlot, QObject
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QAction, QPainter, QBrush,
    QColor, QPalette, QLinearGradient, QCursor,
    QFont, QPainterPath, QRegion, QGuiApplication,
    QImage, QPixmapCache
)
from pathlib import Path
from typing import Optional, List, Dict
import random
from datetime import datetime
import hashlib
import os


class FlowLayout(QLayout):
    """A flow layout that wraps widgets to next row when space runs out"""
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.item_list = []

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()

        for item in self.item_list:
            widget = item.widget()
            if widget and not widget.isVisible():
                continue
                
            spaceX = spacing
            spaceY = spacing
            nextX = x + item.sizeHint().width() + spaceX
            
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class ThemeManager:
    """Manages dark and light theme colors"""
    
    @staticmethod
    def is_dark_mode():
        """Detect if system is in dark mode"""
        palette = QGuiApplication.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        # Consider dark if background luminance is low
        luminance = (0.299 * window_color.red() + 
                    0.587 * window_color.green() + 
                    0.114 * window_color.blue())
        return luminance < 128
    
    @staticmethod
    def get_colors():
        """Get theme colors based on current mode"""
        if ThemeManager.is_dark_mode():
            return {
                # OLED-friendly pure black backgrounds
                'background': '#000000',
                'surface': '#121212',
                'surface_variant': '#1e1e1e',
                'card': '#1a1a1a',
                'card_hover': '#252525',
                
                # Text colors
                'text_primary': '#ffffff',
                'text_secondary': '#b0b0b0',
                'text_disabled': '#606060',
                
                # Borders and dividers
                'border': '#2a2a2a',
                'border_hover': '#404040',
                'divider': '#1e1e1e',
                
                # Accent colors
                'primary': '#2196f3',
                'primary_variant': '#1976d2',
                'secondary': '#4caf50',
                'error': '#f44336',
                
                # Input fields
                'input_bg': '#1a1a1a',
                'input_border': '#333333',
                'input_hover': '#404040',
                
                # Selection and highlights
                'selection': '#1e3a5f',
                'selection_border': '#2196f3',
                
                # Shadows (subtle in dark mode)
                'shadow': 'rgba(0, 0, 0, 0.8)',
                'shadow_hover': 'rgba(33, 150, 243, 0.3)',
                
                # Loading placeholder
                'loading_bg': '#1a1a1a',
                'loading_fg': '#2a2a2a',
            }
        else:
            return {
                # Light mode colors
                'background': '#fafafa',
                'surface': '#ffffff',
                'surface_variant': '#f5f5f5',
                'card': '#ffffff',
                'card_hover': '#f8f8f8',
                
                # Text colors
                'text_primary': '#212121',
                'text_secondary': '#666666',
                'text_disabled': '#9e9e9e',
                
                # Borders and dividers
                'border': '#e0e0e0',
                'border_hover': '#cccccc',
                'divider': '#e0e0e0',
                
                # Accent colors
                'primary': '#2196f3',
                'primary_variant': '#1976d2',
                'secondary': '#4caf50',
                'error': '#f44336',
                
                # Input fields
                'input_bg': '#f5f5f5',
                'input_border': '#e0e0e0',
                'input_hover': '#cccccc',
                
                # Selection and highlights
                'selection': '#e3f2fd',
                'selection_border': '#2196f3',
                
                # Shadows
                'shadow': 'rgba(0, 0, 0, 0.15)',
                'shadow_hover': 'rgba(33, 150, 243, 0.25)',
                
                # Loading placeholder
                'loading_bg': '#f0f0f0',
                'loading_fg': '#e0e0e0',
            }


class ThumbnailCache:
    """Persistent thumbnail cache for fast loading"""
    
    def __init__(self):
        self.cache_dir = Path.home() / '.cache' / 'wallpaper-thumbnails'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Set QPixmapCache to 50MB
        QPixmapCache.setCacheLimit(50 * 1024)
    
    def get_cache_path(self, image_path: Path, size: int, quality: str = 'fast') -> Path:
        """Get cache file path"""
        mtime = image_path.stat().st_mtime if image_path.exists() else 0
        hash_str = f"{image_path}_{size}_{quality}_{mtime}"
        file_hash = hashlib.md5(hash_str.encode()).hexdigest()
        ext = 'jpg' if quality == 'fast' else 'png'
        return self.cache_dir / f"{file_hash}.{ext}"
    
    def get_cached(self, image_path: Path, size: int, quality: str = 'fast') -> Optional[QPixmap]:
        """Get from cache if exists"""
        cache_key = f"{image_path}_{size}_{quality}"
        
        # Check QPixmapCache first
        pixmap = QPixmapCache.find(cache_key)
        if pixmap and not pixmap.isNull():
            return pixmap
        
        # Check disk cache
        cache_path = self.get_cache_path(image_path, size, quality)
        if cache_path.exists():
            pixmap = QPixmap(str(cache_path))
            if not pixmap.isNull():
                QPixmapCache.insert(cache_key, pixmap)
                return pixmap
        return None
    
    def save(self, image_path: Path, pixmap: QPixmap, size: int, quality: str = 'fast'):
        """Save to cache"""
        cache_key = f"{image_path}_{size}_{quality}"
        cache_path = self.get_cache_path(image_path, size, quality)
        
        # Save with appropriate quality
        if quality == 'fast':
            pixmap.save(str(cache_path), 'JPEG', 75)
        else:
            pixmap.save(str(cache_path), 'PNG', 95)
        
        # Add to memory cache
        QPixmapCache.insert(cache_key, pixmap)


class ThumbnailWorkerSignals(QObject):
    """Signals for thumbnail worker"""
    finished = pyqtSignal(Path, QPixmap, str)
    error = pyqtSignal(Path, str)


class ThumbnailWorker(QRunnable):
    """Worker for parallel thumbnail loading"""
    
    def __init__(self, image_path: Path, size: int, quality: str, cache: ThumbnailCache):
        super().__init__()
        self.image_path = image_path
        self.size = size
        self.quality = quality
        self.cache = cache
        self.signals = ThumbnailWorkerSignals()
    
    @pyqtSlot()
    def run(self):
        """Load thumbnail in background"""
        try:
            # Check cache first
            pixmap = self.cache.get_cached(self.image_path, self.size, self.quality)
            if pixmap:
                self.signals.finished.emit(self.image_path, pixmap, self.quality)
                return
            
            # Load image
            image = QImage(str(self.image_path))
            if image.isNull():
                self.signals.error.emit(self.image_path, "Failed to load")
                return
            
            # Always use SmoothTransformation for quality
            scaled = image.scaled(self.size, self.size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            pixmap = QPixmap.fromImage(scaled)
            self.cache.save(self.image_path, pixmap, self.size, self.quality)
            self.signals.finished.emit(self.image_path, pixmap, self.quality)
            
        except Exception as e:
            self.signals.error.emit(self.image_path, str(e))


class ThumbnailLoader(QThread):
    """Optimized thumbnail loader with parallel processing"""
    thumbnail_ready = pyqtSignal(Path, QPixmap, str)
    progress_update = pyqtSignal(int, int)
    all_loaded = pyqtSignal()
    
    def __init__(self, wallpaper_manager):
        super().__init__()
        self.wallpaper_manager = wallpaper_manager
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(6)  # Use 6 threads
        self.cache = ThumbnailCache()
        self.tasks = []
        self.running = True
    
    def add_task(self, image_path: Path, size: int = 200, quality: str = 'fast', priority: bool = False):
        """Add loading task with priority support"""
        task = (image_path, size, quality)
        if priority:
            self.tasks.insert(0, task)
        else:
            self.tasks.append(task)
    
    def load_batch(self, images: List[Path], size: int):
        """Load batch of images"""
        self.tasks.clear()
        
        # Queue all images
        for img in images:
            self.tasks.append((img, size, 'hd'))
        
        # Start processing
        self.process_tasks()
    
    def process_tasks(self):
        """Process tasks using thread pool"""
        total = len(self.tasks)
        processed = 0
        
        for task in self.tasks:
            if not self.running:
                break
                
            image_path, size, quality = task
            
            # Create worker
            worker = ThumbnailWorker(image_path, size, quality, self.cache)
            worker.signals.finished.connect(self.on_worker_finished)
            worker.signals.error.connect(self.on_worker_error)
            
            # Start worker
            self.thread_pool.start(worker)
            
            processed += 1
            self.progress_update.emit(processed, total)
    
    def on_worker_finished(self, image_path: Path, pixmap: QPixmap, quality: str):
        """Handle worker completion"""
        self.thumbnail_ready.emit(image_path, pixmap, quality)
    
    def on_worker_error(self, image_path: Path, error: str):
        """Handle worker error"""
        pass  # Silently ignore errors
    
    def run(self):
        """Thread main loop"""
        while self.running:
            self.msleep(100)  # Keep thread alive
    
    def stop(self):
        """Stop the thread and pool"""
        self.running = False
        self.thread_pool.waitForDone(2000)
        self.tasks.clear()


class ModernThumbnailCard(QFrame):
    """Modern card-style thumbnail widget with Material Design"""
    clicked = pyqtSignal(Path)
    double_clicked = pyqtSignal(Path)
    right_clicked = pyqtSignal(Path, QPoint)
    
    def __init__(self, image_path: Path, size: int = 200):
        super().__init__()
        self.image_path = image_path
        self.size = size
        self.selected = False
        self.hovered = False
        self.is_current = False
        self.is_favorite = False
        self.is_excluded = False
        self.pixmap = None
        self.colors = ThemeManager.get_colors()
        self.preview_loaded = False
        self.hd_loaded = False
        
        self.setup_ui()
        self.setup_animations()
        self.apply_card_style()
    
    def setup_ui(self):
        """Setup the card UI"""
        # Card size with padding for shadow
        self.setFixedSize(self.size + 20, self.size + 60)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Container for image with rounded corners
        self.image_container = QFrame()
        self.image_container.setFixedSize(self.size, self.size)
        self.image_container.setStyleSheet(f"""
            QFrame {{
                border-radius: 8px;
                background-color: {self.colors['surface_variant']};
            }}
        """)
        
        # Thumbnail label
        self.thumb_label = QLabel(self.image_container)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setFixedSize(self.size, self.size)
        self.thumb_label.setScaledContents(True)
        self.thumb_label.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: transparent;
            }
        """)
        
        # Loading placeholder
        self.set_loading_state()
        
        layout.addWidget(self.image_container)
        
        # Title container
        title_container = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)
        
        # Status indicators
        self.status_indicators = QLabel()
        self.update_status_indicators()
        title_layout.addWidget(self.status_indicators)
        
        # Filename label
        self.name_label = QLabel(self.image_path.stem[:20])
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPointSize(9)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        title_layout.addWidget(self.name_label, 1)
        
        title_container.setLayout(title_layout)
        layout.addWidget(title_container)
        
        self.setLayout(layout)
    
    def setup_animations(self):
        """Setup hover and selection animations"""
        # Initialize scale value
        self._scale = 1.0
        
        # Shadow animation (subtle in dark mode)
        self.shadow_effect = QGraphicsDropShadowEffect()
        if ThemeManager.is_dark_mode():
            self.shadow_effect.setColor(QColor(0, 0, 0, 30))  # Very subtle in dark mode
            self.shadow_effect.setBlurRadius(10)
        else:
            self.shadow_effect.setColor(QColor(0, 0, 0, 60))
            self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow_effect)
    
    def apply_card_style(self):
        """Apply modern card styling with theme support"""
        if self.selected:
            style = f"""
                ModernThumbnailCard {{
                    background-color: {self.colors['selection']};
                    border-radius: 12px;
                    border: 2px solid {self.colors['selection_border']};
                }}
            """
        elif self.is_current:
            style = f"""
                ModernThumbnailCard {{
                    background-color: {self.colors['card']};
                    border-radius: 12px;
                    border: 2px solid {self.colors['secondary']};
                }}
            """
        else:
            style = f"""
                ModernThumbnailCard {{
                    background-color: {self.colors['card']};
                    border-radius: 12px;
                    border: 2px solid transparent;
                }}
            """
        
        self.setStyleSheet(style)
    
    def set_loading_state(self):
        """Show ultra-light placeholder for performance"""
        placeholder = QPixmap(self.size, self.size)
        placeholder.fill(QColor(self.colors['surface_variant']))
        self.thumb_label.setPixmap(placeholder)
    
    def set_thumbnail(self, pixmap: QPixmap, quality: str = 'fast'):
        """Set thumbnail with quality level"""
        self.pixmap = pixmap
        self.thumb_label.setPixmap(pixmap)
        self.thumb_label.setScaledContents(True)
        
        if quality == 'fast':
            self.preview_loaded = True
        else:
            self.hd_loaded = True
    
    def set_selected(self, selected: bool):
        """Set selection state with animation"""
        self.selected = selected
        self.apply_card_style()
        
        if selected:
            if ThemeManager.is_dark_mode():
                self.shadow_effect.setBlurRadius(15)
                self.shadow_effect.setColor(QColor(33, 150, 243, 50))
            else:
                self.shadow_effect.setBlurRadius(20)
                self.shadow_effect.setColor(QColor(33, 150, 243, 100))
        else:
            if ThemeManager.is_dark_mode():
                self.shadow_effect.setBlurRadius(10)
                self.shadow_effect.setColor(QColor(0, 0, 0, 30))
            else:
                self.shadow_effect.setBlurRadius(15)
                self.shadow_effect.setColor(QColor(0, 0, 0, 60))
    
    def set_current(self, is_current: bool):
        """Mark as current wallpaper"""
        self.is_current = is_current
        self.update_status_indicators()
        self.apply_card_style()
    
    def set_favorite(self, is_favorite: bool):
        """Mark as favorite"""
        self.is_favorite = is_favorite
        self.update_status_indicators()
    
    def set_excluded(self, is_excluded: bool):
        """Mark as excluded"""
        self.is_excluded = is_excluded
        self.update_status_indicators()
        
        if is_excluded:
            self.setEnabled(False)
            self.setStyleSheet(f"""
                ModernThumbnailCard {{
                    background-color: {self.colors['surface_variant']};
                    border-radius: 12px;
                    border: 2px solid {self.colors['border']};
                    opacity: 0.5;
                }}
            """)
        else:
            self.setEnabled(True)
            self.apply_card_style()
    
    def update_status_indicators(self):
        """Update status indicator icons"""
        indicators = []
        
        if self.is_current:
            indicators.append("✓")
        if self.is_favorite:
            indicators.append("★")
        if self.is_excluded:
            indicators.append("⊘")
        
        self.status_indicators.setText(" ".join(indicators))
        
        if indicators:
            self.status_indicators.setStyleSheet(f"""
                QLabel {{
                    color: {self.colors['primary']};
                    font-size: 14px;
                    font-weight: bold;
                }}
            """)
        else:
            self.status_indicators.setText("")
    
    def enterEvent(self, event):
        """Handle mouse enter with HD loading and animation"""
        self.hovered = True
        if ThemeManager.is_dark_mode():
            self.shadow_effect.setBlurRadius(15)
        else:
            self.shadow_effect.setBlurRadius(25)
        self.shadow_effect.setOffset(0, 4)
        self.raise_()  # Bring to front
        
        # Request HD on hover if preview is loaded
        if self.preview_loaded and not self.hd_loaded:
            gallery = self.window()
            if hasattr(gallery, 'request_hd_thumbnail'):
                gallery.request_hd_thumbnail(self.image_path)
    
    def leaveEvent(self, event):
        """Handle mouse leave with animation"""
        self.hovered = False
        if not self.selected:
            if ThemeManager.is_dark_mode():
                self.shadow_effect.setBlurRadius(10)
            else:
                self.shadow_effect.setBlurRadius(15)
            self.shadow_effect.setOffset(0, 2)
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_path)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.image_path, event.globalPosition().toPoint())
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.image_path)
    
    # Animation property
    def get_scale(self):
        return self._scale
    
    def set_scale(self, value):
        self._scale = value
    
    scale = pyqtProperty(float, get_scale, set_scale)


# Preview Dialog removed - double click now applies wallpaper directly
'''
class PreviewDialog(QDialog):
    # Modern preview dialog with fullscreen support
    wallpaper_applied = pyqtSignal(Path)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = None
        self.colors = ThemeManager.get_colors()
        self.setup_ui()
    
    def setup_ui(self):
        # Setup preview dialog UI
        self.setWindowTitle("Wallpaper Preview")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        
        # Remove window frame for cleaner look
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.FramelessWindowHint
        )
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header bar
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['primary']};
                border: none;
            }}
        """)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("Wallpaper Preview")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Action buttons
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedSize(30, 30)
        self.fullscreen_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 20px;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        header_layout.addWidget(self.fullscreen_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 20px;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        header.setLayout(header_layout)
        layout.addWidget(header)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.colors['background']};
            }}
        """)
        self.image_label.setScaledContents(False)
        layout.addWidget(self.image_label, 1)
        
        # Info bar
        info_bar = QFrame()
        info_bar.setFixedHeight(60)
        info_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['surface']};
                border-top: 1px solid {self.colors['divider']};
            }}
        """)
        
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(15, 10, 15, 10)
        
        self.info_label = QLabel()
        self.info_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        
        # Apply button
        apply_btn = QPushButton("Apply Wallpaper")
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
        """)
        apply_btn.clicked.connect(self.apply_wallpaper)
        info_layout.addWidget(apply_btn)
        
        info_bar.setLayout(info_layout)
        layout.addWidget(info_bar)
        
        self.setLayout(layout)
    
    def show_preview(self, image_path: Path, image_info: dict):
        """Show wallpaper preview"""
        self.current_path = image_path
        
        # Load and display image
        pixmap = QPixmap(str(image_path))
        
        # Scale to fit
        display_size = self.image_label.size()
        scaled = pixmap.scaled(
            display_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        
        # Update info
        info_text = (
            f"<b>{image_info['name']}</b> | "
            f"{image_info['dimensions'][0]}x{image_info['dimensions'][1]} | "
            f"{image_info['size'] / 1024 / 1024:.1f} MB"
        )
        self.info_label.setText(info_text)
        
        self.show()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("⛶")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("⛷")
    
    def apply_wallpaper(self):
        """Apply the wallpaper"""
        if self.current_path:
            self.wallpaper_applied.emit(self.current_path)
            self.close()
    
    def keyPressEvent(self, event):
        """Handle key press"""
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.close()
        elif event.key() == Qt.Key.Key_Return:
            self.apply_wallpaper()
'''


class FilterPanel(QFrame):
    """Modern filter panel with Material Design"""
    filters_changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.colors = ThemeManager.get_colors()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup filter panel UI"""
        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['surface']};
                border-bottom: 1px solid {self.colors['divider']};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)
        
        # Search input with icon
        search_container = QFrame()
        search_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['input_bg']};
                border-radius: 20px;
                border: 1px solid {self.colors['input_border']};
            }}
        """)
        search_container.setFixedHeight(40)
        
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(15, 0, 15, 0)
        search_layout.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search wallpapers...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: {self.colors['text_primary']};
            }}
        """)
        self.search_input.textChanged.connect(self.on_filters_changed)
        search_layout.addWidget(self.search_input)
        
        search_container.setLayout(search_layout)
        layout.addWidget(search_container, 2)
        
        # Sort dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Date", "Random", "Size"])
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colors['input_bg']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                color: {self.colors['text_primary']};
            }}
            QComboBox:hover {{
                border-color: {self.colors['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.sort_combo.currentTextChanged.connect(self.on_filters_changed)
        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        layout.addWidget(sort_label)
        layout.addWidget(self.sort_combo)
        
        # View size slider
        size_label = QLabel("Size:")
        size_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        layout.addWidget(size_label)
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Small", "Medium", "Large", "Extra Large"])
        self.size_combo.setCurrentText("Medium")
        self.size_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colors['input_bg']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                color: {self.colors['text_primary']};
            }}
        """)
        self.size_combo.currentTextChanged.connect(self.on_filters_changed)
        layout.addWidget(self.size_combo)
        
        layout.addStretch()
        
        # Filter toggles
        self.show_excluded = QCheckBox("Show Excluded")
        self.show_excluded.setStyleSheet(f"""
            QCheckBox {{
                font-size: 14px;
                color: {self.colors['text_secondary']};
            }}
        """)
        self.show_excluded.toggled.connect(self.on_filters_changed)
        layout.addWidget(self.show_excluded)
        
        # Statistics
        self.stats_label = QLabel("0 wallpapers")
        self.stats_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_secondary']};
                font-size: 14px;
            }}
        """)
        layout.addWidget(self.stats_label)
        
        self.setLayout(layout)
    
    def on_filters_changed(self):
        """Emit filter changes"""
        filters = {
            'search': self.search_input.text(),
            'sort': self.sort_combo.currentText(),
            'size': self.size_combo.currentText(),
            'show_excluded': self.show_excluded.isChecked()
        }
        self.filters_changed.emit(filters)
    
    def update_stats(self, total: int, visible: int):
        """Update statistics display"""
        if total == visible:
            self.stats_label.setText(f"{total} wallpapers")
        else:
            self.stats_label.setText(f"{visible} of {total} wallpapers")


class ModernGalleryWindow(QMainWindow):
    """Redesigned gallery window with modern UX/UI"""
    
    wallpaper_selected = pyqtSignal(Path)
    
    def __init__(self, config_manager, wallpaper_manager):
        super().__init__()
        self.config = config_manager
        self.wallpaper_manager = wallpaper_manager
        self.thumbnail_cards: Dict[Path, ModernThumbnailCard] = {}
        self.selected_path = None
        self.current_wallpaper = None
        self.colors = ThemeManager.get_colors()
        
        self.setup_ui()
        self.restore_geometry()
        
        # Start optimized thumbnail loader
        self.thumb_loader = ThumbnailLoader(self.wallpaper_manager)
        self.thumb_loader.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumb_loader.progress_update.connect(self.on_loading_progress)
        self.thumb_loader.all_loaded.connect(self.on_all_images_loaded)
        self.thumb_loader.start()
        
        # Queue for HD loading
        self.hd_queue = []
        self.hd_timer = QTimer()
        self.hd_timer.timeout.connect(self.process_hd_queue)
        self.hd_timer.setInterval(50)
        
        # Load wallpapers immediately - no lazy loading
        self.load_wallpapers()
        
        # Monitor theme changes (optional - refresh on palette change)
        app = QApplication.instance()
        if app:
            app.paletteChanged.connect(self.on_theme_changed)
    
    def setup_ui(self):
        """Setup the modern UI"""
        self.setWindowTitle("Wallpaper Gallery")
        self.setMinimumSize(1200, 800)
        
        # Apply modern window style with theme support
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['background']};
            }}
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Filter panel
        self.filter_panel = FilterPanel()
        self.filter_panel.filters_changed.connect(self.apply_filters)
        main_layout.addWidget(self.filter_panel)
        
        # Scrollable grid area
        self.create_grid_area()
        main_layout.addWidget(self.scroll_area, 1)
        
        # Bottom action bar
        self.create_action_bar()
        main_layout.addWidget(self.action_bar)
        
        central_widget.setLayout(main_layout)
        
        # No preview dialog - double click applies wallpaper directly
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {self.colors['surface']};
                border-top: 1px solid {self.colors['divider']};
                color: {self.colors['text_secondary']};
            }}
        """)
    
    def create_grid_area(self):
        """Create responsive scrollable grid"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {self.colors['background']};
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['surface_variant']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.colors['border_hover']};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['text_disabled']};
            }}
        """)
        
        # Use Flow Layout for responsive grid
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet(f"background-color: {self.colors['background']};")
        self.flow_layout = FlowLayout(margin=20, spacing=20)
        self.grid_widget.setLayout(self.flow_layout)
        
        self.scroll_area.setWidget(self.grid_widget)
    
    def create_action_bar(self):
        """Create bottom action bar"""
        self.action_bar = QFrame()
        self.action_bar.setFixedHeight(60)
        self.action_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['surface']};
                border-top: 1px solid {self.colors['divider']};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)
        
        # Quick actions
        random_btn = QPushButton("🎲 Random")
        random_btn.setStyleSheet(self.get_button_style())
        random_btn.clicked.connect(self.select_random)
        layout.addWidget(random_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style())
        refresh_btn.clicked.connect(self.load_wallpapers)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        # Image count label
        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        layout.addWidget(self.count_label)
        
        self.action_bar.setLayout(layout)
    
    def get_button_style(self):
        """Get consistent button style with theme support"""
        return f"""
            QPushButton {{
                background-color: {self.colors['input_bg']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['input_border']};
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['surface_variant']};
                border-color: {self.colors['border_hover']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['card_hover']};
            }}
        """
    
    def load_wallpapers(self):
        """Load all wallpapers immediately - no lazy loading"""
        # Clear existing
        self.clear_grid()
        self.thumbnail_cards.clear()
        
        # Get wallpapers
        wallpapers = self.wallpaper_manager.get_wallpaper_list()
        
        if not wallpapers:
            self.status_bar.showMessage("No wallpapers found", 5000)
            return
        
        # Get current wallpaper
        self.current_wallpaper = self.wallpaper_manager.get_current_wallpaper()
        
        # Get thumbnail size
        size = self.get_thumbnail_size()
        
        # Load all images
        self.status_bar.showMessage(f"Loading {len(wallpapers)} images...", 0)
        self.thumb_loader.load_batch(wallpapers, size)
        
        # Create all cards immediately
        for wallpaper in wallpapers:
            # Create modern card
            card = ModernThumbnailCard(wallpaper, size)
            card.clicked.connect(self.on_thumbnail_clicked)
            card.double_clicked.connect(self.on_thumbnail_double_clicked)
            card.right_clicked.connect(self.show_context_menu)
            
            # Mark current wallpaper
            if wallpaper == self.current_wallpaper:
                card.set_current(True)
            
            # Check if excluded
            if self.config.is_file_excluded(str(wallpaper)):
                card.set_excluded(True)
            
            # Add to flow layout for responsive display
            self.flow_layout.addWidget(card)
            self.thumbnail_cards[wallpaper] = card
        
        # Process visible items first
        QTimer.singleShot(100, self.prioritize_visible)
        
        # Update stats
        self.filter_panel.update_stats(len(wallpapers), len(wallpapers))
        # Update count instead of showing loading
        if hasattr(self, 'count_label'):
            self.count_label.setText(f"{len(wallpapers)} images")
    
    def clear_grid(self):
        """Clear the flow layout"""
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def on_thumbnail_ready(self, image_path: Path, pixmap: QPixmap, quality: str):
        """Handle thumbnail ready with quality level"""
        if image_path in self.thumbnail_cards:
            card = self.thumbnail_cards[image_path]
            card.set_thumbnail(pixmap, quality)
    
    def on_all_images_loaded(self):
        """All images have been loaded"""
        self.status_bar.showMessage(f"Loaded {len(self.thumbnail_cards)} images", 3000)
    
    def prioritize_visible(self):
        """Prioritize loading of visible items"""
        visible_rect = self.scroll_area.viewport().rect()
        
        for card in self.thumbnail_cards.values():
            card_pos = card.mapTo(self.scroll_area.viewport(), QPoint(0, 0))
            card_rect = QRect(card_pos, QSize(card.width(), card.height()))
            
            if visible_rect.intersects(card_rect):
                # Load this card with priority
                self.thumb_loader.add_task(card.image_path, card.size, 'hd', priority=True)
    
    def request_hd_thumbnail(self, image_path: Path):
        """Request HD quality thumbnail"""
        if image_path not in self.hd_queue:
            self.hd_queue.append(image_path)
            if not self.hd_timer.isActive():
                self.hd_timer.start()
    
    def process_hd_queue(self):
        """Process HD loading queue"""
        if self.hd_queue:
            image_path = self.hd_queue.pop(0)
            size = self.get_thumbnail_size()
            self.thumb_loader.add_task(image_path, size, 'hd')
        else:
            self.hd_timer.stop()
    
    def on_loading_progress(self, completed: int, total: int):
        """Update loading progress"""
        if completed < total:
            # Show progress only in status bar
            self.status_bar.showMessage(f"Loading... {completed}/{total}")
        else:
            self.status_bar.showMessage("All images loaded", 2000)
    
    def on_thumbnail_clicked(self, image_path: Path):
        """Handle thumbnail selection"""
        # Update selection
        if self.selected_path and self.selected_path in self.thumbnail_cards:
            self.thumbnail_cards[self.selected_path].set_selected(False)
        
        self.selected_path = image_path
        
        if image_path in self.thumbnail_cards:
            self.thumbnail_cards[image_path].set_selected(True)
            
            # Smooth scroll to selected item
            card = self.thumbnail_cards[image_path]
            self.scroll_area.ensureWidgetVisible(card, 50, 50)
    
    def on_thumbnail_double_clicked(self, image_path: Path):
        """Apply wallpaper on double click"""
        self.wallpaper_manager.set_wallpaper(image_path)
        self.status_bar.showMessage(f"Wallpaper applied: {image_path.name}", 3000)
        
        # Update current wallpaper indicator
        if hasattr(self, 'current_wallpaper') and self.current_wallpaper in self.thumbnail_cards:
            self.thumbnail_cards[self.current_wallpaper].set_current(False)
        
        self.current_wallpaper = image_path
        if image_path in self.thumbnail_cards:
            self.thumbnail_cards[image_path].set_current(True)
    
    def show_context_menu(self, image_path: Path, pos: QPoint):
        """Show context menu for thumbnail"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colors['surface']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 5px;
                color: {self.colors['text_primary']};
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colors['selection']};
            }}
        """)
        
        # Actions
        apply_action = menu.addAction("✓ Apply Wallpaper")
        apply_action.triggered.connect(lambda: self.apply_wallpaper(image_path))
        
        preview_action = menu.addAction("👁 Preview")
        preview_action.triggered.connect(lambda: self.on_thumbnail_double_clicked(image_path))
        
        menu.addSeparator()
        
        # Toggle favorite
        favorite_action = menu.addAction("★ Add to Favorites")
        favorite_action.triggered.connect(lambda: self.toggle_favorite(image_path))
        
        # Toggle exclusion
        is_excluded = self.config.is_file_excluded(str(image_path))
        exclude_text = "✓ Include in Rotation" if is_excluded else "⊘ Exclude from Rotation"
        exclude_action = menu.addAction(exclude_text)
        exclude_action.triggered.connect(lambda: self.toggle_exclusion(image_path))
        
        menu.addSeparator()
        
        # File operations
        info_action = menu.addAction("ℹ Properties")
        info_action.triggered.connect(lambda: self.show_properties(image_path))
        
        menu.exec(pos)
    
    def apply_wallpaper(self, image_path: Path = None):
        """Apply wallpaper"""
        path = image_path or self.selected_path
        if path:
            if self.wallpaper_manager.set_wallpaper(path):
                self.status_bar.showMessage(f"✓ Wallpaper applied: {path.name}", 5000)
                
                # Update current indicator
                if self.current_wallpaper and self.current_wallpaper in self.thumbnail_cards:
                    self.thumbnail_cards[self.current_wallpaper].set_current(False)
                
                self.current_wallpaper = path
                if path in self.thumbnail_cards:
                    self.thumbnail_cards[path].set_current(True)
                
                self.wallpaper_selected.emit(path)
            else:
                self.status_bar.showMessage("✗ Failed to apply wallpaper", 5000)
    
    def toggle_favorite(self, image_path: Path):
        """Toggle favorite status"""
        if image_path in self.thumbnail_cards:
            card = self.thumbnail_cards[image_path]
            card.set_favorite(not card.is_favorite)
            
            # Save to config
            favorites = self.config.get('favorites', [])
            path_str = str(image_path)
            
            if card.is_favorite:
                if path_str not in favorites:
                    favorites.append(path_str)
                self.status_bar.showMessage(f"★ Added to favorites: {image_path.name}", 3000)
            else:
                if path_str in favorites:
                    favorites.remove(path_str)
                self.status_bar.showMessage(f"☆ Removed from favorites: {image_path.name}", 3000)
            
            self.config.set('favorites', favorites)
    
    def toggle_exclusion(self, image_path: Path):
        """Toggle exclusion status"""
        self.config.toggle_file_exclusion(str(image_path))
        
        if image_path in self.thumbnail_cards:
            is_excluded = self.config.is_file_excluded(str(image_path))
            self.thumbnail_cards[image_path].set_excluded(is_excluded)
            
            if is_excluded:
                self.status_bar.showMessage(f"⊘ Excluded: {image_path.name}", 3000)
            else:
                self.status_bar.showMessage(f"✓ Included: {image_path.name}", 3000)
    
    def show_properties(self, image_path: Path):
        """Show image properties"""
        info = self.wallpaper_manager.get_image_info(image_path)
        
        # Format properties
        from datetime import datetime
        modified = datetime.fromtimestamp(info['modified']).strftime('%Y-%m-%d %H:%M')
        
        properties = (
            f"<b>File:</b> {info['name']}<br>"
            f"<b>Path:</b> {info['path']}<br>"
            f"<b>Dimensions:</b> {info['dimensions'][0]} × {info['dimensions'][1]} pixels<br>"
            f"<b>Size:</b> {info['size'] / 1024 / 1024:.2f} MB<br>"
            f"<b>Format:</b> {info['format']}<br>"
            f"<b>Modified:</b> {modified}"
        )
        
        # Show in message box
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Image Properties")
        msg.setText(properties)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.exec()
    
    def apply_filters(self, filters: dict):
        """Apply filters to grid"""
        search_text = filters['search'].lower()
        sort_by = filters['sort']
        size = filters['size']
        show_excluded = filters['show_excluded']
        
        # Update thumbnail size if changed
        if size != self.filter_panel.size_combo.currentText():
            self.load_wallpapers()
            return
        
        # Filter and sort
        visible_count = 0
        for path, card in self.thumbnail_cards.items():
            # Search filter
            visible = search_text in path.name.lower()
            
            # Exclusion filter
            if not show_excluded and card.is_excluded:
                visible = False
            
            card.setVisible(visible)
            if visible:
                visible_count += 1
        
        # Update stats
        self.filter_panel.update_stats(len(self.thumbnail_cards), visible_count)
    
    def select_random(self):
        """Select random wallpaper with animation"""
        visible_cards = [
            (path, card) for path, card in self.thumbnail_cards.items()
            if card.isVisible() and not card.is_excluded
        ]
        
        if visible_cards:
            random_path, random_card = random.choice(visible_cards)
            self.on_thumbnail_clicked(random_path)
            
            # Animate selection
            if ThemeManager.is_dark_mode():
                random_card.shadow_effect.setBlurRadius(20)
                random_card.shadow_effect.setColor(QColor(76, 175, 80, 80))
            else:
                random_card.shadow_effect.setBlurRadius(30)
                random_card.shadow_effect.setColor(QColor(76, 175, 80, 150))
            
            # Reset after animation
            QTimer.singleShot(500, lambda: random_card.set_selected(True))
    
    def get_thumbnail_size(self) -> int:
        """Get optimized thumbnail sizes"""
        sizes = {
            "Small": 120,      # Optimized from 200
            "Medium": 180,     # Optimized from 280
            "Large": 240,      # Optimized from 360
            "Extra Large": 320 # Optimized from 440
        }
        return sizes.get(self.filter_panel.size_combo.currentText(), 180)
    
    def restore_geometry(self):
        """Restore window geometry"""
        geometry = self.config.get('window_geometry', {})
        if geometry:
            self.move(geometry.get('x', 100), geometry.get('y', 100))
            self.resize(geometry.get('width', 1200), geometry.get('height', 800))
    
    def save_geometry(self):
        """Save window geometry"""
        geometry = {
            'x': self.x(),
            'y': self.y(),
            'width': self.width(),
            'height': self.height()
        }
        self.config.set('window_geometry', geometry)
    
    def on_theme_changed(self):
        """Handle system theme change"""
        # Update colors
        self.colors = ThemeManager.get_colors()
        
        # Refresh UI elements
        self.setup_ui()
        
        # Reload wallpapers with new theme
        QTimer.singleShot(100, self.load_wallpapers)
    
    def closeEvent(self, event):
        """Handle close event"""
        self.save_geometry()
        self.thumb_loader.stop()
        self.thumb_loader.wait()
        event.accept()