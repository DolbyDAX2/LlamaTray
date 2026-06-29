"""
Command Preview Widget — Başlatma komutu önizleme bileşeni.
llama-server komutunu gerçek zamanlı olarak gösterir.
"""

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtGui import QFont


class CommandPreviewWidget(QGroupBox):
    """Başlatma komutu önizleme widget'ı"""

    def __init__(self, translations_func):
        super().__init__()
        self.translations_func = translations_func
        self._build_ui()

    def _build_ui(self):
        """Widget arayüzünü oluştur"""
        self.setTitle(self.translations_func("preview_group_title", "Başlatma Komutu Önizlemesi"))
        layout = QVBoxLayout()

        preview_label = QLabel(self.translations_func("label_command_preview", "Komut:"))
        layout.addWidget(preview_label)
        self.preview_label = preview_label

        self.command_text = QTextEdit()
        self.command_text.setReadOnly(True)
        mono_font = QFont("monospace")
        mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.command_text.setFont(mono_font)
        self.command_text.setFixedHeight(60)
        layout.addWidget(self.command_text)

        self.setLayout(layout)

    def build_command(self, model_path, advanced_settings):
        """Başlatma komutunu oluştur ve göster"""
        try:
            from ..server import LlamaServerManager
            cmd_path = LlamaServerManager(log_callback=None).find_llama_server()
        except Exception:
            cmd_path = "llama-server"

        parts = [cmd_path]

        # Model yolu
        if model_path:
            parts.extend(["-m", model_path])

        # Gelişmiş ayarlar
        if advanced_settings:
            gpu_layers = advanced_settings.gpu_layers_spinbox.value()
            parts.extend(["--n-gpu-layers", str(gpu_layers)])

            # Context boyutu
            try:
                context_size = int(advanced_settings.context_size_combobox.currentText())
            except (ValueError, TypeError):
                context_size = 32768
            parts.extend(["--ctx-size", str(context_size)])

            # Port
            port = advanced_settings.port_spinbox.value()
            parts.extend(["--port", str(port)])

            # mmproj dosyası
            mmproj_path = advanced_settings.mmproj_lineedit.text().strip()
            if mmproj_path:
                parts.extend(["--mmproj", mmproj_path])

            # Ek parametreler
            extra_params = advanced_settings.extra_params_lineedit.text().strip()
            if extra_params:
                parts.append(extra_params)

        self.command_text.setPlainText(" ".join(parts))

    def update_labels(self):
        """Çeviri etiketlerini güncelle"""
        self.setTitle(self.translations_func("preview_group_title", "Başlatma Komutu Önizlemesi"))
        if hasattr(self, 'preview_label'):
            self.preview_label.setText(self.translations_func("label_command_preview", "Komut:"))
