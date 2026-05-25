"""
Profil Yönetimi Bileşeni.
Kayıtlı profilleri listeleme, kaydetme, güncelleme ve silme işlevlerini içerir.
"""

import json
import os
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QInputDialog


class ProfileManagerWidget(QGroupBox):
    """Profil yönetimi grubu - profilleri kaydet, güncelle ve sil"""
    
    def __init__(self, translations_func=None):
        """
        Args:
            translations_func: Çeviri fonksiyonu (get_translated metodu)
        """
        super().__init__()
        self.translations_func = translations_func
        
        self._init_ui()
    
    def _init_ui(self):
        """UI'yi başlat"""
        self.setTitle(self.get_translated("profile_group_title", "Profil Yönetimi"))
        
        layout = QVBoxLayout()
        
        # Profil seçme combobox'ı
        profile_select_layout = QHBoxLayout()
        self.profile_combobox = QComboBox()
        self.profile_combobox.setMinimumHeight(28)
        profile_select_layout.addWidget(self.profile_combobox, 1)
        
        # Profil butonları
        self.save_profile_button = QPushButton(self.get_translated("button_save_profile", "💾 Profili Kaydet"))
        self.save_profile_button.setFixedHeight(28)
        
        self.update_profile_button = QPushButton(self.get_translated("button_update_profile", "🔄 Profili Güncelle"))
        self.update_profile_button.setFixedHeight(28)
        
        self.delete_profile_button = QPushButton(self.get_translated("button_delete_profile", "🗑️ Profili Sil"))
        self.delete_profile_button.setFixedHeight(28)
        
        profile_buttons_layout = QHBoxLayout()
        profile_buttons_layout.addWidget(self.save_profile_button)
        profile_buttons_layout.addWidget(self.update_profile_button)
        profile_buttons_layout.addWidget(self.delete_profile_button)
        
        layout.addLayout(profile_select_layout)
        layout.addLayout(profile_buttons_layout)
        
        self.setLayout(layout)
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        if self.translations_func:
            return self.translations_func(key, default)
        return default
    
    def load_profiles(self, config_dir=None):
        """Kayıtlı profilleri JSON'dan yükle"""
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".llamatray")
        
        profiles_path = os.path.join(config_dir, "profiles.json")
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠ Profiller yüklenemedi: {e}")
        return {}
    
    def save_profiles(self, profiles, config_dir=None):
        """Profilleri JSON dosyasına yaz"""
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".llamatray")
        
        profiles_path = os.path.join(config_dir, "profiles.json")
        try:
            with open(profiles_path, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Profiller kaydedilemedi: {e}")
    
    def refresh_combobox(self, config_dir=None):
        """Combobox'ı kayıtlı profillerle doldur, mevcut seçimi koru"""
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".llamatray")
        
        # Mevcut seçimi hatırla
        current_name = self.profile_combobox.currentText()
        
        self.profile_combobox.blockSignals(True)
        self.profile_combobox.clear()
        
        profiles = self.load_profiles(config_dir)
        if profiles:
            self.profile_combobox.addItems(sorted(profiles.keys()))
            # Daha önce seçili olan varsa onu seç
            idx = self.profile_combobox.findText(current_name)
            if idx >= 0:
                self.profile_combobox.setCurrentIndex(idx)
        else:
            self.profile_combobox.addItem(self.get_translated("no_profile", "(Profil yok)"))
        
        self.profile_combobox.blockSignals(False)
    
    def get_current_form_values(self, settings_widget=None):
        """Formdaki tüm alanların değerlerini dict olarak döndür"""
        if settings_widget:
            return settings_widget.get_values()
        
        # Varsayılan değerler (eğer settings_widget yoksa)
        try:
            context_size = int(32768)  # Varsayılan
        except (ValueError, TypeError):
            context_size = 32768
        
        return {
            "gpu_layers": 99,  # Varsayılan
            "context_size": context_size,
            "port": 8080,  # Varsayılan
            "extra_args": ""
        }
    
    def apply_profile_values(self, profile_data, settings_widget=None):
        """Profil verisini form alanlarına uygula"""
        if settings_widget:
            settings_widget.apply_values(profile_data)
            return
        
        # Varsayılan değerler (eğer settings_widget yoksa)
        # Bu metod aslında ana sınıf tarafından çağrılacak, bu yüzden burada bir şey yapmıyoruz
        pass
    
    def get_widgets(self):
        """Tüm widget'ları döndür (dışarıdan erişim için)"""
        return {
            'profile_combobox': self.profile_combobox,
            'save_profile_button': self.save_profile_button,
            'update_profile_button': self.update_profile_button,
            'delete_profile_button': self.delete_profile_button,
        }
