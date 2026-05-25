"""
Ana Pencere Bileşeni.
Ana LlamaTray uygulamasının QMainWindow tabanlı penceresini içerir.
"""

import os
import webbrowser
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QSystemTrayIcon, QMenu, QAction, QLabel, QFrame,
    QProgressBar
)
from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtCore import QTimer


class LlamaTrayMainWindow(QMainWindow):
    """Ana pencere - menü ve temel butonları içerir"""
    
    def __init__(self, system_monitor, translations_func=None, icon_path=None):
        """
        Args:
            system_monitor: SystemMonitor instance
            translations_func: Çeviri fonksiyonu (get_translated metodu)
            icon_path: İkon yolu
        """
        super().__init__()
        self.system_monitor = system_monitor
        self.translations_func = translations_func
        self.icon_path = icon_path
        
        self._init_ui()
    
    def _init_ui(self):
        """UI'yi başlat"""
        # Varsayılan ikon
        self.default_icon = QIcon(self.icon_path) if self.icon_path else QIcon()
        
        # Log penceresi
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setFixedHeight(100)
        
        # Butonlar
        self.browse_button = QPushButton(self.get_translated("button_model_select", "Model Seç"))
        self.start_server_button = QPushButton(self.get_translated("button_start_server", "Sunucuyu Başlat"))
        self.stop_server_button = QPushButton(self.get_translated("button_stop_server", "Sunucuyu Durdur"))
        self.open_web_ui_button = QPushButton(self.get_translated("button_open_web_ui", "Web Arayüzünü Aç"))
        self.open_web_ui_button.setEnabled(False)  # Başlangıçta devre dışı
        
        # Dil seçimi ve Uygulama Hakkında butonu (sağ alt köşede, yan yana)
        self.language_combo = QComboBox()
        self.language_combo.addItems([self.get_translated("tr_language", "🇹🇷 Türkçe"), self.get_translated("en_language", "🇬🇧 English")])
        self.language_combo.setCurrentIndex(0)  # Varsayılan Türkçe
        self.language_combo.setFixedHeight(28)
        
        self.about_button = QPushButton(self.get_translated("about_button", "ℹ️ Uygulama Hakkında"))
        self.about_button.setFixedHeight(28)
        
        # Dil seçimi ve about butonu için container layout
        self.bottom_container = QHBoxLayout()
        self.bottom_container.addWidget(self.language_combo)
        self.bottom_container.addWidget(self.about_button)
        self.bottom_container.addStretch()
        
        # Ana layout
        layout = QVBoxLayout()
        layout.addWidget(self.log_window)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.start_server_button)
        layout.addWidget(self.stop_server_button)
        layout.addWidget(self.open_web_ui_button)
        layout.addLayout(self.bottom_container)
        
        # Sistem monitörü bilgilerini ekle
        monitor_frame = QFrame()
        monitor_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        monitor_layout = QVBoxLayout()
        
        self.cpu_label = QLabel("CPU Kullanımı: %0")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)
        
        self.ram_label = QLabel("RAM Kullanımı: %0")
        self.ram_progress = QProgressBar()
        self.ram_progress.setRange(0, 100)
        self.ram_progress.setValue(0)
        
        self.gpu_label = QLabel("GPU Kullanımı: %0")
        self.gpu_progress = QProgressBar()
        self.gpu_progress.setRange(0, 100)
        self.gpu_progress.setValue(0)
        
        self.vram_label = QLabel("VRAM Kullanımı: %0")
        self.vram_progress = QProgressBar()
        self.vram_progress.setRange(0, 100)
        self.vram_progress.setValue(0)
        
        # GPU ve VRAM desteği kontrolü
        if not self.system_monitor.gpu_available:
            self.gpu_label.setText(self.get_translated("label_gpu_not_supported", "GPU: Desteklenmiyor"))
            self.gpu_progress.setVisible(False)
        if not self.system_monitor.vram_available:
            self.vram_label.setText(self.get_translated("label_vram_not_supported", "VRAM: Desteklenmiyor"))
            self.vram_progress.setVisible(False)
        
        monitor_layout.addWidget(self.cpu_label)
        monitor_layout.addWidget(self.cpu_progress)
        monitor_layout.addWidget(self.ram_label)
        monitor_layout.addWidget(self.ram_progress)
        monitor_layout.addWidget(self.gpu_label)
        monitor_layout.addWidget(self.gpu_progress)
        monitor_layout.addWidget(self.vram_label)
        monitor_layout.addWidget(self.vram_progress)
        
        monitor_frame.setLayout(monitor_layout)
        layout.addWidget(monitor_frame)
        
        # Ana widget ve layout
        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)
        
        # Pencere başlığı
        self.setWindowTitle(f"{self.get_translated('app_name', '🦙 LlamaTray')} {self.get_translated('version', 'v1.0.2')}")
        self.setGeometry(100, 100, 450, 650)
        
        # Pencere ikonu
        if not self.default_icon.isNull():
            self.setWindowIcon(self.default_icon)
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        if self.translations_func:
            return self.translations_func(key, default)
        return default
    
    def get_widgets(self):
        """Tüm widget'ları döndür (dışarıdan erişim için)"""
        return {
            'log_window': self.log_window,
            'browse_button': self.browse_button,
            'start_server_button': self.start_server_button,
            'stop_server_button': self.stop_server_button,
            'open_web_ui_button': self.open_web_ui_button,
            'language_combo': self.language_combo,
            'about_button': self.about_button,
            'cpu_label': self.cpu_label,
            'cpu_progress': self.cpu_progress,
            'ram_label': self.ram_label,
            'ram_progress': self.ram_progress,
            'gpu_label': self.gpu_label,
            'gpu_progress': self.gpu_progress,
            'vram_label': self.vram_label,
            'vram_progress': self.vram_progress,
        }


class LlamaTraySystemTray(QSystemTrayIcon):
    """Sistem tepsisi ikonu ve menüsü"""
    
    def __init__(self, translations_func=None, icon_path=None):
        """
        Args:
            translations_func: Çeviri fonksiyonu (get_translated metodu)
            icon_path: İkon yolu
        """
        super().__init__()
        self.translations_func = translations_func
        self.icon_path = icon_path
        
        self._init_ui()
    
    def _init_ui(self):
        """UI'yi başlat"""
        # Varsayılan ikon
        self.default_icon = QIcon(self.icon_path) if self.icon_path else QIcon()
        
        if not self.default_icon.isNull():
            self.setIcon(self.default_icon)
        self.setVisible(True)
        
        # Menü
        self.menu = QMenu()
        
        self.browse_action = QAction(self.get_translated("menu_browse", "Göz Al"), self)
        self.browse_action.triggered.connect(lambda: None)  # Ana sınıftan bağlanacak
        self.menu.addAction(self.browse_action)
        
        self.start_server_action = QAction(self.get_translated("menu_start_server", "Sunucuyu Başlat"), self)
        self.start_server_action.triggered.connect(lambda: None)  # Ana sınıftan bağlanacak
        self.menu.addAction(self.start_server_action)
        
        self.stop_server_action = QAction(self.get_translated("menu_stop_server", "Sunucuyu Durdur"), self)
        self.stop_server_action.triggered.connect(lambda: None)  # Ana sınıftan bağlanacak
        self.menu.addAction(self.stop_server_action)
        
        self.menu.addSeparator()
        
        self.about_action = QAction(self.get_translated("menu_about", "Hakkında / About"), self)
        self.about_action.triggered.connect(lambda: None)  # Ana sınıftan bağlanacak
        self.menu.addAction(self.about_action)
        
        self.setContextMenu(self.menu)
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        if self.translations_func:
            return self.translations_func(key, default)
        return default
