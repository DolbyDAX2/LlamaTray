"""
Model Selector Widget — Model dosyası seçimi ve görüntüleme.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
import os


class ModelSelectorWidget(QWidget):
    """Model dosyası seçimi widget'ı"""

    def __init__(self, translations_func):
        super().__init__()
        self.translations_func = translations_func
        self.model_path = ""
        self._build_ui()

    def _build_ui(self):
        """Widget arayüzünü oluştur"""
        layout = QVBoxLayout()

        self.browse_button = QPushButton(self.translations_func("button_model_select", "Model Seç"))
        layout.addWidget(self.browse_button)

        self.model_label = QLabel("")
        self.model_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.model_label)

        self.setLayout(layout)

    def get_browse_button(self):
        """Browse butonunu döndür (bağlantılar için)"""
        return self.browse_button

    def set_model_path(self, path):
        """Model yolunu dışarıdan ayarla ve UI'ı güncelle"""
        self.model_path = path
        if path:
            display_name = os.path.basename(path)
            try:
                file_size_mb = os.path.getsize(path) / (1024 * 1024)
                self.model_label.setText(f"{display_name} ({file_size_mb:.2f} MB)")
                self.model_label.setStyleSheet("color: green; font-style: italic;")
            except OSError:
                self.model_label.setText(display_name)
                self.model_label.setStyleSheet("color: gray; font-style: italic;")
        else:
            self.model_label.setText("")
            self.model_label.setStyleSheet("color: gray; font-style: italic;")

    def update_labels(self):
        """Çeviri etiketlerini güncelle"""
        if hasattr(self, 'browse_button'):
            self.browse_button.setText(self.translations_func("button_model_select", "Model Seç"))
