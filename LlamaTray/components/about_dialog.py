"""
Hakkında Dialog Bileşeni.
Uygulama bilgilerini, geliştiriciyi ve kaynak linklerini gösterir.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QDialogButtonBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt


class AboutDialog(QDialog):
    """Hakkında penceresi - dil desteği ile"""
    
    def __init__(self, translations_func=None, icon_path=None, parent=None):
        """
        Args:
            translations_func: Çeviri fonksiyonu (get_translated metodu)
            icon_path: İkon yolu
            parent: Üst pencere referansı
        """
        super().__init__(parent)
        self.translations_func = translations_func
        self.icon_path = icon_path
        
        # Dil bilgisini translations_func'den al (varsayılan Türkçe)
        self.current_language = "tr"
        if self.translations_func:
            # translations_func ana uygulamadan gelir, oradaki current_language'ı kullan
            # Merkezi _tray_instance referansını ui_utils üzerinden al
            try:
                from LlamaTray import ui_utils
                if ui_utils._tray_instance is not None:
                    self.current_language = ui_utils._tray_instance.current_language
            except Exception:
                pass
        
        self.setWindowTitle(self.get_translated("about_dialog_title", "Hakkında / About"))
        self.setModal(True)
        self.setMinimumSize(400, 350)
        
        if icon_path:
            try:
                from PyQt6.QtWidgets import QApplication
                icon = QIcon(icon_path)
                if not icon.isNull():
                    self.setWindowIcon(icon)
            except Exception:
                pass
        
        self._init_ui()
    
    def _init_ui(self):
        """UI'yi başlat"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Dil seçimi
        about_language_combo = QComboBox()
        about_language_combo.addItems([self.get_translated("tr_language", "🇹🇷 Türkçe"), self.get_translated("en_language", "🇬🇧 English")])
        if self.current_language == "en":
            about_language_combo.setCurrentIndex(1)
        
        # HTML içerik (önce tanımla ki callback'te kullanılabilsin)
        self.html_content = QLabel()
        self.html_content.setWordWrap(True)
        self.html_content.setOpenExternalLinks(True)
        
        def update_about_dialog_language(language):
            """About dialog dilini güncelle"""
            lang_code = "tr" if "Türkçe" in language or "Turkish" in language else "en"
            
            html = self._build_html_content(lang_code)
            self.html_content.setText(html)
        
        about_language_combo.currentTextChanged.connect(update_about_dialog_language)
        
        # Başlangıçta dilin doğru ayarlanması için tetikle
        update_about_dialog_language(about_language_combo.currentText())
        
        layout.addWidget(about_language_combo)
        layout.addWidget(self.html_content)
        layout.addStretch()
        
        # Kapat butonu - çeviri desteği
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        if self.translations_func:
            return self.translations_func(key, default)
        return default
    
    def _build_html_content(self, lang_code):
        """HTML içeriğini dil seçimine göre oluştur"""
        # translations_func'u kullan (ana uygulamadan gelen çeviri fonksiyonu)
        # veya varsayılan değerler
        app_name = self.get_translated("app_name", "🦙 LlamaTray")
        version = self.get_translated("version", "v1.1.3")
        developer = self.get_translated("developer", "Geliştirici: Fatih Durdu")
        description = self.get_translated("description", "Linux (Arch Linux / CachyOS) sistemler için minimalist, hafif ve zombi süreç önleme mekanizmasına sahip PyQt6 tabanlı Llama.cpp (llama-server) yönetim aracı.")
        website = self.get_translated("website", "Kişisel Web Sitesi")
        github_profile = self.get_translated("github_profile", "GitHub Profili (DolbyDAX2)")
        gitea_repo = self.get_translated("gitea_repo", "Proje Gitea Deposu")
        
        return (
            f"<h3 style='color: #2980b9;'>{app_name} {version}</h3>"
            f"<p><b>{developer}</b></p>"
            f"<p>{description}</p>"
            "<hr>"
            f"<p>🌐 <a href='https://fatihdurdu.xyz/llamatray'>{website}</a></p>"
            f"<p>🐙 <a href='https://github.com/DolbyDAX2'>{github_profile}</a></p>"
            f"<p>📦 <a href='https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray'>{gitea_repo}</a></p>"
        )
