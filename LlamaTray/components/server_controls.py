"""
Server Controls Widget — Sunucu başlatma/durdurma ve Web UI butonları.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
import webbrowser


class ServerControlsWidget(QWidget):
    """Sunucu kontrol butonları widget'ı"""

    def __init__(self, translations_func, server_manager, advanced_settings, timer, log_func):
        super().__init__()
        self.translations_func = translations_func
        self.server_manager = server_manager
        self.advanced_settings = advanced_settings
        self.timer = timer
        self.log = log_func
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.start_server_button = QPushButton(self.translations_func("button_start_server", "Sunucuyu Başlat"))
        layout.addWidget(self.start_server_button)
        self.stop_server_button = QPushButton(self.translations_func("button_stop_server", "Sunucuyu Durdur"))
        layout.addWidget(self.stop_server_button)
        self.open_web_ui_button = QPushButton(self.translations_func("button_open_web_ui", "Web Arayüzünü Aç"))
        self.open_web_ui_button.setEnabled(False)
        layout.addWidget(self.open_web_ui_button)
        self.setLayout(layout)

    def update_labels(self):
        self.start_server_button.setText(self.translations_func("button_start_server", "Sunucuyu Başlat"))
        self.stop_server_button.setText(self.translations_func("button_stop_server", "Sunucuyu Durdur"))
        self.open_web_ui_button.setText(self.translations_func("button_open_web_ui", "Web Arayüzünü Aç"))

    def start_server(self, model_path):
        try:
            gpu_layers = self.advanced_settings.gpu_layers_spinbox.value()
            ctx_text = self.advanced_settings.context_size_combobox.currentText()
            try:
                context_size = int(ctx_text)
            except ValueError:
                self.log(self.translations_func("log_context_size_invalid", "❌ Hata: Context size geçersiz sayı: {value}").format(value=ctx_text))
                return
            port = self.advanced_settings.port_spinbox.value()
            extra_params = self.advanced_settings.extra_params_lineedit.text().strip()
            mmproj_path = self.advanced_settings.mmproj_lineedit.text().strip()
            self.start_server_button.setEnabled(False)
            self.stop_server_button.setEnabled(False)
            self.log("=" * 60)
            self.log(self.translations_func("log_server_starting", "🚀 Sunucu başlatma işlemi başladı..."))
            success = self.server_manager.start_server(
                model_path=model_path, gpu_layers=gpu_layers,
                context_size=context_size, port=port,
                extra_params=extra_params, mmproj_path=mmproj_path
            )
            if success:
                self.timer.start(1000)
                self.log(self.translations_func("log_server_start_success", "✓ Sunucu başlatma talebi kabul edildi."))
            else:
                self.log(self.translations_func("log_server_start_failed", "❌ Sunucu başlatma başarısız oldu."))
                self.start_server_button.setEnabled(True)
        except Exception as e:
            self.log(f"❌ Beklenmeyen hata (start_server): {type(e).__name__}: {e}")
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(True)

    def stop_server(self):
        try:
            self.log(self.translations_func("log_server_stopping", "🛑 Sunucu durdurma talebi gönderiliyor..."))
            self.stop_server_button.setEnabled(False)
            self.start_server_button.setEnabled(False)
            self.server_manager.stop_server()
            self.timer.stop()
            self.open_web_ui_button.setEnabled(False)
            self.start_server_button.setEnabled(True)
            self.log(self.translations_func("log_server_stopped", "✓ Sunucu durdurma işlemi tamamlandı."))
        except Exception as e:
            self.log(self.translations_func("log_server_stopping_error", "❌ Sunucu durdurma hatası: {type}: {error}").format(type=type(e).__name__, error=e))
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(True)

    def cleanup_server_process(self):
        self.server_manager.cleanup_server_process()

    def open_web_ui(self):
        port = self.advanced_settings.port_spinbox.value()
        url = f"http://127.0.0.1:{port}"
        try:
            webbrowser.open(url)
            self.log(self.translations_func("log_web_ui_opening", "✓ Web arayüzü açılıyor: {url}").format(url=url))
        except Exception as e:
            self.log(self.translations_func("log_web_ui_open_error", "⚠ Web arayüzü açılamadı: {error}").format(error=e))

    def on_server_started(self):
        self.log(self.translations_func("log_server_started", "✓ Sunucu başarıyla başlatıldı, Web UI butonu aktifleştirildi."))
        self.open_web_ui_button.setEnabled(True)
        self.start_server_button.setEnabled(False)
        self.stop_server_button.setEnabled(True)

    def on_server_finished(self, exit_code, exit_status):
        self.log(self.translations_func("log_server_finished", "⚠ Sunucu kapandı (Exit Code: {code})").format(code=exit_code))
        self.open_web_ui_button.setEnabled(False)
        self.start_server_button.setEnabled(True)
        self.stop_server_button.setEnabled(False)
        self.timer.stop()

    def on_server_error(self, error):
        self.log(self.translations_func("log_server_error", "❌ Server Process hatası: {error}").format(error=error))
        self.start_server_button.setEnabled(True)
        self.stop_server_button.setEnabled(False)
        self.open_web_ui_button.setEnabled(False)
        self.timer.stop()

    def set_browse_enabled(self, enabled):
        """Model selector'ın browse butonunu enable/disable et (dışarıdan çağrılır)"""
        pass  # Bu model_selector sorumluluğunda
