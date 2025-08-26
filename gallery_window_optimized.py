#!/usr/bin/env python3
"""
Optimized Gallery Window - High performance thumbnail loading
With 2-level loading, parallel processing, and smart caching
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QStatusBar, QMenu, QApplication,
    QDialog, QCheckBox, QLayout, QLayoutItem
)
from PyQt6.QtCore import (
    Qt, QSize, pyqtSignal, QThread, QTimer, QRunnable,
    QThreadPool, QRect, QPoint, pyqtSlot, QObject
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QPainter, QBrush, QPixmapCache,
    QColor, QPalette, QCursor, QGuiApplication, QImage
)
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import hashlib
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os


class FlowLayout(QLayout):
    """Responsive flow layout for thumbnails"""
    
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
        return self.doLayout(QRect(0, 0, width, 0), True)

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


class ThumbnailCache:
    """Persistent thumbnail cache manager"""
    
    def __init__(self):
        self.cache_dir = Path.home() / '.cache' / 'wallpaper-thumbnails'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache = {}  # In-memory cache
        
        # Set QPixmapCache size (in KB)
        QPixmapCache.setCacheLimit(50 * 1024)  # 50MB cache
    
    def get_cache_path(self, image_path: Path, size: int, quality: str = 'fast') -> Path:
        """Get cache file path for thumbnail"""
        # Create unique hash for this image+size+quality combo
        hash_str = f"{image_path}_{size}_{quality}_{image_path.stat().st_mtime}"
        file_hash = hashlib.md5(hash_str.encode()).hexdigest()
        return self.cache_dir / f"{file_hash}.jpg"
    
    def get_thumbnail(self, image_path: Path, size: int, quality: str = 'fast') -> Optional[QPixmap]:
        """Get thumbnail from cache or create it"""
        cache_key = f"{image_path}_{size}_{quality}"
        
        # Check QPixmapCache first
        pixmap = QPixmapCache.find(cache_key)
        if pixmap:
            return pixmap
        
        # Check memory cache
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # Check disk cache
        cache_path = self.get_cache_path(image_path, size, quality)
        if cache_path.exists():
            pixmap = QPixmap(str(cache_path))
            if not pixmap.isNull():
                QPixmapCache.insert(cache_key, pixmap)
                return pixmap
        
        return None
    
    def save_thumbnail(self, image_path: Path, pixmap: QPixmap, size: int, quality: str = 'fast'):
        """Save thumbnail to cache"""
        cache_key = f"{image_path}_{size}_{quality}"
        cache_path = self.get_cache_path(image_path, size, quality)
        
        # Save to disk with JPEG compression
        jpeg_quality = 85 if quality == 'hd' else 60
        pixmap.save(str(cache_path), 'JPEG', jpeg_quality)
        
        # Add to QPixmapCache
        QPixmapCache.insert(cache_key, pixmap)
        
        # Limit memory cache size
        if len(self.memory_cache) > 100:
            # Remove oldest entries
            self.memory_cache.clear()
        self.memory_cache[cache_key] = pixmap


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
        """Load thumbnail in background thread"""
        try:
            # Check cache first
            pixmap = self.cache.get_thumbnail(self.image_path, self.size, self.quality)
            if pixmap:
                self.signals.finished.emit(self.image_path, pixmap, self.quality)
                return
            
            # Load and scale image
            image = QImage(str(self.image_path))
            if image.isNull():
                self.signals.error.emit(self.image_path, "Failed to load image")
                return
            
            # Scale based on quality setting
            if self.quality == 'fast':
                # Fast preview - lower quality, faster loading
                scaled = image.scaled(
                    self.size, self.size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
            else:
                # HD quality - smooth transformation
                scaled = image.scaled(
                    self.size, self.size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            pixmap = QPixmap.fromImage(scaled)
            
            # Save to cache
            self.cache.save_thumbnail(self.image_path, pixmap, self.size, self.quality)
            
            # Emit result
            self.signals.finished.emit(self.image_path, pixmap, self.quality)
            
        except Exception as e:
            self.signals.error.emit(self.image_path, str(e))


class OptimizedThumbnailCard(QFrame):
    """Optimized thumbnail card with 2-level loading"""
    clicked = pyqtSignal(Path)
    double_clicked = pyqtSignal(Path)
    right_clicked = pyqtSignal(Path, QPoint)
    
    def __init__(self, image_path: Path, size: int = 180):
        super().__init__()
        self.image_path = image_path
        self.size = size
        self.preview_loaded = False
        self.hd_loaded = False
        self.is_visible = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup minimal UI"""
        self.setFixedSize(self.size + 20, self.size + 40)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 5)
        
        # Thumbnail label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(self.size, self.size)
        self.thumb_label.setScaledContents(True)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Fast placeholder - solid color
        self.set_placeholder()
        
        # File name label
        self.name_label = QLabel(self.image_path.name[:20])
        self.name_label.setMaximumHeight(20)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.name_label.font()
        font.setPointSize(9)
        self.name_label.setFont(font)
        
        layout.addWidget(self.thumb_label)
        layout.addWidget(self.name_label)
        self.setLayout(layout)
        
        # Simple styling
        self.setStyleSheet("""
            OptimizedThumbnailCard {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            OptimizedThumbnailCard:hover {
                border: 2px solid #2196f3;
            }
        """)
    
    def set_placeholder(self):
        """Set ultra-light placeholder"""
        placeholder = QPixmap(self.size, self.size)
        placeholder.fill(QColor(240, 240, 240))
        self.thumb_label.setPixmap(placeholder)
    
    def set_preview(self, pixmap: QPixmap):
        """Set fast preview thumbnail"""
        self.thumb_label.setPixmap(pixmap)
        self.preview_loaded = True
    
    def set_hd_thumbnail(self, pixmap: QPixmap):
        """Set HD quality thumbnail"""
        if self.preview_loaded:  # Only update if preview was loaded
            self.thumb_label.setPixmap(pixmap)
            self.hd_loaded = True
    
    def enterEvent(self, event):
        """Request HD on hover"""
        super().enterEvent(event)
        if self.preview_loaded and not self.hd_loaded:
            # Find the gallery window
            gallery = self.window()
            if hasattr(gallery, 'request_hd_thumbnail'):
                gallery.request_hd_thumbnail(self.image_path)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_path)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.image_path, event.globalPosition().toPoint())
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.image_path)


class OptimizedGalleryWindow(QMainWindow):
    """Optimized gallery with fast loading"""
    
    wallpaper_selected = pyqtSignal(Path)
    
    def __init__(self, config_manager, wallpaper_manager):
        super().__init__()
        self.config = config_manager
        self.wallpaper_manager = wallpaper_manager
        self.thumbnail_cards: Dict[Path, OptimizedThumbnailCard] = {}
        self.cache = ThumbnailCache()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(8)  # Use 8 threads for parallel loading
        
        # Loading queues
        self.preview_queue = []
        self.hd_queue = []
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.process_loading_queue)
        
        self.setup_ui()
        self.load_wallpapers()
    
    def setup_ui(self):
        """Setup optimized UI"""
        self.setWindowTitle("Gallery - Optimized")
        self.setMinimumSize(1000, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Scroll area with flow layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_widget = QWidget()
        self.flow_layout = FlowLayout(margin=15, spacing=15)
        self.grid_widget.setLayout(self.flow_layout)
        
        self.scroll_area.setWidget(self.grid_widget)
        layout.addWidget(self.scroll_area)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        central.setLayout(layout)
    
    def create_header(self) -> QWidget:
        """Create simple header"""
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background: #f5f5f5; border-bottom: 1px solid #ddd;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Title
        title = QLabel("Wallpaper Gallery - Optimized")
        font = title.font()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        
        # Size selector
        size_label = QLabel("Size:")
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Small", "Medium", "Large", "Extra Large"])
        self.size_combo.setCurrentText("Medium")
        self.size_combo.currentTextChanged.connect(self.on_size_changed)
        
        # Stats label
        self.stats_label = QLabel()
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.stats_label)
        layout.addWidget(size_label)
        layout.addWidget(self.size_combo)
        
        header.setLayout(layout)
        return header
    
    def get_thumbnail_size(self) -> int:
        """Get optimized thumbnail sizes"""
        sizes = {
            "Small": 120,      # Reduced from 200
            "Medium": 180,     # Reduced from 280
            "Large": 240,      # Reduced from 360
            "Extra Large": 320 # Reduced from 440
        }
        return sizes.get(self.size_combo.currentText(), 180)
    
    def load_wallpapers(self):
        """Load wallpapers with optimized strategy"""
        # Clear existing
        self.clear_grid()
        
        # Get wallpapers
        wallpapers = self.wallpaper_manager.get_wallpaper_list()
        if not wallpapers:
            self.status_bar.showMessage("No wallpapers found")
            return
        
        size = self.get_thumbnail_size()
        self.status_bar.showMessage(f"Loading {len(wallpapers)} wallpapers...")
        
        # Create cards immediately with placeholders
        for wallpaper in wallpapers:
            card = OptimizedThumbnailCard(wallpaper, size)
            card.clicked.connect(self.on_thumbnail_clicked)
            card.double_clicked.connect(self.on_thumbnail_double_clicked)
            
            self.flow_layout.addWidget(card)
            self.thumbnail_cards[wallpaper] = card
            
            # Queue for preview loading
            self.preview_queue.append(wallpaper)
        
        # Update stats
        self.stats_label.setText(f"{len(wallpapers)} images")
        
        # Start loading previews after UI is responsive
        QTimer.singleShot(100, self.start_preview_loading)
    
    def start_preview_loading(self):
        """Start loading preview thumbnails"""
        # Load visible items first
        visible_cards = self.get_visible_cards()
        
        # Prioritize visible items
        for card in visible_cards:
            if card.image_path in self.preview_queue:
                self.preview_queue.remove(card.image_path)
                self.preview_queue.insert(0, card.image_path)
        
        # Start batch loading
        self.loading_timer.start(10)  # Process every 10ms
    
    def process_loading_queue(self):
        """Process loading queue in batches"""
        batch_size = 4  # Load 4 images per batch
        
        for _ in range(batch_size):
            if self.preview_queue:
                image_path = self.preview_queue.pop(0)
                self.load_thumbnail_async(image_path, 'fast')
            elif self.hd_queue:
                image_path = self.hd_queue.pop(0)
                self.load_thumbnail_async(image_path, 'hd')
            else:
                self.loading_timer.stop()
                self.status_bar.showMessage("All thumbnails loaded", 2000)
                break
    
    def load_thumbnail_async(self, image_path: Path, quality: str):
        """Load thumbnail asynchronously"""
        size = self.get_thumbnail_size()
        worker = ThumbnailWorker(image_path, size, quality, self.cache)
        worker.signals.finished.connect(self.on_thumbnail_ready)
        worker.signals.error.connect(self.on_thumbnail_error)
        self.thread_pool.start(worker)
    
    def on_thumbnail_ready(self, image_path: Path, pixmap: QPixmap, quality: str):
        """Handle loaded thumbnail"""
        if image_path in self.thumbnail_cards:
            card = self.thumbnail_cards[image_path]
            if quality == 'fast':
                card.set_preview(pixmap)
            else:
                card.set_hd_thumbnail(pixmap)
    
    def on_thumbnail_error(self, image_path: Path, error: str):
        """Handle loading error"""
        print(f"Error loading {image_path}: {error}")
    
    def request_hd_thumbnail(self, image_path: Path):
        """Request HD thumbnail for specific image"""
        if image_path not in self.hd_queue:
            self.hd_queue.insert(0, image_path)
            if not self.loading_timer.isActive():
                self.loading_timer.start(10)
    
    def get_visible_cards(self) -> List[OptimizedThumbnailCard]:
        """Get currently visible cards"""
        visible_cards = []
        viewport_rect = self.scroll_area.viewport().rect()
        
        for card in self.thumbnail_cards.values():
            card_pos = card.mapTo(self.scroll_area.viewport(), QPoint(0, 0))
            card_rect = QRect(card_pos, QSize(card.width(), card.height()))
            
            if viewport_rect.intersects(card_rect):
                visible_cards.append(card)
        
        return visible_cards
    
    def clear_grid(self):
        """Clear the grid"""
        self.preview_queue.clear()
        self.hd_queue.clear()
        self.loading_timer.stop()
        
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.thumbnail_cards.clear()
    
    def on_size_changed(self):
        """Handle size change"""
        self.load_wallpapers()
    
    def on_thumbnail_clicked(self, image_path: Path):
        """Handle thumbnail click"""
        self.wallpaper_selected.emit(image_path)
    
    def on_thumbnail_double_clicked(self, image_path: Path):
        """Handle double click - show preview"""
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            # Simple preview dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(image_path.name)
            dialog.setModal(True)
            
            layout = QVBoxLayout()
            label = QLabel()
            
            # Scale to fit screen
            screen_size = QApplication.primaryScreen().size()
            max_size = QSize(int(screen_size.width() * 0.8), int(screen_size.height() * 0.8))
            scaled = pixmap.scaled(max_size, Qt.AspectRatioMode.KeepAspectRatio, 
                                  Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)
            
            layout.addWidget(label)
            dialog.setLayout(layout)
            dialog.exec()
    
    def closeEvent(self, event):
        """Clean up on close"""
        self.loading_timer.stop()
        self.thread_pool.waitForDone(1000)
        super().closeEvent(event)