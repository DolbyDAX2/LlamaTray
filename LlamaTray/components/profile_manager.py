"""
Profil Yönetimi Bileşeni.
Kayıtlı profilleri listeleme, kaydetme, güncelleme ve silme işlevlerini içerir.
"""

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
    
