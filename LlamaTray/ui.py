"""
PyQt6 kullanıcı arayüzü modülü.
LlamaTray ana uygulaması - modüler yapı ile yeniden düzenlenmiştir.
"""

import os
import json
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QFileDialog, QMessageBox, QMainWindow,
    QTextEdit, QVBoxLayout, QHBoxLayout, QComboBox, QWidget, QDialog,
    QMenu, QPushButton, QInputDialog, QDialogButtonBox
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

import LlamaTray.ui_utils as ui_utils
from .ui_utils import load_translations, get_icon_path
from .monitor import SystemMonitor
from .server import LlamaServerManager
from .components import (
    SystemMonitorWidget, AdvancedSettingsWidget, ProfileManagerWidget,
    AboutDialog, CommandPreviewWidget, ServerControlsWidget, ModelSelectorWidget,
    HfDownloaderDialog,
)


class LlamaTray:
    """Ana LlamaTray uygulaması - modüler yapı"""

    def __init__(self):
        ui_utils._tray_instance = self
        self.translations = load_translations()
        self.current_language = "tr"

        # 1. Tüm temel özellikleri ve widget'ları önce belleğe al
        self.model_path = ""
        self.timer = QTimer()
        self.log = lambda msg: print(msg)  # Geçici log (log_window henüz yok)
        self.server_manager = LlamaServerManager(log_callback=self.log)
        self.system_monitor = SystemMonitor()

        # 2. Tray icon oluştur (get_translated hazır, widget'lar henüz gerekmiyor)
        self._init_tray_icon()

        # 3. Ana pencere ve tüm widget'ları oluştur
        self._init_main_window()

        # 4. Şimdi tüm widget'lar ve self.log hazır — sinyalleri bağla
        self.server_manager.started.connect(self.server_controls.on_server_started)
        self.server_manager.finished.connect(self.server_controls.on_server_finished)
        self.server_manager.errorOccurred.connect(self.server_controls.on_server_error)

        # 5. Konfigürasyon yükle (self.log artık log_window'a yazıyor, widget'lar mevcut)
        self.load_config()
        self.model_selector.set_model_path(self.model_path)
        self.profile_manager.refresh_combobox()

        # 6. Çevirileri uygula (tüm widget'lar + tray action'ları hazır)
        self.apply_translations()

        # 7. Timer'ı başlat
        self.timer.timeout.connect(self.update_system_monitor)
        self.timer.start(1000)

        # 8. Uygulama kapanış temizliği
        try:
            app = QApplication.instance()
            if app: app.aboutToQuit.connect(self.cleanup_tray)
        except Exception: pass

    def _init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon()
        ip = get_icon_path()
        if os.path.exists(ip): self.tray_icon.setIcon(QIcon(ip))
        self.tray_icon.setVisible(True)
        self.menu = QMenu()
        tr = self.get_translated
        self.browse_action = QAction(tr("menu_browse", "Göz At"))
        self.browse_action.triggered.connect(self.browse_file)
        self.menu.addAction(self.browse_action)
        self.start_server_action = QAction(tr("menu_start_server", "Sunucuyu Başlat"))
        self.start_server_action.triggered.connect(lambda: self.start_server())
        self.menu.addAction(self.start_server_action)
        self.stop_server_action = QAction(tr("menu_stop_server", "Sunucuyu Durdur"))
        self.stop_server_action.triggered.connect(lambda: self.stop_server())
        self.menu.addAction(self.stop_server_action)
        self.menu.addSeparator()
        self.about_action = QAction(tr("menu_about", "Hakkında / About"))
        self.about_action.triggered.connect(self.show_about_dialog)
        self.menu.addAction(self.about_action)
        self.tray_icon.setContextMenu(self.menu)

    def _init_main_window(self):
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setFixedHeight(100)
        # Şimdi log metodunu tanımla (log_window oluşturulduktan sonra)
        def _do_log(msg):
            self.log_window.append(msg)
        self.log = _do_log
        tr = self.get_translated
        # server_manager'ın log_callback'ini gerçek log fonksiyonuna yönlendir
        self.server_manager.log_callback = self.log
        # Modüler bileşenler
        self.model_selector = ModelSelectorWidget(tr)
        self.advanced_settings = AdvancedSettingsWidget(translations_func=tr)
        self.server_controls = ServerControlsWidget(
            translations_func=tr, server_manager=self.server_manager,
            advanced_settings=self.advanced_settings, timer=self.timer,
            log_func=self.log)
        self.command_preview = CommandPreviewWidget(tr, self.server_manager)
        self.profile_manager = ProfileManagerWidget(translations_func=tr, callbacks={
            'log': self.log, 'get_form_values': self.get_current_form_values,
            'apply_profile_values': self.apply_profile_values,
            'get_profiles_path': self.get_profiles_path,
            'save_profiles': self.save_profiles,
            'load_profiles': self.load_profiles,
            'window': None,  # Henüz oluşturulmadı, sonra ayarlanacak
        })
        self.monitor_widget = SystemMonitorWidget(
            system_monitor=self.system_monitor, translations_func=tr)

        # Sinyaller
        self.model_selector.get_browse_button().clicked.connect(self.browse_file)
        self.model_selector.get_hf_download_button().clicked.connect(self.hf_download)
        self.server_controls.start_server_button.clicked.connect(lambda: self.start_server())
        self.server_controls.stop_server_button.clicked.connect(lambda: self.stop_server())
        self.server_controls.open_web_ui_button.setEnabled(False)
        self.server_controls.open_web_ui_button.clicked.connect(lambda: self.server_controls.open_web_ui())
        for w, sig in [(self.advanced_settings.gpu_layers_spinbox, 'valueChanged'),
                       (self.advanced_settings.context_size_combobox, 'currentTextChanged'),
                       (self.advanced_settings.port_spinbox, 'valueChanged'),
                       (self.advanced_settings.preset_combobox, 'currentTextChanged'),
                       (self.advanced_settings.extra_params_lineedit, 'textChanged'),
                       (self.advanced_settings.mmproj_lineedit, 'textChanged')]:
            getattr(w, sig).connect(self.build_command_preview)
        self.profile_manager.profile_combobox.currentIndexChanged.connect(
            lambda i: self.profile_manager.load_profile(i))
        self.profile_manager.save_profile_button.clicked.connect(
            lambda: self.profile_manager.save_profile())
        self.profile_manager.update_profile_button.clicked.connect(
            lambda: self.profile_manager.update_profile())
        self.profile_manager.delete_profile_button.clicked.connect(
            lambda: self.profile_manager.delete_profile())
        self.build_command_preview()

        # Dil + about (sağ alt)
        self.language_combo = QComboBox()
        self.language_combo.addItems([tr("tr_language", "🇹🇷 Türkçe"), tr("en_language", "🇬🇧 English")])
        self.language_combo.setCurrentIndex(0)
        self.language_combo.setFixedHeight(28)
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        bottom = QHBoxLayout()
        bottom.addWidget(self.language_combo)
        self.about_button = QPushButton(tr("about_button", "ℹ️ Uygulama Hakkında"))
        self.about_button.clicked.connect(self.show_about_dialog)
        self.about_button.setFixedHeight(28)
        bottom.addWidget(self.about_button)
        bottom.addStretch()

        # Ana layout
        self.layout = QVBoxLayout()
        for w in [self.log_window, self.model_selector, self.server_controls,
                  self.advanced_settings, self.command_preview,
                  self.profile_manager, self.monitor_widget]:
            self.layout.addWidget(w)
        self.layout.addLayout(bottom)

        self.window = QMainWindow()
        cw = QWidget(); cw.setLayout(self.layout); self.window.setCentralWidget(cw)
        self.window.setWindowTitle(f"{tr('app_name', '🦙 LlamaTray')} {tr('version', 'v1.3.0')}")
        self.window.setGeometry(100, 100, 450, 750)
        # ProfileManager'a window referansını ver
        self.profile_manager.callbacks['window'] = self.window

        orig_close = self.window.closeEvent
        def win_close(e):
            try:
                self.log("=" * 60)
                self.log(tr("log_window_closing", "🚪 Pencere kapanıyor, sunucu durdurması yapılıyor..."))
                self.stop_server()
                self.log(tr("log_app_closing", "✓ Uygulama kapatılıyor."))
            except Exception as ex:
                self.log(tr("log_close_error", "⚠ Kapanış sırasında hata: {error}").format(error=ex))
            finally:
                if orig_close and callable(orig_close):
                    orig_close(e)
                else:
                    e.accept()
                try: self.cleanup_tray()
                except Exception: pass
        self.window.closeEvent = win_close
        ip = get_icon_path()
        if os.path.exists(ip): self.window.setWindowIcon(QIcon(ip))

    def get_translated(self, key, default=""):
        return self.translations.get(self.current_language, {}).get(key, default)

    def build_command_preview(self):
        if hasattr(self, 'command_preview'):
            self.command_preview.build_command(self.model_path, self.advanced_settings)

    def start_server(self):
        self.server_controls.start_server(self.model_path)
        self.save_config()
        self.model_selector.get_browse_button().setEnabled(False)

    def stop_server(self):
        self.server_controls.stop_server()
        self.model_selector.get_browse_button().setEnabled(True)

    def update_system_monitor(self):
        if hasattr(self, 'monitor_widget'): self.monitor_widget.update_resources()

    # ---- Dil yönetimi ----
    def on_language_changed(self, language):
        self.current_language = "tr" if "Türkçe" in language or "Turkish" in language else "en"
        self.apply_translations()
        ln = "Türkçe" if self.current_language == "tr" else "English"
        self.log(self.get_translated("log_language_changed", "🌐 Dil değiştirildi: {lang}").format(lang=ln))

    def apply_translations(self):
        tr = self.get_translated
        for a, k in [(self.browse_action, "menu_browse"), (self.start_server_action, "menu_start_server"),
                     (self.stop_server_action, "menu_stop_server"), (self.about_action, "menu_about")]:
            a.setText(tr(k))
        if hasattr(self, 'about_button'): self.about_button.setText(tr("about_button", "ℹ️ Uygulama Hakkında"))
        for comp in [self.model_selector, self.server_controls, self.command_preview,
                     self.advanced_settings, self.monitor_widget, self.profile_manager]:
            if hasattr(comp, 'update_labels'): comp.update_labels()
        if hasattr(self, 'language_combo'):
            self.language_combo.blockSignals(True); self.language_combo.clear()
            self.language_combo.addItems([tr("tr_language", "🇹🇷 Türkçe"), tr("en_language", "🇬🇧 English")])
            self.language_combo.setCurrentIndex(1 if self.current_language == "en" else 0)
            self.language_combo.blockSignals(False)
        if hasattr(self, 'window'):
            self.window.setWindowTitle(f"{tr('app_name', '🦙 LlamaTray')} {tr('version', 'v1.3.0')}")

    def show_about_dialog(self):
        AboutDialog(translations_func=self.get_translated, icon_path=get_icon_path(),
                     parent=getattr(self, 'window', None)).exec()

    # ---- Config / Profil ----
    def get_config_dir(self):
        d = os.path.join(os.path.expanduser("~"), ".llamatray")
        os.makedirs(d, exist_ok=True); return d
    def get_config_path(self):
        return os.path.join(self.get_config_dir(), "config.json")
    def get_profiles_path(self):
        return os.path.join(self.get_config_dir(), "profiles.json")

    def load_profiles(self):
        p = self.get_profiles_path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f: return json.load(f)
            except Exception as e: self.log(f"⚠ Profiller yüklenemedi: {e}")
        return {}

    def save_profiles(self, profiles):
        try:
            with open(self.get_profiles_path(), "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
        except Exception as e: self.log(f"❌ Profiller kaydedilemedi: {e}")

    def get_current_form_values(self):
        try: ctx = int(self.advanced_settings.context_size_combobox.currentText())
        except (ValueError, TypeError): ctx = 32768
        return {"gpu_layers": self.advanced_settings.gpu_layers_spinbox.value(), "context_size": ctx,
                "port": self.advanced_settings.port_spinbox.value(),
                "extra_args": self.advanced_settings.extra_params_lineedit.text().strip(),
                "mmproj_path": self.advanced_settings.mmproj_lineedit.text().strip()}

    def apply_profile_values(self, data):
        gl = data.get("gpu_layers")
        if gl is not None:
            try: self.advanced_settings.gpu_layers_spinbox.setValue(int(gl))
            except (ValueError, TypeError): pass
        cs = data.get("context_size")
        if cs is not None:
            try:
                cs = min(max(int(cs), 512), 1000000); cs_str = str(cs)
                if self.advanced_settings.context_size_combobox.findText(cs_str) >= 0:
                    self.advanced_settings.context_size_combobox.setCurrentText(cs_str)
                else:
                    self.advanced_settings.context_size_combobox.blockSignals(True)
                    self.advanced_settings.context_size_combobox.clear()
                    for i in ["16384", "32768", "65536", "131072", "262144"]:
                        self.advanced_settings.context_size_combobox.addItem(i)
                    self.advanced_settings.context_size_combobox.addItem(cs_str)
                    self.advanced_settings.context_size_combobox.setCurrentText(cs_str)
                    self.advanced_settings.context_size_combobox.blockSignals(False)
            except (ValueError, TypeError): pass
        p = data.get("port")
        if p is not None:
            try: self.advanced_settings.port_spinbox.setValue(int(p))
            except (ValueError, TypeError): pass
        ea = data.get("extra_args")
        if ea is not None: self.advanced_settings.extra_params_lineedit.setText(str(ea))
        mp = data.get("mmproj_path")
        if mp is not None: self.advanced_settings.mmproj_lineedit.setText(str(mp))

    def save_config(self):
        try:
            cp = self.get_config_path()
            try: ctx = int(self.advanced_settings.context_size_combobox.currentText())
            except (ValueError, TypeError): ctx = 32768
            config = {"model_path": self.model_path,
                      "gpu_layers": self.advanced_settings.gpu_layers_spinbox.value(),
                      "context_size": ctx,
                      "port": self.advanced_settings.port_spinbox.value(),
                      "extra_params": self.advanced_settings.extra_params_lineedit.text(),
                      "mmproj_path": self.advanced_settings.mmproj_lineedit.text().strip(),
                      "language": self.current_language}
            with open(cp, "w", encoding="utf-8") as f: json.dump(config, f, indent=2)
            self.log(self.get_translated("log_config_saved", "✓ Ayarlar başarıyla kaydedildi."))
        except PermissionError: self.log("❌ Hata: Dosya yazma izni yok.")
        except OSError as e: self.log(f"❌ Hata: Disk hatası: {e}")
        except Exception as e: self.log(f"❌ Hata: {type(e).__name__}: {e}")

    def load_config(self):
        cp = self.get_config_path()
        if not os.path.exists(cp):
            self.log("ℹ Kaydedilmiş yapılandırma bulunamadı. Varsayılan ayarlar kullanılıyor."); return
        try:
            with open(cp, "r", encoding="utf-8") as f: config = json.load(f)
            self.model_path = config.get("model_path")
            if self.model_path:
                self.log(self.get_translated("log_model_path_loaded", "✓ Model yolu yüklendi: {path}").format(path=self.model_path))
            gl = config.get("gpu_layers")
            if gl is not None:
                try: self.advanced_settings.gpu_layers_spinbox.setValue(int(gl))
                except (ValueError, TypeError): self.log("⚠ GPU katmanları geçersiz, varsayılan kullanılıyor")
            cs = config.get("context_size")
            if cs is not None:
                try:
                    cs_str = str(int(cs))
                    if self.advanced_settings.context_size_combobox.findText(cs_str) >= 0:
                        self.advanced_settings.context_size_combobox.setCurrentText(cs_str)
                    else:
                        self.advanced_settings.context_size_combobox.blockSignals(True)
                        self.advanced_settings.context_size_combobox.clear()
                        for i in ["16384", "32768", "65536", "131072", "262144"]:
                            self.advanced_settings.context_size_combobox.addItem(i)
                        self.advanced_settings.context_size_combobox.addItem(cs_str)
                        self.advanced_settings.context_size_combobox.setCurrentText(cs_str)
                        self.advanced_settings.context_size_combobox.blockSignals(False)
                except (ValueError, TypeError):
                    self.log(self.get_translated("log_context_size_load_error", "⚠ Context boyutu geçersiz"))
            p = config.get("port")
            if p is not None:
                try: self.advanced_settings.port_spinbox.setValue(int(p))
                except (ValueError, TypeError): self.log(self.get_translated("log_port_load_error", "⚠ Port geçersiz"))
            ep = config.get("extra_params")
            if ep is not None: self.advanced_settings.extra_params_lineedit.setText(str(ep))
            mp = config.get("mmproj_path")
            if mp is not None: self.advanced_settings.mmproj_lineedit.setText(str(mp))
            sl = config.get("language")
            if sl in ["tr", "en"]:
                self.current_language = sl
                self.log(self.get_translated("log_config_loaded", "✓ Yapılandırma yüklendi. Dil: {lang}").format(lang="Türkçe" if sl == "tr" else "English"))
            else: self.log("✓ Yapılandırma başarıyla yüklendi.")
        except json.JSONDecodeError as e: self.log(f"❌ Hata: Geçersiz JSON - {e}")
        except PermissionError: self.log("❌ Hata: Dosya okunamadı - İzin reddedildi")
        except Exception as e: self.log(f"❌ Hata: {type(e).__name__}: {e}")

    def browse_file(self):
        try:
            fp, _ = QFileDialog.getOpenFileName(
                getattr(self, 'window', None),
                self.get_translated("dialog_select_model_title", "Bilgisayarınızdan .gguf model dosyasını seçin"),
                "", "GGUF/GGML Files (*.gguf *.ggml);;Tüm Dosyalar (*.*)")
            if fp:
                if not os.path.exists(fp):
                    self.log(self.get_translated("log_file_not_found", "❌ Seçilen dosya mevcut değil: {file_path}").format(file_path=fp)); return
                self.model_path = fp; self.model_selector.set_model_path(fp)
                sz = os.path.getsize(fp) / (1024 * 1024)
                self.log(self.get_translated("log_model_selected", "✓ Model seçildi: {file_path}").format(file_path=fp))
                self.log(self.get_translated("log_file_size", "  Dosya boyutu: {size:.2f} MB").format(size=sz))
                self.build_command_preview()
        except Exception as e:
            self.log(f"❌ Hata: Model seçilirken hata - {type(e).__name__}: {e}")

    def hf_download(self):
        """HuggingFace'den model indir"""
        dialog = HfDownloaderDialog(translations_func=self.get_translated, parent=getattr(self, 'window', None))
        if dialog.exec():
            path = dialog.get_downloaded_path()
            if path and os.path.exists(path):
                self.model_path = path
                self.model_selector.set_model_path(path)
                sz = os.path.getsize(path) / (1024 * 1024)
                self.log(self.get_translated("log_model_selected", "✓ Model seçildi: {file_path}").format(file_path=path))
                self.log(self.get_translated("log_file_size", "  Dosya boyutu: {size:.2f} MB").format(size=sz))
                self.build_command_preview()

    def cleanup_tray(self):
        try:
            if hasattr(self, 'tray_icon'): self.tray_icon.hide()
        except Exception: pass
        try:
            if hasattr(self, 'menu') and self.menu:
                self.menu.close(); self.menu.deleteLater()
        except Exception: pass
        try:
            if hasattr(self, 'tray_icon'): self.tray_icon.deleteLater()
        except Exception: pass

    def __del__(self):
        try: self.cleanup_tray()
        except Exception: pass
