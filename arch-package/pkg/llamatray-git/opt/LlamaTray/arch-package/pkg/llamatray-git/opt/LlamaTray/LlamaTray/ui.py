"""
PyQt6 kullanıcı arayüzü modülü.
LlamaTray ana penceresi ve sistem tepsisi işlevlerini içerir.
"""

import os
import json
import atexit
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QFileDialog, QTextEdit,
    QPushButton, QVBoxLayout, QWidget, QProgressBar, QLabel, QFrame,
    QSpinBox, QComboBox, QLineEdit, QGroupBox, QFormLayout, QDialog,
    QDialogButtonBox
)
from PyQt6.QtGui import QIcon, QAction, QIntValidator, QDesktopServices
from PyQt6.QtCore import QTimer, QUrl

from .monitor import SystemMonitor
from .server import LlamaServerManager


# Global referans - atexit için
_tray_instance = None

# İkon yolu - sadece varsayılan ikon
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(CURRENT_DIR, "assets", "icon.png")

if not os.path.exists(ICON_PATH):
    print(f"!!! DIKKAT: İkon bulunamadi, aranan konum: {ICON_PATH}")


def cleanup_on_exit():
    """Uygulama çıkışında tüm süreçleri temizle"""
    global _tray_instance
    if _tray_instance is not None:
        _tray_instance.cleanup_server_process()


class LlamaTray(QSystemTrayIcon):
    """Ana LlamaTray uygulaması"""

    def __init__(self):
        super().__init__()

        # Varsayılan ikon
        self.default_icon = QIcon(ICON_PATH)

        # Sunucu yöneticisi
        self.server_manager = LlamaServerManager(log_callback=self.log)

        # Sistem monitörü
        self.system_monitor = SystemMonitor()

        # Sistem tepsisi ikonu
        self.setIcon(self.default_icon)
        self.setVisible(True)

        # Menü
        self.menu = QMenu()
        self.browse_action = QAction("Göz At", self)
        self.browse_action.triggered.connect(self.browse_file)
        self.menu.addAction(self.browse_action)

        self.start_server_action = QAction("Sunucuyu Başlat", self)
        self.start_server_action.triggered.connect(self.start_server)
        self.menu.addAction(self.start_server_action)

        self.stop_server_action = QAction("Sunucuyu Durdur", self)
        self.stop_server_action.triggered.connect(self.stop_server)
        self.menu.addAction(self.stop_server_action)

        self.menu.addSeparator()

        self.about_action = QAction("Hakkında / About", self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.menu.addAction(self.about_action)

        self.setContextMenu(self.menu)

        # Log penceresi
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setFixedHeight(100)

        # Butonlar
        self.browse_button = QPushButton("Model Seç")
        self.browse_button.clicked.connect(self.browse_file)

        self.start_server_button = QPushButton("Sunucuyu Başlat")
        self.start_server_button.clicked.connect(self.start_server)

        self.stop_server_button = QPushButton("Sunucuyu Durdur")
        self.stop_server_button.clicked.connect(self.stop_server)

        # CPU ve RAM için progress barlar
        self.cpu_label = QLabel("CPU Kullanımı: %0")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)

        self.ram_label = QLabel("RAM Kullanımı: %0")
        self.ram_progress = QProgressBar()
        self.ram_progress.setRange(0, 100)
        self.ram_progress.setValue(0)

        # GPU ve VRAM için progress barlar
        self.gpu_label = QLabel("GPU Kullanımı: %0")
        self.gpu_progress = QProgressBar()
        self.gpu_progress.setRange(0, 100)
        self.gpu_progress.setValue(0)

        self.vram_label = QLabel("VRAM Kullanımı: %0")
        self.vram_progress = QProgressBar()
        self.vram_progress.setRange(0, 100)
        self.vram_progress.setValue(0)

        if not self.system_monitor.gpu_available:
            self.gpu_label.setText("GPU: Desteklenmiyor")
            self.gpu_progress.setVisible(False)
        if not self.system_monitor.vram_available:
            self.vram_label.setText("VRAM: Desteklenmiyor")
            self.vram_progress.setVisible(False)

        # ============ GELİŞMİŞ AYARLAR ============
        self.gpu_layers_spinbox = QSpinBox()
        self.gpu_layers_spinbox.setRange(0, 200)
        self.gpu_layers_spinbox.setValue(99)
        self.gpu_layers_spinbox.setSuffix(" katman")

        self.context_size_combobox = QComboBox()
        self.context_size_combobox.addItems(["2048", "4096", "8192", "16384", "32768", "65536", "131072"])
        self.context_size_combobox.setCurrentText("32768")
        self.context_size_combobox.setEditable(True)
        self.context_size_combobox.setValidator(QIntValidator(512, 1000000))

        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1024, 65535)
        self.port_spinbox.setValue(8080)

        self.extra_params_lineedit = QLineEdit()
        self.extra_params_lineedit.setPlaceholderText("Örn: -t 8 --flash-attn")

        # Gelişmiş Ayarlar GroupBox
        advanced_group = QGroupBox("Gelişmiş Ayarlar")
        advanced_layout = QFormLayout()
        advanced_layout.addRow("GPU Katmanları:", self.gpu_layers_spinbox)
        advanced_layout.addRow("Context Boyutu:", self.context_size_combobox)
        advanced_layout.addRow("Port:", self.port_spinbox)
        advanced_layout.addRow("Ek Parametreler:", self.extra_params_lineedit)
        advanced_group.setLayout(advanced_layout)

        # Ana layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.log_window)
        self.layout.addWidget(self.browse_button)
        self.layout.addWidget(self.start_server_button)
        self.layout.addWidget(self.stop_server_button)
        self.layout.addWidget(advanced_group)

        # Sistem monitörü bilgilerini ekle
        monitor_frame = QFrame()
        monitor_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        monitor_layout = QVBoxLayout()
        monitor_layout.addWidget(self.cpu_label)
        monitor_layout.addWidget(self.cpu_progress)
        monitor_layout.addWidget(self.ram_label)
        monitor_layout.addWidget(self.ram_progress)
        monitor_layout.addWidget(self.gpu_label)
        monitor_layout.addWidget(self.gpu_progress)
        monitor_layout.addWidget(self.vram_label)
        monitor_layout.addWidget(self.vram_progress)
        monitor_frame.setLayout(monitor_layout)
        self.layout.addWidget(monitor_frame)

        # Uygulama Hakkında butonu (en altta, ince ve şık)
        self.about_button = QPushButton("ℹ️ Uygulama Hakkında")
        self.about_button.clicked.connect(self.show_about_dialog)
        self.about_button.setFixedHeight(28)
        self.layout.addWidget(self.about_button)

        # Ana pencere
        self.window = QWidget()
        self.window.setLayout(self.layout)
        self.window.setWindowTitle("LlamaTray")
        self.window.setGeometry(100, 100, 450, 650)

        # Pencere kapatıldığında (X butonu) sunucuyu otomatik durdur
        original_close_event = self.window.closeEvent
        def window_close_event(event):
            self.stop_server()
            original_close_event(event)
        self.window.closeEvent = window_close_event

        # Pencere ikonu
        self.window.setWindowIcon(self.default_icon)

        # Timer (sadece sistem monitörü için)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_monitor)

        self.model_path = None

        # Global referansı ayarla (atexit için)
        global _tray_instance
        _tray_instance = self

        # Tüm ayarları yükle
        self.load_config()

    def show_about_dialog(self):
        """Hakkında penceresini göster"""
        dialog = QDialog(self.window)
        dialog.setWindowTitle("Hakkında / About")
        dialog.setWindowIcon(self.default_icon)
        dialog.setFixedSize(420, 380)
        dialog.setModal(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # HTML içerik
        html_content = QLabel()
        html_content.setWordWrap(True)
        html_content.setOpenExternalLinks(True)
        html_content.setText(
            "<h3 style='color: #2980b9;'>🦙 LlamaTray v1.0.0</h3>"
            "<p><b>Geliştirici:</b> Fatih Durdu</p>"
            "<p>Linux (Arch Linux / CachyOS) sistemler için minimalist, "
            "hafif ve zombi süreç önleme mekanizmasına sahip PyQt6 tabanlı "
            "Llama.cpp (llama-server) yönetim aracı.</p>"
            "<hr>"
            "<p>🌐 <a href='https://fatihdurdu.xyz'>Kişisel Web Sitesi (fatihdurdu.xyz)</a></p>"
            "<p>🐙 <a href='https://github.com/DolbyDAX2'>GitHub Profili (DolbyDAX2)</a></p>"
            "<p>📦 <a href='https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray'>Proje Gitea Deposu</a></p>"
        )
        layout.addWidget(html_content)

        layout.addStretch()

        # Kapat butonu
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        dialog.exec()

    def get_config_path(self):
        """Yapılandırma dosyası yolunu döndür"""
        config_dir = os.path.join(os.path.expanduser("~"), ".llamatray")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return os.path.join(config_dir, "config.json")

    def save_config(self):
        """Tüm ayarları kaydet"""
        config_path = self.get_config_path()
        config = {
            "model_path": self.model_path,
            "gpu_layers": self.gpu_layers_spinbox.value(),
            "context_size": int(self.context_size_combobox.currentText()),
            "port": self.port_spinbox.value(),
            "extra_params": self.extra_params_lineedit.text()
        }
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            self.log("✓ Ayarlar başarıyla kaydedildi.")
        except PermissionError as e:
            self.log(f"⚠ Ayarlar kaydedilemedi: Dosya yazma izni yok. Lütfen dosya izinlerini kontrol edin.")
        except OSError as e:
            self.log(f"⚠ Ayarlar kaydedilemedi: Disk hatası ({e}). Lütfen disk alanını kontrol edin.")
        except Exception as e:
            self.log(f"⚠ Ayarlar kaydedilemedi: Beklenmeyen hata ({e}).")

    def load_config(self):
        """Tüm ayarları yükle"""
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)

                # Model yolu
                self.model_path = config.get("model_path")
                if self.model_path:
                    self.log(f"✓ Kaydedilmiş model yolu yüklendi: {self.model_path}")

                # GPU katmanları
                gpu_layers = config.get("gpu_layers")
                if gpu_layers is not None:
                    self.gpu_layers_spinbox.setValue(gpu_layers)

                # Context boyutu
                context_size = config.get("context_size")
                if context_size is not None:
                    context_str = str(context_size)
                    if self.context_size_combobox.findText(context_str) >= 0:
                        self.context_size_combobox.setCurrentText(context_str)

                # Port
                port = config.get("port")
                if port is not None:
                    self.port_spinbox.setValue(port)

                # Ek parametreler
                extra_params = config.get("extra_params")
                if extra_params is not None:
                    self.extra_params_lineedit.setText(extra_params)

                self.log("✓ Tüm ayarlar başarıyla yüklendi.")

            except json.JSONDecodeError as e:
                self.log(f"⚠ Ayarlar yüklenemedi: Yapılandırma dosyası bozuk ({e}). Varsayılan ayarlar kullanılacak.")
            except PermissionError as e:
                self.log(f"⚠ Ayarlar yüklenemedi: Dosya okuma izni yok. Lütfen dosya izinlerini kontrol edin.")
            except Exception as e:
                self.log(f"⚠ Ayarlar yüklenemedi: Beklenmeyen hata ({e}). Varsayılan ayarlar kullanılacak.")
        else:
            self.log("ℹ Kaydedilmiş yapılandırma bulunamadı. Varsayılan ayarlar kullanılıyor.")

    def browse_file(self):
        """Model dosyası seç"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Bilgisayarınızdan .gguf model dosyasını seçin",
            "",
            "GGUF Files (*.gguf)"
        )
        if file_path:
            self.model_path = file_path
            self.save_config()
            self.log(f"Seçilen dosya: {file_path}")

    def start_server(self):
        """Sunucuyu başlat"""
        gpu_layers = self.gpu_layers_spinbox.value()
        context_size = int(self.context_size_combobox.currentText())
        port = self.port_spinbox.value()
        extra_params = self.extra_params_lineedit.text().strip()

        success = self.server_manager.start_server(
            model_path=self.model_path,
            gpu_layers=gpu_layers,
            context_size=context_size,
            port=port,
            extra_params=extra_params
        )

        if success:
            self.save_config()
            self.timer.start(1000)

    def stop_server(self):
        """Sunucuyu durdur"""
        self.server_manager.stop_server()
        self.timer.stop()

    def cleanup_server_process(self):
        """Sunucu sürecini temizle"""
        self.server_manager.cleanup_server_process()

    def update_system_monitor(self):
        """Sistem monitörünü güncelle"""
        # CPU
        cpu_usage = self.system_monitor.get_cpu_usage()
        self.cpu_label.setText(f"CPU Kullanımı: %{cpu_usage:.1f}")
        self.cpu_progress.setValue(int(cpu_usage))

        # RAM
        ram_usage = self.system_monitor.get_ram_usage()
        self.ram_label.setText(f"RAM Kullanımı: %{ram_usage:.1f}")
        self.ram_progress.setValue(int(ram_usage))

        # GPU
        if self.system_monitor.gpu_available:
            gpu_usage = self.system_monitor.get_gpu_usage()
            if gpu_usage is not None:
                self.gpu_label.setText(f"GPU Kullanımı: %{gpu_usage:.1f}")
                self.gpu_progress.setValue(int(gpu_usage))

        # VRAM
        if self.system_monitor.vram_available:
            vram_usage = self.system_monitor.get_vram_usage()
            if vram_usage is not None:
                self.vram_label.setText(f"VRAM Kullanımı: %{vram_usage:.1f}")
                self.vram_progress.setValue(int(vram_usage))

    def log(self, message):
        """Log mesajı ekle"""
        self.log_window.append(message)

    def closeEvent(self, event):
        """Uygulama kapanırken sunucuyu da otomatik kapat"""
        print("Uygulama kapatılıyor, sunucu durduruluyor...")
        if hasattr(self, 'server_manager') and self.server_manager:
            self.server_manager.stop_server()
        event.accept()


# atexit ile temizlik fonksiyonunu kaydet
atexit.register(cleanup_on_exit)