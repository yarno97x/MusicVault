import sys
import os
import json
import requests
from io import BytesIO
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                               QLineEdit, QSlider, QComboBox, QScrollArea, 
                               QFrame, QDialog, QDialogButtonBox, QMessageBox,
                               QTabWidget, QGroupBox, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QPixmap, QFont, QIcon
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from plotly.offline import plot
import tempfile
import webbrowser

# Import your existing modules
from database import Database
from record import Record


class ImageLoader(QThread):
    """Thread for loading images asynchronously"""
    image_loaded = Signal(str, QPixmap)
    
    def __init__(self, url, identifier):
        super().__init__()
        self.url = url
        self.identifier = identifier
    
    def run(self):
        try:
            response = requests.get(self.url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.image_loaded.emit(self.identifier, pixmap)
        except Exception as e:
            print(f"Error loading image: {e}")


class RatingDialog(QDialog):
    """Dialog for rating albums"""
    
    def __init__(self, album_name, current_rating=0.0):
        super().__init__()
        self.setWindowTitle(f"Rate '{album_name}'")
        self.setFixedSize(300, 150)
        self.rating = current_rating
        
        layout = QVBoxLayout()
        
        # Rating label
        self.rating_label = QLabel(f"Rating: {self.rating:.1f}/5")
        self.rating_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.rating_label)
        
        # Rating slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(50)  # 0-5.0 with 0.1 increments
        self.slider.setValue(int(current_rating * 10))
        self.slider.valueChanged.connect(self.update_rating)
        layout.addWidget(self.slider)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def update_rating(self, value):
        self.rating = value / 10.0
        self.rating_label.setText(f"Rating: {self.rating:.1f}/5")
    
    def get_rating(self):
        return self.rating


class AlbumWidget(QFrame):
    """Widget to display a single album"""
    
    def __init__(self, record, parent_window, is_library=True):
        super().__init__()
        self.record = record
        self.parent_window = parent_window
        self.is_library = is_library
        
        self.setFrameStyle(QFrame.Box)
        self.setFixedSize(200, 320)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Album cover
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(150, 150)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("border: 1px solid gray;")
        
        # Load image asynchronously
        self.image_loader = ImageLoader(record.img_url, record.uri)
        self.image_loader.image_loaded.connect(self.set_image)
        self.image_loader.start()
        
        layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)
        
        # Album name
        name_label = QLabel(record.name)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(40)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(name_label)
        
        # Artist name
        artist_label = QLabel(record.artist)
        artist_label.setWordWrap(True)
        artist_label.setMaximumHeight(20)
        layout.addWidget(artist_label)
        
        # Rating (for library items)
        if is_library:
            if record.rated:
                rating_label = QLabel(f"⭐ Rating: {record.rated}/5")
            else:
                rating_label = QLabel("⭐ Unrated")
            layout.addWidget(rating_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if is_library:
            rate_btn = QPushButton("Rate")
            rate_btn.clicked.connect(self.rate_album)
            button_layout.addWidget(rate_btn)
            
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(self.remove_from_library)
            button_layout.addWidget(remove_btn)
        else:
            log_btn = QPushButton("Log")
            log_btn.clicked.connect(self.move_to_library)
            button_layout.addWidget(log_btn)
            
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(self.remove_from_wishlist)
            button_layout.addWidget(remove_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def set_image(self, identifier, pixmap):
        if identifier == self.record.uri:
            scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cover_label.setPixmap(scaled_pixmap)
    
    def rate_album(self):
        current_rating = float(self.record.rated) if self.record.rated else 0.0
        dialog = RatingDialog(self.record.name, current_rating)
        
        if dialog.exec() == QDialog.Accepted:
            new_rating = dialog.get_rating()
            self.record.rate(new_rating)
            self.parent_window.db.save()
            self.parent_window.refresh_current_tab()
    
    def remove_from_library(self):
        reply = QMessageBox.question(self, 'Confirm Removal', 
                                   f'Remove "{self.record.name}" from library?',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.parent_window.db.remove_from_library(self.record)
            self.parent_window.db.save()
            self.parent_window.refresh_current_tab()
    
    def remove_from_wishlist(self):
        reply = QMessageBox.question(self, 'Confirm Removal',
                                   f'Remove "{self.record.name}" from wishlist?',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.parent_window.db.remove_from_wishlist(self.record)
            self.parent_window.db.save()
            self.parent_window.refresh_current_tab()
    
    def move_to_library(self):
        dialog = RatingDialog(self.record.name)
        
        if dialog.exec() == QDialog.Accepted:
            rating = dialog.get_rating()
            self.parent_window.db.add_to_library(self.record, rating)
            self.parent_window.db.save()
            self.parent_window.refresh_current_tab()
            QMessageBox.information(self, 'Success', 'Album moved to library!')


class StatsWidget(QWidget):
    """Statistics tab widget"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Overview metrics
        metrics_layout = QHBoxLayout()
        
        library_count = len(self.db.library)
        wishlist_count = len(self.db.wishlist)
        
        library_label = QLabel(f"Library Albums\n{library_count}")
        library_label.setAlignment(Qt.AlignCenter)
        library_label.setStyleSheet("border: 1px solid gray; padding: 10px; font-size: 14px;")
        
        wishlist_label = QLabel(f"Wishlist Albums\n{wishlist_count}")
        wishlist_label.setAlignment(Qt.AlignCenter)
        wishlist_label.setStyleSheet("border: 1px solid gray; padding: 10px; font-size: 14px;")
        
        total_label = QLabel(f"Total Albums\n{library_count + wishlist_count}")
        total_label.setAlignment(Qt.AlignCenter)
        total_label.setStyleSheet("border: 1px solid gray; padding: 10px; font-size: 14px;")
        
        metrics_layout.addWidget(library_label)
        metrics_layout.addWidget(wishlist_label)
        metrics_layout.addWidget(total_label)
        
        layout.addLayout(metrics_layout)
        
        if library_count > 0:
            library_list = list(self.db.library)
            
            # Rating statistics
            rated_albums = [album for album in library_list if album.rated is not None]
            unrated_count = library_count - len(rated_albums)
            
            if rated_albums:
                ratings = [float(album.rated) for album in rated_albums]
                avg_rating = sum(ratings) / len(ratings)
                
                rating_info = QLabel(f"Average Rating: {avg_rating:.1f}/5")
                if unrated_count > 0:
                    rating_info.setText(rating_info.text() + f" ({unrated_count} unrated)")
                rating_info.setFont(QFont("Arial", 12, QFont.Bold))
                layout.addWidget(rating_info)
                
                # Generate charts button
                charts_btn = QPushButton("View Detailed Charts")
                charts_btn.clicked.connect(self.show_charts)
                layout.addWidget(charts_btn)
            
            # Top artists
            artist_counts = {}
            for album in library_list:
                artist_counts[album.artist] = artist_counts.get(album.artist, 0) + 1
            
            if artist_counts:
                sorted_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                top_artists_group = QGroupBox("Top Artists")
                top_artists_layout = QVBoxLayout()
                
                for i, (artist, count) in enumerate(sorted_artists, 1):
                    artist_label = QLabel(f"{i}. {artist} ({count} albums)")
                    top_artists_layout.addWidget(artist_label)
                
                top_artists_group.setLayout(top_artists_layout)
                layout.addWidget(top_artists_group)
            
            # Highest rated albums
            if rated_albums:
                top_rated = sorted(rated_albums, key=lambda x: x.rated, reverse=True)[:5]
                
                top_rated_group = QGroupBox("Highest Rated Albums")
                top_rated_layout = QVBoxLayout()
                
                for i, album in enumerate(top_rated, 1):
                    album_label = QLabel(f"{i}. {album.name} by {album.artist} (⭐ {album.rated:.1f}/5)")
                    top_rated_layout.addWidget(album_label)
                
                top_rated_group.setLayout(top_rated_layout)
                layout.addWidget(top_rated_group)
        
        else:
            info_label = QLabel("Add some albums to your library to see statistics!")
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setFont(QFont("Arial", 14))
            layout.addWidget(info_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def show_charts(self):
        """Generate and show charts in browser"""
        library_list = list(self.db.library)
        rated_albums = [album for album in library_list if album.rated is not None]
        
        if not rated_albums:
            QMessageBox.information(self, 'No Data', 'No rated albums to display charts for.')
            return
        
        # Create rating distribution chart
        ratings = [float(album.rated) for album in rated_albums]
        fig = px.histogram(
            x=ratings, 
            nbins=10, 
            title="Distribution of Ratings",
            labels={'x': 'Rating', 'y': 'Number of Albums'}
        )
        fig.update_xaxes(range=[0.5, 5.5])
        
        # Save chart to temporary file and open in browser
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            plot(fig, filename=f.name, auto_open=False)
            webbrowser.open(f'file://{f.name}')
        
        QMessageBox.information(self, 'Charts', 'Charts opened in your default browser!')


class LibraryWidget(QWidget):
    """Library tab widget"""
    
    def __init__(self, db, parent_window):
        super().__init__()
        self.db = db
        self.parent_window = parent_window
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Add album section
        add_section = QGroupBox("Add Album to Library")
        add_layout = QHBoxLayout()
        
        self.uri_input = QLineEdit()
        self.uri_input.setPlaceholderText("Spotify Album URI or URL...")
        add_layout.addWidget(self.uri_input, 3)
        
        self.rating_slider = QSlider(Qt.Horizontal)
        self.rating_slider.setMinimum(0)
        self.rating_slider.setMaximum(50)
        self.rating_slider.setValue(25)
        self.rating_slider.valueChanged.connect(self.update_rating_label)
        add_layout.addWidget(QLabel("Rating:"))
        add_layout.addWidget(self.rating_slider, 1)
        
        self.rating_label = QLabel("2.5/5")
        add_layout.addWidget(self.rating_label)
        
        add_btn = QPushButton("Add to Library")
        add_btn.clicked.connect(self.add_to_library)
        add_layout.addWidget(add_btn)
        
        add_section.setLayout(add_layout)
        layout.addWidget(add_section)
        
        # Sort section
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sort by:"))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Artist", "Album", "Rating"])
        self.sort_combo.currentTextChanged.connect(self.refresh_library)
        sort_layout.addWidget(self.sort_combo)
        
        clear_btn = QPushButton("Clear All Library")
        clear_btn.clicked.connect(self.clear_library)
        sort_layout.addWidget(clear_btn)
        
        sort_layout.addStretch()
        layout.addLayout(sort_layout)
        
        # Albums grid
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.albums_layout = QGridLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        
        layout.addWidget(self.scroll_area)
        
        self.setLayout(layout)
        self.refresh_library()
    
    def update_rating_label(self, value):
        rating = value / 10.0
        self.rating_label.setText(f"{rating:.1f}/5")
    
    def add_to_library(self):
        uri = self.uri_input.text().strip()
        if not uri:
            QMessageBox.warning(self, 'Error', 'Please enter a Spotify URI or URL.')
            return
        
        try:
            # Convert URL to URI if needed
            if "http" in uri:
                uri = "spotify:album:" + uri[uri.index("album/") + 6:uri.index("?")]
            
            rating = self.rating_slider.value() / 10.0
            record = Record(uri, rating)
            self.db.add_to_library(record, rating)
            self.db.save()
            
            self.uri_input.clear()
            self.rating_slider.setValue(25)
            self.refresh_library()
            
            QMessageBox.information(self, 'Success', f"Added '{record.name}' by {record.artist} to library!")
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Error adding album: {str(e)}")
    
    def refresh_library(self):
        # Clear existing widgets
        for i in reversed(range(self.albums_layout.count())):
            child = self.albums_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not self.db.library:
            no_albums_label = QLabel("Your library is empty. Add some albums!")
            no_albums_label.setAlignment(Qt.AlignCenter)
            self.albums_layout.addWidget(no_albums_label, 0, 0)
            return
        
        # Sort library
        library_list = list(self.db.library)
        sort_by = self.sort_combo.currentText()
        
        if sort_by == "Artist":
            library_list.sort(key=lambda x: x.artist)
        elif sort_by == "Album":
            library_list.sort(key=lambda x: x.name)
        elif sort_by == "Rating":
            library_list.sort(key=lambda x: float(x.rated) if x.rated is not None else 0, reverse=True)
        
        # Add albums to grid
        cols = 4
        for i, record in enumerate(library_list):
            row = i // cols
            col = i % cols
            album_widget = AlbumWidget(record, self.parent_window, is_library=True)
            self.albums_layout.addWidget(album_widget, row, col)
    
    def clear_library(self):
        reply = QMessageBox.question(self, 'Confirm Clear', 
                                   'Are you sure you want to clear all library items?',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.clear_library()
            self.db.save()
            self.refresh_library()


class WishlistWidget(QWidget):
    """Wishlist tab widget"""
    
    def __init__(self, db, parent_window):
        super().__init__()
        self.db = db
        self.parent_window = parent_window
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Add album section
        add_section = QGroupBox("Add Album to Wishlist")
        add_layout = QHBoxLayout()
        
        self.uri_input = QLineEdit()
        self.uri_input.setPlaceholderText("Spotify Album URI or URL...")
        add_layout.addWidget(self.uri_input)
        
        add_btn = QPushButton("Add to Wishlist")
        add_btn.clicked.connect(self.add_to_wishlist)
        add_layout.addWidget(add_btn)
        
        add_section.setLayout(add_layout)
        layout.addWidget(add_section)
        
        # Clear button
        clear_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear All Wishlist")
        clear_btn.clicked.connect(self.clear_wishlist)
        clear_layout.addWidget(clear_btn)
        clear_layout.addStretch()
        layout.addLayout(clear_layout)
        
        # Albums grid
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.albums_layout = QGridLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        
        layout.addWidget(self.scroll_area)
        
        self.setLayout(layout)
        self.refresh_wishlist()
    
    def add_to_wishlist(self):
        uri = self.uri_input.text().strip()
        if not uri:
            QMessageBox.warning(self, 'Error', 'Please enter a Spotify URI or URL.')
            return
        
        try:
            # Convert URL to URI if needed
            if "http" in uri:
                uri = "spotify:album:" + uri[uri.index("album/") + 6:uri.index("?")]
            
            record = Record(uri)
            self.db.add_to_wishlist(record)
            self.db.save()
            
            self.uri_input.clear()
            self.refresh_wishlist()
            
            QMessageBox.information(self, 'Success', f"Added '{record.name}' by {record.artist} to wishlist!")
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Error adding album: {str(e)}")
    
    def refresh_wishlist(self):
        # Clear existing widgets
        for i in reversed(range(self.albums_layout.count())):
            child = self.albums_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not self.db.wishlist:
            no_albums_label = QLabel("Your wishlist is empty. Add some albums!")
            no_albums_label.setAlignment(Qt.AlignCenter)
            self.albums_layout.addWidget(no_albums_label, 0, 0)
            return
        
        # Sort by artist
        wishlist_list = list(self.db.wishlist)
        wishlist_list.sort(key=lambda x: x.artist)
        
        # Add albums to grid
        cols = 4
        for i, record in enumerate(wishlist_list):
            row = i // cols
            col = i % cols
            album_widget = AlbumWidget(record, self.parent_window, is_library=False)
            self.albums_layout.addWidget(album_widget, row, col)
    
    def clear_wishlist(self):
        reply = QMessageBox.question(self, 'Confirm Clear', 
                                   'Are you sure you want to clear all wishlist items?',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.clear_wishlist()
            self.db.save()
            self.refresh_wishlist()


class MusicVaultWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("MusicVault")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("MusicVault")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Stats tab
        self.stats_widget = StatsWidget(self.db)
        self.tab_widget.addTab(self.stats_widget, "📊 Statistics")
        
        # Library tab
        self.library_widget = LibraryWidget(self.db, self)
        self.tab_widget.addTab(self.library_widget, "📚 Library")
        
        # Wishlist tab
        self.wishlist_widget = WishlistWidget(self.db, self)
        self.tab_widget.addTab(self.wishlist_widget, "⭐ Wishlist")
        
        layout.addWidget(self.tab_widget)
    
    def refresh_current_tab(self):
        """Refresh the currently active tab"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index == 0:  # Stats
            # Remove and recreate stats widget
            self.tab_widget.removeTab(0)
            self.stats_widget = StatsWidget(self.db)
            self.tab_widget.insertTab(0, self.stats_widget, "📊 Statistics")
            self.tab_widget.setCurrentIndex(0)
        elif current_index == 1:  # Library
            self.library_widget.refresh_library()
        elif current_index == 2:  # Wishlist
            self.wishlist_widget.refresh_wishlist()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = MusicVaultWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
