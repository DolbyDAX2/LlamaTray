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
        
        # Dil varsayılanı Türkçe (tr)
        self.current_language = "tr"
        
        self.setWindowTitle(self.get_translated("about_dialog_title", "Hakkında / About"))
        self.setModal(True)
        
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
        # Translation dosyasından değerleri al
        try:
            import json
            import os
            TRANSLATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "translations.json")
            with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
                translations = json.load(f)
            
            tr = translations.get(lang_code, {})
        except Exception:
            # Hata durumunda varsayılan değerler
            tr = {
                'app_name': '🦙 LlamaTray',
                'version': 'v1.1.1',
                'developer': 'Geliştirici: Fatih Durdu',
                'description': 'Linux (Arch Linux / CachyOS) sistemler için minimalist, hafif ve zombi süreç önleme mekanizmasına sahip PyQt6 tabanlı Llama.cpp (llama-server) yönetim aracı.',
                'website': 'Kişisel Web Sitesi',
                'github_profile': 'GitHub Profili (DolbyDAX2)',
                'gitea_repo': 'Proje Gitea Deposu'
            }
        
        return (
            f"<h3 style='color: #2980b9;'>{tr.get('app_name', '🦙 LlamaTray')} {tr.get('version', 'v1.1.1')}</h3>"
            f"<p><b>{tr.get('developer', 'Geliştirici: Fatih Durdu')}</b></p>"
            f"<p>{tr.get('description', 'Linux (Arch Linux / CachyOS) sistemler için minimalist, hafif ve zombi süreç önleme mekanizmasına sahip PyQt6 tabanlı Llama.cpp (llama-server) yönetim aracı.')}</p>"
            "<hr>"
            f"<p>🌐 <a href='https://fatihdurdu.xyz/llamatray'>{tr.get('website', 'Kişisel Web Sitesi')}</a></p>"
            f"<p>🐙 <a href='https://github.com/DolbyDAX2'>{tr.get('github_profile', 'GitHub Profili (DolbyDAX2)')}</a></p>"
            f"<p>📦 <a href='https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray'>{tr.get('gitea_repo', 'Proje Gitea Deposu')}</a></p>"
        )
