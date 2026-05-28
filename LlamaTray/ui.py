"""
PyQt6 kullanıcı arayüzü modülü.
LlamaTray ana uygulaması - modüler yapı ile yeniden düzenlenmiştir.
"""

import os
import sys
import json
import atexit
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QFileDialog, QMessageBox, QInputDialog,
    QDialogButtonBox, QMenu, QTextEdit, QPushButton, QVBoxLayout,
    QWidget, QHBoxLayout, QLabel, QFrame, QProgressBar, QSpinBox, QComboBox,
    QLineEdit, QGroupBox
)
from PyQt6.QtGui import QIcon, QAction, QIntValidator
from PyQt6.QtCore import QTimer, QUrl

from .ui_utils import (
    load_translations, cleanup_tray_icon, cleanup_on_exit, get_icon_path, _tray_instance
)
from .monitor import SystemMonitor
from .server import LlamaServerManager
from .components import (
    SystemMonitorWidget,
    AdvancedSettingsWidget,
    ProfileManagerWidget,
    AboutDialog
)


# Global referans - atexit için (tek global değişken)
_tray_instance = None


class LlamaTray:
    """Ana LlamaTray uygulaması - modüler yapı"""
    
    def __init__(self):
        """Uygulama başlatıcı"""
        global _tray_instance
        _tray_instance = self
        
        # Translation desteği
        self.translations = load_translations()
        self.current_language = "tr"  # Varsayılan dil Türkçe
        
        # Sunucu yöneticisi
        self.server_manager = LlamaServerManager(log_callback=self.log)
        
        # Server state sinyallerini bağla
        self.server_manager.started.connect(self.on_server_started)
        self.server_manager.finished.connect(self.on_server_finished)
        self.server_manager.errorOccurred.connect(self.on_server_error)
        
        # Sistem monitörü
        self.system_monitor = SystemMonitor()
        
        # Tray ikonunu başlat
        self._init_tray_icon()
        
        # Ana pencereyi başlat
        self._init_main_window()
        
        # Tüm ayarları yükle
        self.load_config()
        
        # Profil listesini yükle
        self.refresh_profile_combobox()
        
        # Dil seçimi ve çevirileri uygula
        self.apply_translations()
        
        # Timer (sadece sistem monitörü için)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_monitor)
        self.timer.start(1000)  # 1 saniye aralıklarla güncelle
        
        self.model_path = None
        
        # QApplication signals bağla - uygulama çıkışında temizlik yap
        try:
            app = QApplication.instance()
            if app:
                app.aboutToQuit.connect(self.cleanup_tray)
        except Exception:
            pass
    
    def _init_tray_icon(self):
        """Sistem tepsisi ikonunu başlat"""
        self.tray_icon = QSystemTrayIcon()
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            print(f"!!! DIKKAT: İkon bulunamadi, aranan konum: {icon_path}")
        
        self.tray_icon.setVisible(True)
        
        # Menü
        self.menu = QMenu()
        
        self.browse_action = QAction(self.get_translated("menu_browse", "Göz Al"))
        self.browse_action.triggered.connect(self.browse_file)
        self.menu.addAction(self.browse_action)
        
        self.start_server_action = QAction(self.get_translated("menu_start_server", "Sunucuyu Başlat"))
        self.start_server_action.triggered.connect(self.start_server)
        self.menu.addAction(self.start_server_action)
        
        self.stop_server_action = QAction(self.get_translated("menu_stop_server", "Sunucuyu Durdur"))
        self.stop_server_action.triggered.connect(self.stop_server)
        self.menu.addAction(self.stop_server_action)
        
        self.menu.addSeparator()
        
        self.about_action = QAction(self.get_translated("menu_about", "Hakkında / About"))
        self.about_action.triggered.connect(self.show_about_dialog)
        self.menu.addAction(self.about_action)
        
        self.tray_icon.setContextMenu(self.menu)
    
    def _init_main_window(self):
        """Ana pencereyi başlat"""
        from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFrame, QLabel, QProgressBar
        
        # Log penceresi
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setFixedHeight(100)
        
        # Butonlar
        self.browse_button = QPushButton(self.get_translated("button_model_select", "Model Seç"))
        self.browse_button.clicked.connect(self.browse_file)
        
        self.start_server_button = QPushButton(self.get_translated("button_start_server", "Sunucuyu Başlat"))
        self.start_server_button.clicked.connect(self.start_server)
        
        self.stop_server_button = QPushButton(self.get_translated("button_stop_server", "Sunucuyu Durdur"))
        self.stop_server_button.clicked.connect(self.stop_server)
        
        self.open_web_ui_button = QPushButton(self.get_translated("button_open_web_ui", "Web Arayüzünü Aç"))
        self.open_web_ui_button.clicked.connect(self.open_web_ui)
        self.open_web_ui_button.setEnabled(False)  # Başlangıçta devre dışı
        
        # Dil seçimi ve Uygulama Hakkında butonu (sağ alt köşede, yan yana)
        self.language_combo = QComboBox()
        self.language_combo.addItems([self.get_translated("tr_language", "🇹🇷 Türkçe"), self.get_translated("en_language", "🇬🇧 English")])
        self.language_combo.setCurrentIndex(0)  # Varsayılan Türkçe
        self.language_combo.setFixedHeight(28)
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        
        # Dil seçimi ve about butonu için container layout
        self.bottom_container = QHBoxLayout()
        self.bottom_container.addWidget(self.language_combo)
        
        self.about_button = QPushButton(self.get_translated("about_button", "ℹ️ Uygulama Hakkında"))
        self.about_button.clicked.connect(self.show_about_dialog)
        self.about_button.setFixedHeight(28)
        self.bottom_container.addWidget(self.about_button)
        self.bottom_container.addStretch()
        
        # Ana layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.log_window)
        self.layout.addWidget(self.browse_button)
        self.layout.addWidget(self.start_server_button)
        self.layout.addWidget(self.stop_server_button)
        self.layout.addWidget(self.open_web_ui_button)
        
        # Gelişmiş ayarlar bileşenini ekle
        self.advanced_settings = AdvancedSettingsWidget(translations_func=self.get_translated)
        self.layout.addWidget(self.advanced_settings)
        
        # Profil yönetimi bileşenini ekle
        self.profile_manager = ProfileManagerWidget(translations_func=self.get_translated)
        self.profile_manager.profile_combobox.currentIndexChanged.connect(self.on_profile_selected)
        self.profile_manager.save_profile_button.clicked.connect(self.save_current_profile)
        self.profile_manager.update_profile_button.clicked.connect(self.update_selected_profile)
        self.profile_manager.delete_profile_button.clicked.connect(self.delete_selected_profile)
        self.layout.addWidget(self.profile_manager)
        
        # Sistem monitörü bileşenini ekle
        self.monitor_widget = SystemMonitorWidget(
            system_monitor=self.system_monitor,
            translations_func=self.get_translated
        )
        self.layout.addWidget(self.monitor_widget)
        
        self.layout.addLayout(self.bottom_container)
        
        # Ana pencere
        self.window = QMainWindow()
        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.window.setCentralWidget(central_widget)
        self.window.setWindowTitle(f"{self.get_translated('app_name', '🦙 LlamaTray')} {self.get_translated('version', 'v1.0.2')}")
        self.window.setGeometry(100, 100, 450, 650)
        
        # Pencere kapatıldığında (X butonu) sunucuyu otomatik durdur
        original_close_event = self.window.closeEvent
        
        def window_close_event(event):
            try:
                self.log("=" * 60)
                self.log(self.get_translated("log_window_closing", "🚪 Pencere kapanıyor, sunucu durdurması yapılıyor..."))
                self.stop_server()
                self.log(self.get_translated("log_app_closing", "✓ Uygulama kapatılıyor."))
            except Exception as e:
                msg = self.get_translated("log_close_error", "⚠ Kapanış sırasında hata: {error}")
                self.log(msg.format(error=e))
            finally:
                original_close_event(event)
                # Pencere kapandığında tray'i de kapat
                try:
                    self.cleanup_tray()
                except Exception:
                    pass
        
        self.window.closeEvent = window_close_event
        
        # Pencere ikonu
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            self.window.setWindowIcon(QIcon(icon_path))
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        return self.translations.get(self.current_language, {}).get(key, default)
    
    def on_language_changed(self, language):
        """Dil değiştiğinde çağrılır"""
        if "Türkçe" in language or "Turkish" in language:
            self.current_language = "tr"
        elif "English" in language:
            self.current_language = "en"
        
        # Tüm UI elementlerine çevirileri uygula
        self.apply_translations()
        
        # Dil değişikliğini logla
        lang_name = "Türkçe" if self.current_language == "tr" else "English"
        self.log(self.get_translated("log_language_changed", "🌐 Language changed: {lang}").format(lang=lang_name))
    
    def apply_translations(self):
        """Tüm UI elementlerine çevirileri uygula"""
        tr = self.get_translated
        
        # Menü öğeleri
        if hasattr(self, 'browse_action'):
            self.browse_action.setText(tr("menu_browse", "Göz Al"))
        if hasattr(self, 'start_server_action'):
            self.start_server_action.setText(tr("menu_start_server", "Sunucuyu Başlat"))
        if hasattr(self, 'stop_server_action'):
            self.stop_server_action.setText(tr("menu_stop_server", "Sunucuyu Durdur"))
        if hasattr(self, 'about_action'):
            self.about_action.setText(tr("menu_about", "Hakkında / About"))
        
        # Butonlar
        if hasattr(self, 'browse_button'):
            self.browse_button.setText(tr("button_model_select", "Model Seç"))
        if hasattr(self, 'start_server_button'):
            self.start_server_button.setText(tr("button_start_server", "Sunucuyu Başlat"))
        if hasattr(self, 'stop_server_button'):
            self.stop_server_button.setText(tr("button_stop_server", "Sunucuyu Durdur"))
        if hasattr(self, 'open_web_ui_button'):
            self.open_web_ui_button.setText(tr("button_open_web_ui", "Web Arayüzünü Aç"))
        if hasattr(self, 'about_button'):
            self.about_button.setText(tr("about_button", "ℹ️ Uygulama Hakkında"))
        
        # Etiketler
        if hasattr(self, 'cpu_label'):
            self.cpu_label.setText(tr("label_cpu_usage", "CPU Kullanımı: %0").replace("%0", "0"))
        if hasattr(self, 'ram_label'):
            self.ram_label.setText(tr("label_ram_usage", "RAM Kullanımı: %0").replace("%0", "0"))
        if hasattr(self, 'gpu_label'):
            if self.system_monitor.gpu_available:
                self.gpu_label.setText(tr("label_gpu_usage", "GPU Kullanımı: %0").replace("%0", "0"))
            else:
                self.gpu_label.setText(tr("label_gpu_not_supported", "GPU: Desteklenmiyor"))
        if hasattr(self, 'vram_label'):
            if self.system_monitor.vram_available:
                self.vram_label.setText(tr("label_vram_usage", "VRAM Kullanımı: %0").replace("%0", "0"))
            else:
                self.vram_label.setText(tr("label_vram_not_supported", "VRAM: Desteklenmiyor"))
        
        # GroupBox başlıkları
        if hasattr(self, 'profile_manager'):
            self.profile_manager.setTitle(tr("profile_group_title", "Profil Yönetimi"))
        
        # Profil butonları
        if hasattr(self, 'profile_manager'):
            if hasattr(self.profile_manager, 'save_profile_button'):
                self.profile_manager.save_profile_button.setText(tr("button_save_profile", "💾 Profili Kaydet"))
            if hasattr(self.profile_manager, 'update_profile_button'):
                self.profile_manager.update_profile_button.setText(tr("button_update_profile", "🔄 Profili Güncelle"))
            if hasattr(self.profile_manager, 'delete_profile_button'):
                self.profile_manager.delete_profile_button.setText(tr("button_delete_profile", "🗑️ Profili Sil"))
        
        # Gelişmiş ayarlar label'ları
        if hasattr(self, 'advanced_settings') and hasattr(self.advanced_settings, 'update_labels'):
            self.advanced_settings.update_labels()
        
        # Sistem monitörü label'ları
        if hasattr(self, 'monitor_widget') and hasattr(self.monitor_widget, 'update_labels'):
            self.monitor_widget.update_labels()
        
        # Dil combo box - event signal'ini bloke et ki döngü oluşmasın
        if hasattr(self, 'language_combo'):
            self.language_combo.blockSignals(True)
            self.language_combo.clear()
            self.language_combo.addItems([tr("tr_language", "🇹🇷 Türkçe"), tr("en_language", "🇬🇧 English")])
            if self.current_language == "en":
                self.language_combo.setCurrentIndex(1)
            else:
                self.language_combo.setCurrentIndex(0)
            self.language_combo.blockSignals(False)
        
        # Pencere başlığı
        if hasattr(self, 'window'):
            self.window.setWindowTitle(f"{tr('app_name', '🦙 LlamaTray')} {tr('version', 'v1.1.1')}")
    
    def show_about_dialog(self):
        """Hakkında penceresini göster - dil desteği ile"""
        dialog = AboutDialog(
            translations_func=self.get_translated,
            icon_path=get_icon_path(),
            parent=self.window if hasattr(self, 'window') else None
        )
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
                with open(profiles_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                self.log(f"⚠ Profiller yüklenemedi: {e}")
        return {}
    
    def save_profiles(self, profiles):
        """Profilleri JSON dosyasına yaz"""
        profiles_path = self.get_profiles_path()
        try:
            with open(profiles_path, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ Profiller kaydedilemedi: {e}")
    
    def refresh_profile_combobox(self):
        """Combobox'ı kayıtlı profillerle doldur, mevcut seçimi koru"""
        if not hasattr(self, 'profile_manager'):
            return
        
        # Mevcut seçimi hatırla
        current_name = self.profile_manager.profile_combobox.currentText()
        
        self.profile_manager.profile_combobox.blockSignals(True)
        self.profile_manager.profile_combobox.clear()
        
        profiles = self.load_profiles()
        if profiles:
            self.profile_manager.profile_combobox.addItems(sorted(profiles.keys()))
            # Daha önce seçili olan varsa onu seç
            idx = self.profile_manager.profile_combobox.findText(current_name)
            if idx >= 0:
                self.profile_manager.profile_combobox.setCurrentIndex(idx)
        else:
            self.profile_manager.profile_combobox.addItem(self.get_translated("no_profile", "(Profil yok)"))
        
        self.profile_manager.profile_combobox.blockSignals(False)
    
    def get_current_form_values(self):
        """Formdaki tüm alanların değerlerini dict olarak döndür"""
        if not hasattr(self, 'advanced_settings'):
            return {
                "gpu_layers": 99,
                "context_size": 32768,
                "port": 8080,
                "extra_args": ""
            }
        
        try:
            context_size = int(self.advanced_settings.context_size_combobox.currentText())
        except (ValueError, TypeError):
            context_size = 32768
        
        return {
            "gpu_layers": self.advanced_settings.gpu_layers_spinbox.value(),
            "context_size": context_size,
            "port": self.advanced_settings.port_spinbox.value(),
            "extra_args": self.advanced_settings.extra_params_lineedit.text().strip()
        }
    
    def apply_profile_values(self, profile_data):
        """Profil verisini form alanlarına uygula - combobox'ta sadece hazır seçenekler görünür"""
        if not hasattr(self, 'advanced_settings'):
            return
        
        # GPU katmanları
        gpu_layers = profile_data.get("gpu_layers")
        if gpu_layers is not None:
            try:
                self.advanced_settings.gpu_layers_spinbox.setValue(int(gpu_layers))
            except (ValueError, TypeError):
                pass
        
        # Context boyutu - sadece hazır seçenekler gösterilir, custom değer combobox'a eklenmez
        context_size = profile_data.get("context_size")
        if context_size is not None:
            try:
                # Overflow kontrolü ve değer sınırlaması (512-1000000 arası)
                context_size = min(max(int(context_size), 512), 1000000)
                context_str = str(context_size)
                # Combobox'ta bu değer var mı kontrol et
                if self.advanced_settings.context_size_combobox.findText(context_str) >= 0:
                    self.advanced_settings.context_size_combobox.setCurrentText(context_str)
                else:
                    # Eğer listede yoksa, combobox'ı sıfırla ve sadece hazır seçenekleri ekle
                    self.advanced_settings.context_size_combobox.blockSignals(True)
                    self.advanced_settings.context_size_combobox.clear()
                    for item in ["16384", "32768", "65536", "131072", "262144"]:
                        self.advanced_settings.context_size_combobox.addItem(item)
                    # Profilin custom değerini ekle (çünkü profil tarafından yükleniyor)
                    self.advanced_settings.context_size_combobox.addItem(context_str)
                    self.advanced_settings.context_size_combobox.setCurrentText(context_str)
                    self.advanced_settings.context_size_combobox.blockSignals(False)
            except (ValueError, TypeError):
                pass
        
        # Port
        port = profile_data.get("port")
        if port is not None:
            try:
                self.advanced_settings.port_spinbox.setValue(int(port))
            except (ValueError, TypeError):
                pass
        
        # Ek parametreler
        extra_args = profile_data.get("extra_args")
        if extra_args is not None:
            self.advanced_settings.extra_params_lineedit.setText(str(extra_args))
    
    def save_current_profile(self):
        """Mevcut form değerlerini bir profile kaydet - dil desteği ile"""
        # Kullanıcıdan profil adı iste
        title = self.get_translated("dialog_save_profile_title", "Profili Kaydet")
        prompt = self.get_translated("dialog_save_profile_prompt", "Profil adı:")
        
        profile_name, ok = QInputDialog.getText(
            self.window if hasattr(self, 'window') else None,
            title,
            prompt,
            text=""
        )
        if not ok or not profile_name:
            return
        
        profile_name = profile_name.strip()
        if not profile_name:
            self.log(self.get_translated("log_profile_name_empty", "⚠ Profil adı boş olamaz."))
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
        idx = self.profile_manager.profile_combobox.findText(profile_name)
        if idx >= 0:
            self.profile_manager.profile_combobox.setCurrentIndex(idx)
        
        if is_update:
            msg = self.get_translated("log_profile_updated", "✓ Profil güncellendi: '{profile_name}'")
            self.log(msg.format(profile_name=profile_name))
        else:
            msg = self.get_translated("log_profile_saved", "✓ Profil kaydedildi: '{profile_name}'")
            self.log(msg.format(profile_name=profile_name))
    
    def on_profile_selected(self, index):
        """Combobox'tan profil seçildiğinde form alanlarını doldur"""
        if index < 0 or not hasattr(self, 'profile_manager'):
            return
        
        profile_name = self.profile_manager.profile_combobox.currentText()
        no_profile_text = self.get_translated("no_profile", "(Profil yok)")
        if not profile_name or profile_name == no_profile_text:
            return
        
        profiles = self.load_profiles()
        profile_data = profiles.get(profile_name)
        if profile_data:
            self.apply_profile_values(profile_data)
            msg = self.get_translated("log_profile_loaded", "✓ Profil yüklendi: '{profile_name}'")
            self.log(msg.format(profile_name=profile_name))
    
    def update_selected_profile(self):
        """Seçili profili güncelle - ekrandaki değerlerle mevcut profili yenile"""
        if not hasattr(self, 'profile_manager'):
            return
        
        profile_name = self.profile_manager.profile_combobox.currentText()
        no_profile_text = self.get_translated("no_profile", "(Profil yok)")
        if not profile_name or profile_name == no_profile_text:
            self.log(self.get_translated("log_no_profile_to_update", "⚠ Güncellenecek profil seçilmedi."))
            return
        
        # Mevcut değerleri al
        values = self.get_current_form_values()
        
        # Profili güncelle
        profiles = self.load_profiles()
        if profile_name in profiles:
            profiles[profile_name] = values
            self.save_profiles(profiles)
            msg = self.get_translated("dialog_update_profile_success", "✓ Profil '{profile_name}' güncellendi.")
            self.log(msg.format(profile_name=profile_name))
        else:
            msg = self.get_translated("dialog_update_profile_not_found", "⚠ Profil '{profile_name}' bulunamadı. Lütfen önce kaydedin.")
            self.log(msg.format(profile_name=profile_name))
    
    def delete_selected_profile(self):
        """Seçili profili sil - dil desteği ile"""
        if not hasattr(self, 'profile_manager'):
            return
        
        profile_name = self.profile_manager.profile_combobox.currentText()
        no_profile_text = self.get_translated("no_profile", "(Profil yok)")
        if not profile_name or profile_name == no_profile_text:
            self.log(self.get_translated("log_no_profile_to_delete", "⚠ Silinecek profil seçilmedi."))
            return
        
        # Onay sor
        title = self.get_translated("dialog_delete_profile_title", "Profili Sil")
        prompt = self.get_translated("dialog_delete_profile_prompt", "'{profile_name}' profilini silmek istediğinize emin misiniz?").format(profile_name=profile_name)
        
        reply = QMessageBox.question(
            self.window if hasattr(self, 'window') else None,
            title,
            prompt,
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
            msg = self.get_translated("log_profile_deleted", "✓ Profil silindi: '{profile_name}'")
            self.log(msg.format(profile_name=profile_name))
    
    def save_config(self):
        """Tüm ayarları kaydet - hem config.json hem de mevcut profil hem de dil tercihi"""
        try:
            config_path = self.get_config_path()
            
            # Context size'ı güvenli bir şekilde dönüştür
            try:
                context_size = int(self.advanced_settings.context_size_combobox.currentText())
            except (ValueError, TypeError):
                msg = self.get_translated("log_context_size_load_error", "⚠ Context size dönüştürülemedi, varsayılan 32768 kullanılıyor")
                self.log(msg)
                context_size = 32768
            
            # Dil tercihi kaydet
            language = self.current_language
            
            config = {
                "model_path": self.model_path,
                "gpu_layers": self.advanced_settings.gpu_layers_spinbox.value(),
                "context_size": context_size,
                "port": self.advanced_settings.port_spinbox.value(),
                "extra_params": self.advanced_settings.extra_params_lineedit.text(),
                "language": language  # Dil tercihi kaydet
            }
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self.log(self.get_translated("log_config_saved", "✓ Ayarlar başarıyla kaydedildi."))
            
        except PermissionError:
            self.log(f"❌ Hata: Ayarlar kaydedilemedi - Dosya yazma izni yok. (Dosya: {config_path})")
        except OSError as e:
            self.log(f"❌ Hata: Ayarlar kaydedilemedi - Disk hatası: {e}")
        except Exception as e:
            self.log(f"❌ Hata: Ayarlar kaydedilemedi - {type(e).__name__}: {e}")
    
    def load_config(self):
        """Tüm ayarları yükle - dil tercihi dahil"""
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Model yolu
                self.model_path = config.get("model_path")
                if self.model_path:
                    self.log(self.get_translated("log_model_load_error", "✓ Model yolu yüklendi: {path}").format(path=self.model_path))
                
                # GPU katmanları
                gpu_layers = config.get("gpu_layers")
                if gpu_layers is not None:
                    try:
                        self.advanced_settings.gpu_layers_spinbox.setValue(int(gpu_layers))
                    except (ValueError, TypeError) as e:
                        self.log(f"⚠ GPU katmanları değeri geçersiz ({gpu_layers}, tip: {type(gpu_layers).__name__}), varsayılan 99 kullanılıyor")
                
                # Context boyutu - combobox'ta sadece hazır seçenekler görünür ama config'den gelen custom değer eklenir
                context_size = config.get("context_size")
                if context_size is not None:
                    try:
                        context_str = str(int(context_size))
                        # Mevcut combobox'ta bu değer var mı kontrol et
                        if self.advanced_settings.context_size_combobox.findText(context_str) >= 0:
                            self.advanced_settings.context_size_combobox.setCurrentText(context_str)
                        else:
                            # Eğer listede yoksa, combobox'ı sıfırla ve sadece hazır seçenekleri ekle
                            self.advanced_settings.context_size_combobox.blockSignals(True)
                            self.advanced_settings.context_size_combobox.clear()
                            for item in ["16384", "32768", "65536", "131072", "262144"]:
                                self.advanced_settings.context_size_combobox.addItem(item)
                            # Config'den gelen custom değeri ekle
                            self.advanced_settings.context_size_combobox.addItem(context_str)
                            self.advanced_settings.context_size_combobox.setCurrentText(context_str)
                            self.advanced_settings.context_size_combobox.blockSignals(False)
                    except (ValueError, TypeError):
                        self.log(self.get_translated("log_context_size_load_error", "⚠ Context boyutu değeri geçersiz, varsayılan kullanılıyor"))
                
                # Port
                port = config.get("port")
                if port is not None:
                    try:
                        self.advanced_settings.port_spinbox.setValue(int(port))
                    except (ValueError, TypeError):
                        self.log(self.get_translated("log_port_load_error", "⚠ Port değeri geçersiz, varsayılan kullanılıyor"))
                
                # Ek parametreler
                extra_params = config.get("extra_params")
                if extra_params is not None:
                    self.advanced_settings.extra_params_lineedit.setText(str(extra_params))
                
                # Dil tercihi - kayıtlı dil varsa onu kullan
                saved_language = config.get("language")
                if saved_language in ["tr", "en"]:
                    self.current_language = saved_language
                    self.log(self.get_translated("log_config_loaded", "✓ Yapılandırma başarıyla yüklendi. Dil: {lang}").format(
                        lang="Türkçe" if saved_language == "tr" else "English"))
                else:
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
        """Model dosyası seç - dil desteği ile"""
        try:
            title = self.get_translated("dialog_select_model_title", "Bilgisayarınızdan .gguf model dosyasını seçin")
            file_path, _ = QFileDialog.getOpenFileName(
                self.window if hasattr(self, 'window') else None,
                title,
                "",
                "GGUF/GGML Files (*.gguf *.ggml);;Tüm Dosyalar (*.*)"
            )
            if file_path:
                if not os.path.exists(file_path):
                    msg = self.get_translated("log_file_not_found", "❌ Hata: Seçilen dosya artık mevcut değil: {file_path}")
                    self.log(msg.format(file_path=file_path))
                    return
                
                self.model_path = file_path
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                msg = self.get_translated("log_model_selected", "✓ Model seçildi: {file_path}")
                self.log(msg.format(file_path=file_path))
                msg = self.get_translated("log_file_size", "  Dosya boyutu: {size:.2f} MB")
                self.log(msg.format(size=file_size_mb))
        except Exception as e:
            self.log(f"❌ Hata: Model seçilirken hata - {type(e).__name__}: {e}")
    
    def start_server(self):
        """Sunucuyu başlat - dil desteği ile"""
        try:
            # Başlangıç kontrolleri
            gpu_layers = self.advanced_settings.gpu_layers_spinbox.value()
            
            # Context size'ı kontrol et
            context_size_text = self.advanced_settings.context_size_combobox.currentText()
            try:
                context_size = int(context_size_text)
            except ValueError:
                msg = self.get_translated("log_context_size_invalid", "❌ Hata: Context size geçersiz sayı: {value}")
                self.log(msg.format(value=context_size_text))
                return
            
            port = self.advanced_settings.port_spinbox.value()
            extra_params = self.advanced_settings.extra_params_lineedit.text().strip()
            
            # UI button'larını disable et işlem sırasında
            self.start_server_button.setEnabled(False)
            self.stop_server_button.setEnabled(False)
            self.browse_button.setEnabled(False)
            
            self.log("=" * 60)
            self.log(self.get_translated("log_server_starting", "🚀 Sunucu başlatma işlemi başladı..."))
            
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
                self.log(self.get_translated("log_server_start_success", "✓ Sunucu başlatma talebi kabul edildi. Yapılandırma kaydedildi."))
            else:
                self.log(self.get_translated("log_server_start_failed", "❌ Sunucu başlatma başarısız oldu."))
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
        """Sunucuyu durdur - dil desteği ile"""
        try:
            self.log(self.get_translated("log_server_stopping", "🛑 Sunucu durdurma talebi gönderiliyor..."))
            
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
            
            self.log(self.get_translated("log_server_stopped", "✓ Sunucu durdurma işlemi tamamlandı."))
            
        except Exception as e:
            msg = self.get_translated("log_server_stopping_error", "❌ Sunucu durdurma hatası: {type}: {error}")
            self.log(msg.format(type=type(e).__name__, error=e))
            # Button'ları geri aktifleştir
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(True)
            self.browse_button.setEnabled(True)
    
    def cleanup_server_process(self):
        """Sunucu sürecini temizle"""
        self.server_manager.cleanup_server_process()
    
    def open_web_ui(self):
        """Web arayüzünü varsayılan tarayıcıda aç - dil desteği ile"""
        port = self.advanced_settings.port_spinbox.value()
        url = f"http://127.0.0.1:{port}"
        try:
            webbrowser.open(url)
            msg = self.get_translated("log_web_ui_opening", "✓ Web arayüzü açılıyor: {url}")
            self.log(msg.format(url=url))
        except Exception as e:
            msg = self.get_translated("log_web_ui_open_error", "⚠ Web arayüzü açılamadı: {error}")
            self.log(msg.format(error=e))
    
    def on_server_started(self):
        """Sunucu başarıyla başlatıldığında"""
        self.log(self.get_translated("log_server_started", "✓ Sunucu başarıyla başlatıldı, Web UI butonu aktifleştirildi."))
        self.open_web_ui_button.setEnabled(True)
        self.start_server_button.setEnabled(False)
        self.stop_server_button.setEnabled(True)
        self.browse_button.setEnabled(False)
    
    def on_server_finished(self, exit_code, exit_status):
        """Sunucu kapandığında"""
        msg = self.get_translated("log_server_finished", "⚠ Sunucu kapandı (Exit Code: {code})")
        self.log(msg.format(code=exit_code))
        self.open_web_ui_button.setEnabled(False)
        self.start_server_button.setEnabled(True)
        self.stop_server_button.setEnabled(False)
        self.browse_button.setEnabled(True)
        self.timer.stop()
    
    def on_server_error(self, error):
        """Sunucu başlatılırken hata oluştuğunda"""
        msg = self.get_translated("log_server_error", "❌ Server Process hatası: {error}")
        self.log(msg.format(error=error))
        self.start_server_button.setEnabled(True)
        self.stop_server_button.setEnabled(False)
        self.browse_button.setEnabled(True)
        self.open_web_ui_button.setEnabled(False)
        self.timer.stop()
    
    def update_system_monitor(self):
        """Sistem monitörünü güncelle - dil desteği ile"""
        if hasattr(self, 'monitor_widget'):
            self.monitor_widget.update_monitor()
    
    def log(self, message):
        """Log mesajı ekle - dil desteği ile"""
        # Eğer mesaj bir format string ise ve çeviri anahtarı içeriyorsa çevir
        if isinstance(message, str) and ("✓" in message or "❌" in message or "⚠" in message or "🚀" in message or "🛑" in message or "🌐" in message or "🚪" in message):
            # Basit çeviri kontrolü - eğer İngilizce karakterler varsa İngilizce versiyonu kullan
            pass
        
        if hasattr(self, 'log_window'):
            self.log_window.append(message)
    
    def cleanup_tray(self):
        """Sistem tepsisindeki ikonları temiz bir şekilde kaldır"""
        try:
            # Tray ikonunu gizle
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
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
            if hasattr(self, 'tray_icon'):
                self.tray_icon.deleteLater()
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
