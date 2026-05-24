"""
PyQt6 kullanıcı arayüzü modülü.
LlamaTray ana penceresi ve sistem tepsisi işlevlerini içerir.
"""

import os
import sys
import json
import atexit
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QFileDialog, QTextEdit,
    QPushButton, QVBoxLayout, QWidget, QProgressBar, QLabel, QFrame,
    QSpinBox, QComboBox, QLineEdit, QGroupBox, QFormLayout, QDialog,
    QDialogButtonBox, QInputDialog, QHBoxLayout
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


def cleanup_tray_icon():
    """Sistem tepsisindeki ikonları temizle - uygulama crash olsa bile çalıştırılmalı"""
    global _tray_instance
    try:
        if _tray_instance is not None:
            # Tray ikonunu gizle (Wayland/KDE uyumluluğu)
            try:
                _tray_instance.hide()
            except Exception as e:
                pass
            
            # Tray ikonunu bellekten sil
            try:
                _tray_instance.deleteLater()
            except Exception as e:
                pass
            
            # Eğer context menu varsa onu da sil
            try:
                if hasattr(_tray_instance, 'menu') and _tray_instance.menu:
                    _tray_instance.menu.close()
                    _tray_instance.menu.deleteLater()
            except Exception:
                pass
    except Exception:
        pass
    finally:
        _tray_instance = None


def cleanup_on_exit():
    """Uygulama çıkışında tüm süreçleri ve tray ikonunu temizle"""
    global _tray_instance
    try:
        if _tray_instance is not None:
            # Sunucuyu kapat
            try:
                if hasattr(_tray_instance, 'cleanup_server_process'):
                    _tray_instance.cleanup_server_process()
            except Exception:
                pass
            
            # Tray ikonunu temizle
            cleanup_tray_icon()
    except Exception:
        pass


class LlamaTray(QSystemTrayIcon):
    """Ana LlamaTray uygulaması"""

    def __init__(self):
        super().__init__()

        # Varsayılan ikon
        self.default_icon = QIcon(ICON_PATH)

        # Sunucu yöneticisi
        self.server_manager = LlamaServerManager(log_callback=self.log)
        
        # Server state sinyallerini bağla
        self.server_manager.started.connect(self.on_server_started)
        self.server_manager.finished.connect(self.on_server_finished)
        self.server_manager.errorOccurred.connect(self.on_server_error)

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

        self.open_web_ui_button = QPushButton("Web Arayüzünü Aç")
        self.open_web_ui_button.clicked.connect(self.open_web_ui)
        self.open_web_ui_button.setEnabled(False)  # Başlangıçta devre dışı

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
        self.context_size_combobox.addItems(["16384", "32768", "65536", "131072", "262144"])
        self.context_size_combobox.setCurrentText("32768")
        # Combobox'ı editabl yap ama sadece dropdown listesi göster
        self.context_size_combobox.setEditable(True)
        self.context_size_combobox.setValidator(QIntValidator(512, 1000000))
        # Dropdown listesindeki öğelerin sırasını koru - ilk öğeyi varsayılan yap
        self.context_size_combobox.setCurrentIndex(0)

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

        # ============ PROFİL YÖNETİMİ ============
        profile_group = QGroupBox("Profil Yönetimi")
        profile_layout = QVBoxLayout()

        # Profil seçme combobox'ı
        profile_select_layout = QHBoxLayout()
        self.profile_combobox = QComboBox()
        self.profile_combobox.setMinimumHeight(28)
        self.profile_combobox.currentIndexChanged.connect(self.on_profile_selected)
        profile_select_layout.addWidget(self.profile_combobox, 1)

        # Profil butonları
        self.save_profile_button = QPushButton("💾 Profili Kaydet")
        self.save_profile_button.clicked.connect(self.save_current_profile)
        self.save_profile_button.setFixedHeight(28)

        self.update_profile_button = QPushButton("🔄 Profili Güncelle")
        self.update_profile_button.clicked.connect(self.update_selected_profile)
        self.update_profile_button.setFixedHeight(28)

        self.delete_profile_button = QPushButton("🗑 Profili Sil")
        self.delete_profile_button.clicked.connect(self.delete_selected_profile)
        self.delete_profile_button.setFixedHeight(28)

        profile_buttons_layout = QHBoxLayout()
        profile_buttons_layout.addWidget(self.save_profile_button)
        profile_buttons_layout.addWidget(self.update_profile_button)
        profile_buttons_layout.addWidget(self.delete_profile_button)

        profile_layout.addLayout(profile_select_layout)
        profile_layout.addLayout(profile_buttons_layout)
        profile_group.setLayout(profile_layout)

        # Ana layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.log_window)
        self.layout.addWidget(self.browse_button)
        self.layout.addWidget(self.start_server_button)
        self.layout.addWidget(self.stop_server_button)
        self.layout.addWidget(self.open_web_ui_button)
        self.layout.addWidget(advanced_group)
        self.layout.addWidget(profile_group)

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
            try:
                self.log("=" * 60)
                self.log("🚪 Pencere kapanıyor, sunucu durdurması yapılıyor...")
                self.stop_server()
                self.log("✓ Uygulama kapatılıyor.")
            except Exception as e:
                self.log(f"⚠ Kapanış sırasında hata: {e}")
            finally:
                original_close_event(event)
                # Pencere kapandığında tray'i de kapat
                try:
                    self.cleanup_tray()
                except Exception:
                    pass
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
        
        # QApplication signals bağla - uygulama çıkışında temizlik yap
        try:
            app = QApplication.instance()
            if app:
                app.aboutToQuit.connect(self.cleanup_tray)
        except Exception:
            pass

        # Tüm ayarları yükle
        self.load_config()

        # Profil listesini yükle
        self.refresh_profile_combobox()

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
            "<h3 style='color: #2980b9;'>🦙 LlamaTray v1.0.2</h3>"
            "<p><b>Geliştirici:</b> Fatih Durdu</p>"
            "<p>Linux (Arch Linux / CachyOS) sistemler için minimalist, "
            "hafif ve zombi süreç önleme mekanizmasına sahip PyQt6 tabanlı "
            "Llama.cpp (llama-server) yönetim aracı.</p>"
            "<hr>"
            "<p>🌐 <a href='https://fatihdurdu.xyz/llamatray'>Kişisel Web Sitesi (fatihdurdu.xyz/llamatray)</a></p>"
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

    def get_config_dir(self):
        """Yapılandırma dizinini döndür (oluşturur)"""
        config_dir = os.path.join(os.path.expanduser("~"), ".llamatray")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def get_config_path(self):
        """Yapılandırma dosyası yolunu döndür"""
        return os.path.join(self.get_config_dir(), "config.json")

    def get_profiles_path(self):
        """Profil JSON dosyasının yolunu döndür"""
        return os.path.join(self.get_config_dir(), "profiles.json")

    def load_profiles(self):
        """Kayıtlı profilleri JSON'dan yükle"""
        profiles_path = self.get_profiles_path()
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                self.log(f"⚠ Profiller yüklenemedi: {e}")
        return {}

    def save_profiles(self, profiles):
        """Profilleri JSON dosyasına yaz"""
        profiles_path = self.get_profiles_path()
        try:
            with open(profiles_path, "w") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ Profiller kaydedilemedi: {e}")

    def refresh_profile_combobox(self):
        """Combobox'ı kayıtlı profillerle doldur, mevcut seçimi koru"""
        # Mevcut seçimi hatırla
        current_name = self.profile_combobox.currentText()

        self.profile_combobox.blockSignals(True)
        self.profile_combobox.clear()

        profiles = self.load_profiles()
        if profiles:
            self.profile_combobox.addItems(sorted(profiles.keys()))
            # Daha önce seçili olan varsa onu seç
            idx = self.profile_combobox.findText(current_name)
            if idx >= 0:
                self.profile_combobox.setCurrentIndex(idx)
        else:
            self.profile_combobox.addItem("(Profil yok)")

        self.profile_combobox.blockSignals(False)

    def get_current_form_values(self):
        """Formdaki tüm alanların değerlerini dict olarak döndür"""
        try:
            context_size = int(self.context_size_combobox.currentText())
        except (ValueError, TypeError):
            context_size = 32768
        return {
            "gpu_layers": self.gpu_layers_spinbox.value(),
            "context_size": context_size,
            "port": self.port_spinbox.value(),
            "extra_args": self.extra_params_lineedit.text().strip()
        }

    def apply_profile_values(self, profile_data):
        """Profil verisini form alanlarına uygula - combobox'ta sadece hazır seçenekler görünür"""
        # GPU katmanları
        gpu_layers = profile_data.get("gpu_layers")
        if gpu_layers is not None:
            try:
                self.gpu_layers_spinbox.setValue(int(gpu_layers))
            except (ValueError, TypeError):
                pass

        # Context boyutu - sadece hazır seçenekler gösterilir, custom değer combobox'a eklenmez
        context_size = profile_data.get("context_size")
        if context_size is not None:
            try:
                context_str = str(int(context_size))
                # Combobox'ta bu değer var mı kontrol et
                if self.context_size_combobox.findText(context_str) >= 0:
                    self.context_size_combobox.setCurrentText(context_str)
                else:
                    # Eğer listede yoksa, combobox'ı sıfırla ve sadece hazır seçenekleri ekle
                    self.context_size_combobox.blockSignals(True)
                    self.context_size_combobox.clear()
                    for item in ["16384", "32768", "65536", "131072", "262144"]:
                        self.context_size_combobox.addItem(item)
                    # Profilin custom değerini ekle (çünkü profil tarafından yükleniyor)
                    self.context_size_combobox.addItem(context_str)
                    self.context_size_combobox.setCurrentText(context_str)
                    self.context_size_combobox.blockSignals(False)
            except (ValueError, TypeError):
                pass

        # Port
        port = profile_data.get("port")
        if port is not None:
            try:
                self.port_spinbox.setValue(int(port))
            except (ValueError, TypeError):
                pass

        # Ek parametreler
        extra_args = profile_data.get("extra_args")
        if extra_args is not None:
            self.extra_params_lineedit.setText(str(extra_args))

    def save_current_profile(self):
        """Mevcut form değerlerini bir profile kaydet"""
        # Kullanıcıdan profil adı iste
        profile_name, ok = QInputDialog.getText(
            self.window,
            "Profili Kaydet",
            "Profil adı:",
            text=""
        )
        if not ok or not profile_name:
            return

        profile_name = profile_name.strip()
        if not profile_name:
            self.log("⚠ Profil adı boş olamaz.")
            return

        # Mevcut değerleri al
        values = self.get_current_form_values()
        values["profile_name"] = profile_name

        # Profili kaydet (aynı isim varsa üzerine yaz)
        profiles = self.load_profiles()
        is_update = profile_name in profiles
        profiles[profile_name] = values
        self.save_profiles(profiles)

        # Combobox'ı güncelle ve yeni profili seç
        self.refresh_profile_combobox()
        idx = self.profile_combobox.findText(profile_name)
        if idx >= 0:
            self.profile_combobox.setCurrentIndex(idx)

        if is_update:
            self.log(f"✓ Profil güncellendi: '{profile_name}'")
        else:
            self.log(f"✓ Profil kaydedildi: '{profile_name}'")

    def on_profile_selected(self, index):
        """Combobox'tan profil seçildiğinde form alanlarını doldur"""
        if index < 0:
            return

        profile_name = self.profile_combobox.currentText()
        if not profile_name or profile_name == "(Profil yok)":
            return

        profiles = self.load_profiles()
        profile_data = profiles.get(profile_name)
        if profile_data:
            self.apply_profile_values(profile_data)
            self.log(f"✓ Profil yüklendi: '{profile_name}'")

    def update_selected_profile(self):
        """Seçili profili güncelle - ekrandaki değerlerle mevcut profili yenile"""
        profile_name = self.profile_combobox.currentText()
        if not profile_name or profile_name == "(Profil yok)":
            self.log("⚠ Güncellenecek profil seçilmedi.")
            return

        # Mevcut değerleri al
        values = self.get_current_form_values()
        
        # Profili güncelle
        profiles = self.load_profiles()
        if profile_name in profiles:
            profiles[profile_name] = values
            self.save_profiles(profiles)
            self.log(f"✓ Profil '{profile_name}' güncellendi.")
        else:
            self.log(f"⚠ Profil '{profile_name}' bulunamadı. Lütfen önce kaydedin.")

    def delete_selected_profile(self):
        """Seçili profili sil"""
        profile_name = self.profile_combobox.currentText()
        if not profile_name or profile_name == "(Profil yok)":
            self.log("⚠ Silinecek profil seçilmedi.")
            return

        # Onay sor
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.window,
            "Profili Sil",
            f"'{profile_name}' profilini silmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        profiles = self.load_profiles()
        if profile_name in profiles:
            del profiles[profile_name]
            self.save_profiles(profiles)
            self.refresh_profile_combobox()
            self.log(f"✓ Profil silindi: '{profile_name}'")

    def save_config(self):
        """Tüm ayarları kaydet - hem config.json hem de mevcut profil"""
        try:
            config_path = self.get_config_path()
            
            # Context size'ı güvenli bir şekilde dönüştür
            try:
                context_size = int(self.context_size_combobox.currentText())
            except (ValueError, TypeError):
                self.log(f"⚠ Context size dönüştürülemedi, varsayılan 32768 kullanılıyor")
                context_size = 32768
            
            config = {
                "model_path": self.model_path,
                "gpu_layers": self.gpu_layers_spinbox.value(),
                "context_size": context_size,
                "port": self.port_spinbox.value(),
                "extra_params": self.extra_params_lineedit.text()
            }
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            self.log("✓ Ayarlar başarıyla kaydedildi.")
            
            # Not: Mevcut aktif profil otomatik güncellenmedi.
            # Kullanıcı profil değişikliklerini "Profili Güncelle" butonu ile manuel yapmalıdır.
        except PermissionError:
            self.log(f"❌ Hata: Ayarlar kaydedilemedi - Dosya yazma izni yok. (Dosya: {config_path})")
        except OSError as e:
            self.log(f"❌ Hata: Ayarlar kaydedilemedi - Disk hatası: {e}")
        except Exception as e:
            self.log(f"❌ Hata: Ayarlar kaydedilemedi - {type(e).__name__}: {e}")

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
                    self.log(f"✓ Model yolu yüklendi: {self.model_path}")

                # GPU katmanları
                gpu_layers = config.get("gpu_layers")
                if gpu_layers is not None:
                    try:
                        self.gpu_layers_spinbox.setValue(int(gpu_layers))
                    except (ValueError, TypeError):
                        self.log("⚠ GPU katmanları değeri geçersiz, varsayılan kullanılıyor")

                # Context boyutu - combobox'ta sadece hazır seçenekler görünür ama config'den gelen custom değer eklenir
                context_size = config.get("context_size")
                if context_size is not None:
                    try:
                        context_str = str(int(context_size))
                        # Mevcut combobox'ta bu değer var mı kontrol et
                        if self.context_size_combobox.findText(context_str) >= 0:
                            self.context_size_combobox.setCurrentText(context_str)
                        else:
                            # Eğer listede yoksa, combobox'ı sıfırla ve sadece hazır seçenekleri ekle
                            self.context_size_combobox.blockSignals(True)
                            self.context_size_combobox.clear()
                            for item in ["16384", "32768", "65536", "131072", "262144"]:
                                self.context_size_combobox.addItem(item)
                            # Config'den gelen custom değeri ekle
                            self.context_size_combobox.addItem(context_str)
                            self.context_size_combobox.setCurrentText(context_str)
                            self.context_size_combobox.blockSignals(False)
                    except (ValueError, TypeError):
                        self.log("⚠ Context boyutu değeri geçersiz, varsayılan kullanılıyor")

                # Port
                port = config.get("port")
                if port is not None:
                    try:
                        self.port_spinbox.setValue(int(port))
                    except (ValueError, TypeError):
                        self.log("⚠ Port değeri geçersiz, varsayılan kullanılıyor")

                # Ek parametreler
                extra_params = config.get("extra_params")
                if extra_params is not None:
                    self.extra_params_lineedit.setText(str(extra_params))

                self.log("✓ Yapılandırma başarıyla yüklendi.")

            except json.JSONDecodeError as e:
                self.log(f"❌ Hata: Yapılandırma dosyası geçersiz JSON - {e}")
            except PermissionError:
                self.log(f"❌ Hata: Yapılandırma dosyası okunamadı - İzin reddedildi")
            except Exception as e:
                self.log(f"❌ Hata: Yapılandırma yüklenirken hata - {type(e).__name__}: {e}")
        else:
            self.log("ℹ Kaydedilmiş yapılandırma bulunamadı. Varsayılan ayarlar kullanılıyor.")

    def browse_file(self):
        """Model dosyası seç"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.window,
                "Bilgisayarınızdan .gguf model dosyasını seçin",
                "",
                "GGUF/GGML Files (*.gguf *.ggml);;Tüm Dosyalar (*.*)"
            )
            if file_path:
                if not os.path.exists(file_path):
                    self.log(f"❌ Hata: Seçilen dosya artık mevcut değil: {file_path}")
                    return
                
                self.model_path = file_path
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                self.log(f"✓ Model seçildi: {file_path}")
                self.log(f"  Dosya boyutu: {file_size_mb:.2f} MB")
                # Not: Model seçildiğinde otomatik config güncellemesi devre dışı bırakıldı
                # Kullanıcı istediğinde "Profili Güncelle" butonunu kullanarak manuel güncelleme yapabilir
        except Exception as e:
            self.log(f"❌ Hata: Model seçilirken hata - {type(e).__name__}: {e}")

    def start_server(self):
        """Sunucuyu başlat"""
        try:
            # Başlangıç kontrolleri
            gpu_layers = self.gpu_layers_spinbox.value()
            
            # Context size'ı kontrol et
            context_size_text = self.context_size_combobox.currentText()
            try:
                context_size = int(context_size_text)
            except ValueError:
                self.log(f"❌ Hata: Context size geçersiz sayı: {context_size_text}")
                return
            
            port = self.port_spinbox.value()
            extra_params = self.extra_params_lineedit.text().strip()

            # UI button'larını disable et işlem sırasında
            self.start_server_button.setEnabled(False)
            self.stop_server_button.setEnabled(False)
            self.browse_button.setEnabled(False)
            
            self.log("=" * 60)
            self.log("🚀 Sunucu başlatma işlemi başladı...")
            
            success = self.server_manager.start_server(
                model_path=self.model_path,
                gpu_layers=gpu_layers,
                context_size=context_size,
                port=port,
                extra_params=extra_params
            )

            if success:
                self.save_config()
                # Timer'ı başlat - sistem monitörünü güncelle
                self.timer.start(1000)
                # Web UI butonunu aktifleştir (başarıyla başlandıktan sonra on_started sinyali tetiklenecek)
                self.log("✓ Sunucu başlatma talebi kabul edildi. Yapılandırma kaydedildi.")
            else:
                self.log("❌ Sunucu başlatma başarısız oldu.")
                # Button'ları geri aktifleştir
                self.start_server_button.setEnabled(True)
                self.browse_button.setEnabled(True)
                
        except Exception as e:
            self.log(f"❌ Beklenmeyen hata (start_server): {type(e).__name__}: {e}")
            # Button'ları geri aktifleştir
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(True)
            self.browse_button.setEnabled(True)

    def stop_server(self):
        """Sunucuyu durdur"""
        try:
            self.log("🛑 Sunucu durdurma talebi gönderiliyor...")
            
            # Button'ları disable et
            self.stop_server_button.setEnabled(False)
            self.start_server_button.setEnabled(False)
            
            self.server_manager.stop_server()
            
            # Timer'ı durdur
            self.timer.stop()
            
            # Web UI butonunu devre dışı bırak
            self.open_web_ui_button.setEnabled(False)
            
            # Button'ları geri aktifleştir
            self.start_server_button.setEnabled(True)
            self.browse_button.setEnabled(True)
            
            self.log("✓ Sunucu durdurma işlemi tamamlandı.")
            
        except Exception as e:
            self.log(f"❌ Sunucu durdurma hatası: {type(e).__name__}: {e}")
            # Button'ları geri aktifleştir
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(True)
            self.browse_button.setEnabled(True)

    def cleanup_server_process(self):
        """Sunucu sürecini temizle"""
        self.server_manager.cleanup_server_process()

    def open_web_ui(self):
        """Web arayüzünü varsayılan tarayıcıda aç"""
        port = self.port_spinbox.value()
        url = f"http://127.0.0.1:{port}"
        try:
            webbrowser.open(url)
            self.log(f"✓ Web arayüzü açılıyor: {url}")
        except Exception as e:
            self.log(f"⚠ Web arayüzü açılamadı: {e}")

    def on_server_started(self):
        """Sunucu başarıyla başlatıldığında"""
        self.log("✓ Sunucu başarıyla başlatıldı, Web UI butonu aktifleştirildi.")
        self.open_web_ui_button.setEnabled(True)
        self.start_server_button.setEnabled(False)
        self.stop_server_button.setEnabled(True)
        self.browse_button.setEnabled(False)

    def on_server_finished(self, exit_code, exit_status):
        """Sunucu kapandığında"""
        self.log(f"⚠ Sunucu kapandı (Exit Code: {exit_code})")
        self.open_web_ui_button.setEnabled(False)
        self.start_server_button.setEnabled(True)
        self.stop_server_button.setEnabled(False)
        self.browse_button.setEnabled(True)
        self.timer.stop()

    def on_server_error(self, error):
        """Sunucu başlatılırken hata oluştuğunda"""
        self.log(f"❌ Server Process hatası: {error}")
        self.start_server_button.setEnabled(True)
        self.stop_server_button.setEnabled(False)
        self.browse_button.setEnabled(True)
        self.open_web_ui_button.setEnabled(False)
        self.timer.stop()

    def update_system_monitor(self):
        """Sistem monitörünü güncelle"""
        try:
            # CPU
            try:
                cpu_usage = self.system_monitor.get_cpu_usage()
                self.cpu_label.setText(f"CPU Kullanımı: %{cpu_usage:.1f}")
                self.cpu_progress.setValue(int(cpu_usage))
            except Exception:
                pass

            # RAM
            try:
                ram_usage = self.system_monitor.get_ram_usage()
                self.ram_label.setText(f"RAM Kullanımı: %{ram_usage:.1f}")
                self.ram_progress.setValue(int(ram_usage))
            except Exception:
                pass

            # GPU
            if self.system_monitor.gpu_available:
                try:
                    gpu_usage = self.system_monitor.get_gpu_usage()
                    if gpu_usage is not None:
                        self.gpu_label.setText(f"GPU Kullanımı: %{gpu_usage:.1f}")
                        self.gpu_progress.setValue(int(gpu_usage))
                except Exception:
                    pass

            # VRAM
            if self.system_monitor.vram_available:
                try:
                    vram_usage = self.system_monitor.get_vram_usage()
                    if vram_usage is not None:
                        self.vram_label.setText(f"VRAM Kullanımı: %{vram_usage:.1f}")
                        self.vram_progress.setValue(int(vram_usage))
                except Exception:
                    pass
        except Exception:
            # Timer callback'inde hata olursa sessiz kalsın, uygulama devam etsin
            pass

    def log(self, message):
        """Log mesajı ekle"""
        self.log_window.append(message)

    def cleanup_tray(self):
        """Sistem tepsisindeki ikonları temiz bir şekilde kaldır"""
        try:
            # Tray ikonunu gizle
            self.hide()
        except Exception:
            pass
        
        try:
            # Context menu'yü kapat ve sil
            if hasattr(self, 'menu') and self.menu:
                self.menu.close()
                self.menu.deleteLater()
        except Exception:
            pass
        
        try:
            # Tray ikonunun kendisini bellekten sil
            self.deleteLater()
        except Exception:
            pass

    def __del__(self):
        """Nesne bellekten silinirken tray ikonunu temizle"""
        try:
            self.cleanup_tray()
        except Exception:
            pass


# atexit ile temizlik fonksiyonunu kaydet
atexit.register(cleanup_on_exit)