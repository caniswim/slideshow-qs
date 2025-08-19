#!/usr/bin/env python3
"""
Gallery window for wallpaper selection with preview
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QScrollArea, QLabel, QPushButton, QLineEdit,
    QComboBox, QGridLayout, QSplitter, QFrame,
    QSizePolicy, QToolBar, QStatusBar, QProgressBar
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QAction, QShortcut, QKeySequence
from pathlib import Path
from typing import Optional, List
import threading


class ThumbnailLoader(QThread):
    """Thread for loading thumbnails in background"""
    thumbnail_ready = pyqtSignal(Path, QPixmap)
    
    def __init__(self, wallpaper_manager):
        super().__init__()
        self.wallpaper_manager = wallpaper_manager
        self.tasks = []
        self.running = True
    
    def add_task(self, image_path: Path, size: int = 150):
        """Add thumbnail loading task"""
        self.tasks.append((image_path, size))
    
    def run(self):
        """Run thumbnail loading thread"""
        while self.running:
            if self.tasks:
                image_path, size = self.tasks.pop(0)
                thumb_path = self.wallpaper_manager.create_thumbnail(image_path, size)
                if thumb_path:
                    pixmap = QPixmap(str(thumb_path))
                    self.thumbnail_ready.emit(image_path, pixmap)
            else:
                self.msleep(100)
    
    def stop(self):
        """Stop the thread"""
        self.running = False


class ThumbnailWidget(QFrame):
    """Widget for displaying a wallpaper thumbnail"""
    clicked = pyqtSignal(Path)
    double_clicked = pyqtSignal(Path)
    
    def __init__(self, image_path: Path, size: int = 150):
        super().__init__()
        self.image_path = image_path
        self.size = size
        self.selected = False
        
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFixedSize(size + 20, size + 40)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Thumbnail label
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setFixedSize(size, size)
        self.thumb_label.setStyleSheet("QLabel { background-color: #f0f0f0; }")
        self.thumb_label.setText("Loading...")
        layout.addWidget(self.thumb_label)
        
        # Filename label
        self.name_label = QLabel(image_path.name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(30)
        font = self.name_label.font()
        font.setPointSize(8)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)
        
        self.setLayout(layout)
        self.update_style()
    
    def set_thumbnail(self, pixmap: QPixmap):
        """Set the thumbnail image"""
        scaled = pixmap.scaled(
            self.size, self.size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.thumb_label.setPixmap(scaled)
    
    def set_selected(self, selected: bool):
        """Set selection state"""
        self.selected = selected
        self.update_style()
    
    def update_style(self):
        """Update widget style based on selection"""
        if self.selected:
            self.setStyleSheet("""
                ThumbnailWidget {
                    border: 3px solid #0078d4;
                    background-color: #e3f2fd;
                }
            """)
        else:
            self.setStyleSheet("""
                ThumbnailWidget {
                    border: 1px solid #cccccc;
                    background-color: white;
                }
                ThumbnailWidget:hover {
                    border: 2px solid #0078d4;
                    background-color: #f5f5f5;
                }
            """)
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_path)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.image_path)


class GalleryWindow(QMainWindow):
    """Main gallery window for wallpaper selection"""
    
    wallpaper_selected = pyqtSignal(Path)
    
    def __init__(self, config_manager, wallpaper_manager):
        super().__init__()
        self.config = config_manager
        self.wallpaper_manager = wallpaper_manager
        self.thumbnail_widgets = {}
        self.selected_path = None
        self.current_filter = ""
        
        self.setup_ui()
        self.setup_shortcuts()
        self.restore_geometry()
        
        # Start thumbnail loader thread
        self.thumb_loader = ThumbnailLoader(self.wallpaper_manager)
        self.thumb_loader.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumb_loader.start()
        
        # Load wallpapers
        QTimer.singleShot(100, self.load_wallpapers)
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Wallpaper Gallery")
        self.setMinimumSize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main layout with splitter
        main_layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search wallpapers...")
        self.search_input.textChanged.connect(self.filter_wallpapers)
        search_layout.addWidget(self.search_input)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Date Modified", "Random"])
        self.sort_combo.currentTextChanged.connect(self.sort_wallpapers)
        search_layout.addWidget(QLabel("Sort:"))
        search_layout.addWidget(self.sort_combo)
        
        main_layout.addLayout(search_layout)
        
        # Create splitter for thumbnails and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Thumbnail grid area
        self.create_thumbnail_area()
        splitter.addWidget(self.scroll_area)
        
        # Preview area
        self.create_preview_area()
        splitter.addWidget(self.preview_widget)
        
        # Set splitter sizes (60% thumbnails, 40% preview)
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("Apply Wallpaper")
        self.apply_button.clicked.connect(self.apply_wallpaper)
        self.apply_button.setEnabled(False)
        button_layout.addWidget(self.apply_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_wallpapers)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        
        self.wallpaper_count_label = QLabel("0 wallpapers")
        button_layout.addWidget(self.wallpaper_count_label)
        
        main_layout.addLayout(button_layout)
        
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_toolbar(self):
        """Create toolbar with actions"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Random wallpaper action
        random_action = QAction("Random", self)
        random_action.setShortcut("Ctrl+R")
        random_action.triggered.connect(self.select_random)
        toolbar.addAction(random_action)
        
        toolbar.addSeparator()
        
        # View options
        self.view_size_combo = QComboBox()
        self.view_size_combo.addItems(["Small", "Medium", "Large"])
        self.view_size_combo.setCurrentText("Medium")
        self.view_size_combo.currentTextChanged.connect(self.change_thumbnail_size)
        toolbar.addWidget(QLabel("Size:"))
        toolbar.addWidget(self.view_size_combo)
        
        toolbar.addSeparator()
        
        # Clear cache action
        clear_cache_action = QAction("Clear Cache", self)
        clear_cache_action.triggered.connect(self.clear_cache)
        toolbar.addAction(clear_cache_action)
    
    def create_thumbnail_area(self):
        """Create scrollable thumbnail grid area"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_widget.setLayout(self.grid_layout)
        
        self.scroll_area.setWidget(self.grid_widget)
    
    def create_preview_area(self):
        """Create preview area for selected wallpaper"""
        self.preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        
        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { background-color: #f0f0f0; border: 1px solid #cccccc; }")
        self.preview_label.setText("Select a wallpaper to preview")
        self.preview_label.setScaledContents(False)
        preview_layout.addWidget(self.preview_label)
        
        # Info labels
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setMaximumHeight(100)
        preview_layout.addWidget(self.info_label)
        
        self.preview_widget.setLayout(preview_layout)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        QShortcut(QKeySequence("Escape"), self, self.close)
        QShortcut(QKeySequence("Return"), self, self.apply_wallpaper)
        QShortcut(QKeySequence("F5"), self, self.load_wallpapers)
    
    def load_wallpapers(self):
        """Load wallpapers into grid"""
        # Clear existing thumbnails
        self.clear_grid()
        self.thumbnail_widgets.clear()
        
        # Get wallpaper list
        wallpapers = self.wallpaper_manager.get_wallpaper_list()
        
        if not wallpapers:
            self.status_bar.showMessage("No wallpapers found in directory", 5000)
            self.wallpaper_count_label.setText("0 wallpapers")
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(wallpapers))
        self.progress_bar.setValue(0)
        
        # Get grid dimensions
        columns = self.config.get('gallery_columns', 4)
        thumb_size = self.get_thumbnail_size()
        
        # Create thumbnail widgets
        for i, wallpaper in enumerate(wallpapers):
            row = i // columns
            col = i % columns
            
            # Create thumbnail widget
            thumb_widget = ThumbnailWidget(wallpaper, thumb_size)
            thumb_widget.clicked.connect(self.on_thumbnail_clicked)
            thumb_widget.double_clicked.connect(self.on_thumbnail_double_clicked)
            
            self.grid_layout.addWidget(thumb_widget, row, col)
            self.thumbnail_widgets[wallpaper] = thumb_widget
            
            # Queue thumbnail loading
            self.thumb_loader.add_task(wallpaper, thumb_size)
            
            # Update progress
            self.progress_bar.setValue(i + 1)
        
        # Update count
        self.wallpaper_count_label.setText(f"{len(wallpapers)} wallpapers")
        
        # Hide progress
        QTimer.singleShot(500, lambda: self.progress_bar.setVisible(False))
    
    def clear_grid(self):
        """Clear the thumbnail grid"""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def on_thumbnail_ready(self, image_path: Path, pixmap: QPixmap):
        """Handle thumbnail ready signal"""
        if image_path in self.thumbnail_widgets:
            self.thumbnail_widgets[image_path].set_thumbnail(pixmap)
    
    def on_thumbnail_clicked(self, image_path: Path):
        """Handle thumbnail click"""
        self.select_wallpaper(image_path)
    
    def on_thumbnail_double_clicked(self, image_path: Path):
        """Handle thumbnail double click"""
        self.select_wallpaper(image_path)
        self.apply_wallpaper()
    
    def select_wallpaper(self, image_path: Path):
        """Select a wallpaper and show preview"""
        # Update selection
        if self.selected_path and self.selected_path in self.thumbnail_widgets:
            self.thumbnail_widgets[self.selected_path].set_selected(False)
        
        self.selected_path = image_path
        
        if image_path in self.thumbnail_widgets:
            self.thumbnail_widgets[image_path].set_selected(True)
        
        # Show preview
        self.show_preview(image_path)
        
        # Enable apply button
        self.apply_button.setEnabled(True)
    
    def show_preview(self, image_path: Path):
        """Show wallpaper preview"""
        try:
            pixmap = QPixmap(str(image_path))
            
            # Scale to fit preview area
            preview_size = self.preview_label.size()
            scaled = pixmap.scaled(
                preview_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
            
            # Show image info
            info = self.wallpaper_manager.get_image_info(image_path)
            info_text = f"<b>{info['name']}</b><br>"
            info_text += f"Dimensions: {info['dimensions'][0]}x{info['dimensions'][1]}<br>"
            info_text += f"Size: {info['size'] / 1024 / 1024:.2f} MB<br>"
            info_text += f"Format: {info['format']}"
            self.info_label.setText(info_text)
            
        except Exception as e:
            self.preview_label.setText(f"Error loading preview: {e}")
            self.info_label.setText("")
    
    def apply_wallpaper(self):
        """Apply selected wallpaper"""
        if self.selected_path:
            if self.wallpaper_manager.set_wallpaper(self.selected_path):
                self.status_bar.showMessage(f"Wallpaper set: {self.selected_path.name}", 5000)
                self.wallpaper_selected.emit(self.selected_path)
            else:
                self.status_bar.showMessage("Failed to set wallpaper", 5000)
    
    def filter_wallpapers(self, text: str):
        """Filter wallpapers by search text"""
        self.current_filter = text.lower()
        
        for path, widget in self.thumbnail_widgets.items():
            visible = self.current_filter in path.name.lower()
            widget.setVisible(visible)
    
    def sort_wallpapers(self, sort_type: str):
        """Sort wallpapers"""
        # This would require reloading the grid with sorted wallpapers
        # For now, just refresh with new sort
        self.wallpaper_manager.refresh_wallpaper_list()
        self.load_wallpapers()
    
    def select_random(self):
        """Select a random wallpaper"""
        wallpapers = list(self.thumbnail_widgets.keys())
        if wallpapers:
            import random
            random_path = random.choice(wallpapers)
            self.select_wallpaper(random_path)
    
    def change_thumbnail_size(self, size_text: str):
        """Change thumbnail size"""
        sizes = {"Small": 100, "Medium": 150, "Large": 200}
        size = sizes.get(size_text, 150)
        self.config.set('thumbnail_size', size)
        
        # Reload with new size
        self.load_wallpapers()
    
    def get_thumbnail_size(self) -> int:
        """Get current thumbnail size"""
        size_text = self.view_size_combo.currentText()
        sizes = {"Small": 100, "Medium": 150, "Large": 200}
        return sizes.get(size_text, 150)
    
    def clear_cache(self):
        """Clear thumbnail cache"""
        self.config.clear_cache()
        self.status_bar.showMessage("Thumbnail cache cleared", 5000)
        self.load_wallpapers()
    
    def restore_geometry(self):
        """Restore window geometry from config"""
        geometry = self.config.get('window_geometry', {})
        if geometry:
            self.move(geometry.get('x', 100), geometry.get('y', 100))
            self.resize(geometry.get('width', 1200), geometry.get('height', 800))
    
    def save_geometry(self):
        """Save window geometry to config"""
        geometry = {
            'x': self.x(),
            'y': self.y(),
            'width': self.width(),
            'height': self.height()
        }
        self.config.set('window_geometry', geometry)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.save_geometry()
        self.thumb_loader.stop()
        self.thumb_loader.wait()
        event.accept()