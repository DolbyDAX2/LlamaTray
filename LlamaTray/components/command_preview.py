"""
Command Preview Widget — Başlatma komutu önizleme bileşeni.
llama-server komutunu gerçek zamanlı olarak gösterir.
"""

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtGui import QFont


class CommandPreviewWidget(QGroupBox):
    """Başlatma komutu önizleme widget'ı"""

    def __init__(self, translations_func, server_manager=None):
        super().__init__()
        self.translations_func = translations_func
        self.server_manager = server_manager
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
        self.setCheckable(True)
        self.setChecked(True)
        self.toggled.connect(self._toggle_contents)

    def _toggle_contents(self, expanded):
        """Başlığa tıklandığında bölüm içeriğini daralt/aç."""
        for child in (self.preview_label, self.command_text):
            child.setVisible(expanded)
        self.setMaximumHeight(16777215 if expanded else 32)

    def build_command(self, model_path, advanced_settings, router_mode=False,
                      router_settings=None):
        """Başlatma komutunu oluştur ve göster"""
        if self.server_manager is not None:
            cmd_path = self.server_manager.find_llama_server()
        else:
            try:
                from ..server import LlamaServerManager
                cmd_path = LlamaServerManager(log_callback=None).find_llama_server()
            except Exception:
                cmd_path = "llama-server"

        parts = [cmd_path]

        if advanced_settings:
            gpu_layers = advanced_settings.gpu_layers_spinbox.value()
            port = advanced_settings.port_spinbox.value()

            if router_mode and router_settings:
                models_dir = router_settings.models_dir_lineedit.text().strip()
                if models_dir:
                    parts.extend(["--models-dir", models_dir])
                if not router_settings.no_autoload_checkbox.isChecked():
                    parts.append("--no-models-autoload")
                if router_settings.jinja_checkbox.isChecked():
                    parts.append("--jinja")
                parts.extend(["--host", "127.0.0.1", "--port", str(port)])
                try:
                    context_size = int(advanced_settings.context_size_combobox.currentText())
                except (ValueError, TypeError):
                    context_size = 32768
                parts.extend(["-ngl", str(gpu_layers), "--ctx-size", str(context_size)])
            else:
                if model_path:
                    parts.extend(["-m", model_path])
                parts.extend(["--n-gpu-layers", str(gpu_layers)])
                try:
                    context_size = int(advanced_settings.context_size_combobox.currentText())
                except (ValueError, TypeError):
                    context_size = 32768
                parts.extend(["--ctx-size", str(context_size), "--port", str(port)])
                mmproj_path = advanced_settings.mmproj_lineedit.text().strip()
                if mmproj_path:
                    parts.extend(["--mmproj", mmproj_path])

            extra_params = advanced_settings.extra_params_lineedit.text().strip()
            if extra_params:
                parts.append(extra_params)

        self.command_text.setPlainText(" ".join(parts))

    def update_labels(self):
        """Çeviri etiketlerini güncelle"""
        self.setTitle(self.translations_func("preview_group_title", "Başlatma Komutu Önizlemesi"))
        if hasattr(self, 'preview_label'):
            self.preview_label.setText(self.translations_func("label_command_preview", "Komut:"))
