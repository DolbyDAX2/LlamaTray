#!/usr/bin/env python3
"""
LlamaTray - llama.cpp sunucusu için sistem tepsisi uygulaması

Bu modül, uygulamanın giriş noktasıdır (entry point).
"""

import sys
import os
import ctypes
import atexit
from PyQt6.QtWidgets import QApplication
from .ui import LlamaTray, cleanup_tray_icon, cleanup_on_exit


def setup_crash_handler():
    """Uygulama crash olsa bile tray ikonunu temizlemek için handler kur"""
    original_excepthook = sys.excepthook
    
    def custom_excepthook(exc_type, exc_value, traceback_obj):
        """Hata oluştuğunda tray'i temizle, sonra exception göster"""
        print(f"❌ KRITIK HATA: {exc_type.__name__}: {exc_value}")
        try:
            cleanup_tray_icon()
        except Exception:
            pass
        # Orijinal exception handler'ı çağır
        original_excepthook(exc_type, exc_value, traceback_obj)
    
    sys.excepthook = custom_excepthook


def main():
    """Ana uygulama fonksiyonu"""
    # Crash handler'ı kur
    setup_crash_handler()
    
    # Uygulama çıkışında temizlik fonksiyonunu kaydet
    atexit.register(cleanup_tray_icon)
    
    # Linux/KDE/Wayland üzerinde sistem tepsisi ve pencere ikonunun tanınması için AppID ayarı
    os.environ["QT_QPA_PLATFORM_THEME"] = "kde"

    app = QApplication(sys.argv)
    
    # Uygulama "About to Quit" sinyalini bağla - en son temizlik
    app.aboutToQuit.connect(cleanup_tray_icon)

    tray = LlamaTray()
    tray.window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()