"""
PyQt6 kullanıcı arayüzü modülü.
LlamaTray ana uygulaması - modüler yapı ile yeniden düzenlenmiştir.
"""

import os
import json
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QFileDialog, QMessageBox, QMainWindow,
    QTextEdit, QVBoxLayout, QHBoxLayout, QComboBox, QWidget, QDialog,
    QMenu, QPushButton, QInputDialog, QDialogButtonBox, QTabWidget,
    QGroupBox, QRadioButton, QLineEdit, QScrollArea, QCheckBox
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

import LlamaTray.ui_utils as ui_utils
from .ui_utils import load_translations, get_icon_path
from .version import VERSION_DISPLAY
from .monitor import SystemMonitor
from .server import LlamaServerManager
from .components import (
    SystemMonitorWidget, AdvancedSettingsWidget, ProfileManagerWidget,
    AboutDialog, CommandPreviewWidget, ServerControlsWidget, ModelSelectorWidget,
    HfDownloaderDialog, RouterSettingsWidget,
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
        self._force_quit = False  # True: kapatma isteği minimize-to-tray'i atlar
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
        self.server_manager.started.connect(self._on_router_server_started)
        self.server_manager.finished.connect(lambda _code, _status: self.router_settings.stop_polling())
        self.server_manager.errorOccurred.connect(lambda _error: self.router_settings.stop_polling())

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
        """Sistem tepsi ikonunu oluştur.

        Modern GNOME/Wayland ortamlarında tray protokolü (StatusNotifier / DBus
        org.kde.StatusNotifierWatcher) olmayabilir. Bu yüzden başlatma
        try-except içindedir: tepsi kullanılamazsa uygulama pencere modunda
        çalışmaya devam eder, crash atmaz.
        """
        self.tray_available = False
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.log(self.get_translated(
                    "log_tray_unavailable",
                    "⚠ Sistem tepsisi bu ortamda kullanılamıyor. Pencere modunda devam ediliyor."))
                return
            self.tray_icon = QSystemTrayIcon()
            ip = get_icon_path()
            if os.path.exists(ip): self.tray_icon.setIcon(QIcon(ip))
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
            # Tepsi modunda kalıcı çıkış yolu (minimize-to-tray ile birlikte zorunlu)
            self.quit_action = QAction(tr("menu_quit", "Çıkış"))
            self.quit_action.triggered.connect(self.quit_application)
            self.menu.addAction(self.quit_action)
            self.tray_icon.setContextMenu(self.menu)
            # Tek tık / çift tık: pencereyi göster/gizle
            self.tray_icon.activated.connect(self.on_tray_activated)
            self.tray_icon.setVisible(True)
            self.tray_available = True
        except Exception as e:
            # Tray D-Bus/protokol hatası uygulamayı çökertmemeli
            print(f"⚠ System tray could not be initialized ({type(e).__name__}: {e}). "
                  f"Continuing in window mode.")
            self.tray_available = False

    def on_tray_activated(self, reason):
        """Tepsi simgesine tıklanınca pencereyi göster/gizle."""
        if reason not in (QSystemTrayIcon.ActivationReason.Trigger,
                          QSystemTrayIcon.ActivationReason.DoubleClick):
            return
        try:
            if self.window.isVisible():
                self.window.hide()
            else:
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()
        except Exception:
            pass

    def quit_application(self):
        """Tepsi menüsünden kesin çıkış: minimize-to-tray davranışını atlar."""
        self._force_quit = True
        try:
            window = getattr(self, 'window', None)
            if window is not None and window.isVisible():
                # closeEvent kapanış temizliğini (sunucu durdurma vb.) yapar
                window.close()
                return
        except Exception:
            pass
        # Pencere zaten gizliyse close() hiçbir şey yapmaz; elle temizle ve çık.
        try:
            self.log(self.get_translated("log_app_closing", "✓ Uygulama kapatılıyor."))
            self.stop_server()
            self.cleanup_tray()
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            try:
                app.quit()
            except Exception:
                pass

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
        self.router_settings = RouterSettingsWidget(
            translations_func=tr,
            port_func=lambda: self.advanced_settings.port_spinbox.value(),
            log_func=self.log)
        self.mode_group = QGroupBox()
        mode_layout = QHBoxLayout(self.mode_group)
        self.single_mode_radio = QRadioButton()
        self.router_mode_radio = QRadioButton()
        self.single_mode_radio.setChecked(True)
        self.mode_group.setCheckable(True)
        self.mode_group.setChecked(True)
        self.mode_group.toggled.connect(self._toggle_mode_group)
        mode_layout.addWidget(self.single_mode_radio)
        mode_layout.addWidget(self.router_mode_radio)
        mode_layout.addStretch()
        self.router_settings.setVisible(False)
        self.server_controls = ServerControlsWidget(
            translations_func=tr, server_manager=self.server_manager,
            advanced_settings=self.advanced_settings, timer=self.timer,
            log_func=self.log, router_settings=self.router_settings,
            router_mode_func=self.is_router_mode)
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
        self.single_mode_radio.toggled.connect(self.on_mode_changed)
        for widget in (self.router_settings.models_dir_lineedit,
                       self.router_settings.no_autoload_checkbox,
                       self.router_settings.jinja_checkbox):
            signal = widget.textChanged if isinstance(widget, QLineEdit) else widget.toggled
            signal.connect(self.build_command_preview)
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
        # "Minimize to Tray on Close" ayarı: kapatma butonu pencereyi gizler,
        # uygulama tepside yaşamaya devam eder (sadece tray mevcutken anlamlı).
        self.minimize_to_tray_checkbox = QCheckBox(tr("minimize_to_tray_on_close", "Kapatırken Tepside Minimize Et"))
        bottom.addWidget(self.minimize_to_tray_checkbox)
        self.about_button = QPushButton(tr("about_button", "ℹ️ Uygulama Hakkında"))
        self.about_button.clicked.connect(self.show_about_dialog)
        self.about_button.setFixedHeight(28)
        bottom.addWidget(self.about_button)
        bottom.addStretch()

        # Sekmeli ana layout
        # Düşük çözünürlüklerde (örn. 1024x768) içerik taşmasını/üst üste binmeyi
        # önlemek için Ana ve Ayarlar sekmeleri QScrollArea içine alınmıştır.
        self.tabs = QTabWidget()
        self.main_tab = QScrollArea()
        self.main_tab.setWidgetResizable(True)
        self.main_tab.setFrameShape(QScrollArea.Shape.NoFrame)
        main_content = QWidget()
        main_layout = QVBoxLayout(main_content)
        for widget in (self.log_window, self.model_selector,
                       self.server_controls, self.monitor_widget):
            main_layout.addWidget(widget)
        main_layout.addStretch()
        self.main_tab.setWidget(main_content)

        self.settings_tab = QScrollArea()
        self.settings_tab.setWidgetResizable(True)
        self.settings_tab.setFrameShape(QScrollArea.Shape.NoFrame)
        settings_content = QWidget()
        settings_layout = QVBoxLayout(settings_content)
        for widget in (self.mode_group, self.advanced_settings,
                       self.router_settings, self.command_preview):
            settings_layout.addWidget(widget)
        settings_layout.addStretch()
        self.settings_tab.setWidget(settings_content)

        self.profiles_tab = QWidget()
        profiles_layout = QVBoxLayout(self.profiles_tab)
        profiles_layout.addWidget(self.profile_manager)
        profiles_layout.addStretch()

        self.tabs.addTab(self.main_tab, "")
        self.tabs.addTab(self.settings_tab, "")
        self.tabs.addTab(self.profiles_tab, "")
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tabs)
        self.layout.addLayout(bottom)

        self.window = QMainWindow()
        cw = QWidget(); cw.setLayout(self.layout); self.window.setCentralWidget(cw)
        self.window.setWindowTitle(f"{tr('app_name', '🦙 LlamaTray')} {VERSION_DISPLAY}")
        # Düşük çözünürlüklü ekranlarda (1024x768 vb.) pencere açılabilmesi için
        # minimum boyut düşük tutulur; içerik QScrollArea içinde kayar.
        self.window.setMinimumSize(480, 420)
        screen = QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = min(560, avail.width())
            h = min(680, avail.height())
            x = avail.left() + max(0, (avail.width() - w) // 2)
            y = avail.top() + max(0, (avail.height() - h) // 3)
            self.window.setGeometry(x, y, w, h)
        else:
            self.window.setGeometry(100, 100, 560, 680)
        # ProfileManager'a window referansını ver
        self.profile_manager.callbacks['window'] = self.window

        orig_close = self.window.closeEvent
        def win_close(e):
            # "Minimize to Tray on Close" etkinse ve tepsi kullanılabilirse
            # pencereyi kapatmak yerine gizle; sunucu çalışmaya devam eder.
            checkbox = getattr(self, 'minimize_to_tray_checkbox', None)
            if (not self._force_quit and checkbox is not None
                    and checkbox.isChecked() and getattr(self, 'tray_available', False)):
                try:
                    self.log(tr("log_minimized_to_tray", "📴 Uygulama tepside minimize edildi. Sunucu çalışmaya devam ediyor."))
                except Exception:
                    pass
                try:
                    self.window.hide()
                finally:
                    e.ignore()
                return
            if (not self._force_quit and checkbox is not None
                    and checkbox.isChecked()):
                # Ayar açık ama tepsi yok: gizlersek uygulamaya ulaşılamaz → kapat.
                try:
                    self.log(tr("log_minimize_no_tray", "⚠ Sistem tepsisi kullanılamadığı için uygulama kapatılıyor."))
                except Exception:
                    pass
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

    def _toggle_mode_group(self, expanded):
        """Mod seçici bölümünü başlığa tıklanınca daralt/aç."""
        self.single_mode_radio.setVisible(expanded)
        self.router_mode_radio.setVisible(expanded)
        self.mode_group.setMaximumHeight(16777215 if expanded else 32)

    def is_router_mode(self):
        return hasattr(self, 'router_mode_radio') and self.router_mode_radio.isChecked()

    def on_mode_changed(self, single_mode):
        """Tek model ve router arayüzleri arasında geçiş yap."""
        self.model_selector.setVisible(True)
        self.model_selector.set_router_mode(not single_mode)
        self.advanced_settings.set_single_model_mode(single_mode)
        self.router_settings.setVisible(not single_mode)
        if single_mode:
            self.router_settings.stop_polling()
        elif self.server_manager.is_running():
            self.router_settings.start_polling()
        self.build_command_preview()

    def _on_router_server_started(self):
        if self.is_router_mode():
            QTimer.singleShot(750, self.router_settings.start_polling)

    def build_command_preview(self):
        if hasattr(self, 'command_preview'):
            self.command_preview.build_command(
                self.model_path, self.advanced_settings, self.is_router_mode(),
                getattr(self, 'router_settings', None))

    def start_server(self):
        self.server_controls.start_server(self.model_path)
        self.save_config()
        if not self.is_router_mode():
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
        if getattr(self, 'tray_available', False):
            for a, k in [(self.browse_action, "menu_browse"), (self.start_server_action, "menu_start_server"),
                         (self.stop_server_action, "menu_stop_server"), (self.about_action, "menu_about"),
                         (self.quit_action, "menu_quit")]:
                a.setText(tr(k))
        if hasattr(self, 'about_button'): self.about_button.setText(tr("about_button", "ℹ️ Uygulama Hakkında"))
        if hasattr(self, 'minimize_to_tray_checkbox'):
            self.minimize_to_tray_checkbox.setText(
                tr("minimize_to_tray_on_close", "Kapatırken Tepside Minimize Et"))
        if hasattr(self, 'tabs'):
            self.tabs.setTabText(0, tr("tab_main", "Ana"))
            self.tabs.setTabText(1, tr("tab_settings", "Ayarlar"))
            self.tabs.setTabText(2, tr("tab_profiles", "Profiller"))
            self.mode_group.setTitle(tr("mode_group_title", "Çalışma Modu"))
            self.single_mode_radio.setText(tr("mode_single", "Tek Model"))
            self.router_mode_radio.setText(tr("mode_router", "Router Modu"))
        for comp in [self.model_selector, self.server_controls, self.command_preview,
                     self.advanced_settings, self.router_settings,
                     self.monitor_widget, self.profile_manager]:
            if hasattr(comp, 'update_labels'): comp.update_labels()
        if hasattr(self, 'language_combo'):
            self.language_combo.blockSignals(True); self.language_combo.clear()
            self.language_combo.addItems([tr("tr_language", "🇹🇷 Türkçe"), tr("en_language", "🇬🇧 English")])
            self.language_combo.setCurrentIndex(1 if self.current_language == "en" else 0)
            self.language_combo.blockSignals(False)
        if hasattr(self, 'window'):
            self.window.setWindowTitle(f"{tr('app_name', '🦙 LlamaTray')} {VERSION_DISPLAY}")

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
                "mmproj_path": self.advanced_settings.mmproj_lineedit.text().strip(),
                "mode": "router" if self.is_router_mode() else "single",
                "models_dir": self.router_settings.models_dir_lineedit.text().strip(),
                "no_models_autoload": not self.router_settings.no_autoload_checkbox.isChecked(),
                "jinja": self.router_settings.jinja_checkbox.isChecked()}

    def apply_profile_values(self, data):
        if data.get("mode", "single") == "router":
            self.router_mode_radio.setChecked(True)
        else:
            self.single_mode_radio.setChecked(True)
        self.router_settings.models_dir_lineedit.setText(str(data.get("models_dir", "")))
        self.router_settings.no_autoload_checkbox.setChecked(
            not data.get("no_models_autoload", True))
        self.router_settings.jinja_checkbox.setChecked(data.get("jinja", True))
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
                      "mode": "router" if self.is_router_mode() else "single",
                      "models_dir": self.router_settings.models_dir_lineedit.text().strip(),
                      "no_models_autoload": not self.router_settings.no_autoload_checkbox.isChecked(),
                      "jinja": self.router_settings.jinja_checkbox.isChecked(),
                      "minimize_to_tray_on_close": (self.minimize_to_tray_checkbox.isChecked()
                                                    if hasattr(self, 'minimize_to_tray_checkbox') else False),
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
            self.model_path = config.get("model_path") or ""
            if config.get("mode", "single") == "router":
                self.router_mode_radio.setChecked(True)
            else:
                self.single_mode_radio.setChecked(True)
            self.router_settings.models_dir_lineedit.setText(str(config.get("models_dir", "")))
            self.router_settings.no_autoload_checkbox.setChecked(
                not config.get("no_models_autoload", True))
            self.router_settings.jinja_checkbox.setChecked(config.get("jinja", True))
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
            mtt = config.get("minimize_to_tray_on_close")
            if mtt is not None and hasattr(self, 'minimize_to_tray_checkbox'):
                self.minimize_to_tray_checkbox.setChecked(bool(mtt))
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
        """HuggingFace'den tek-model veya router klasörüne model indir."""
        router_mode = self.is_router_mode()
        initial_folder = (
            self.router_settings.models_dir_lineedit.text().strip()
            if router_mode else "")
        dialog = HfDownloaderDialog(
            translations_func=self.get_translated,
            parent=getattr(self, 'window', None),
            initial_folder=initial_folder)
        if dialog.exec():
            path = dialog.get_downloaded_path()
            if path and os.path.exists(path):
                sz = os.path.getsize(path) / (1024 * 1024)
                if router_mode:
                    self.log(self.get_translated(
                        "hf_router_model_downloaded",
                        "✓ Model router klasörüne indirildi: {file_path}").format(file_path=path))
                    self.log(self.get_translated(
                        "log_file_size", "  Dosya boyutu: {size:.2f} MB").format(size=sz))
                    if self.server_manager.is_running():
                        QTimer.singleShot(500, self.router_settings.refresh_models)
                    return

                self.model_path = path
                self.model_selector.set_model_path(path)
                self.log(self.get_translated(
                    "log_model_selected", "✓ Model seçildi: {file_path}").format(file_path=path))
                self.log(self.get_translated(
                    "log_file_size", "  Dosya boyutu: {size:.2f} MB").format(size=sz))
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
