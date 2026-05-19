#!/usr/bin/env python3
"""
LlamaTray - llama.cpp sunucusu için sistem tepsisi uygulaması

Bu modül, uygulamanın giriş noktasıdır (entry point).
"""

import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication
from .ui import LlamaTray


def main():
    """Ana uygulama fonksiyonu"""
    # Linux/KDE/Wayland üzerinde sistem tepsisi ve pencere ikonunun tanınması için AppID ayarı
    os.environ["QT_QPA_PLATFORM_THEME"] = "kde"

    app = QApplication(sys.argv)

    tray = LlamaTray()
    tray.window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()