#!/usr/bin/env python3
"""
LlamaTray - llama.cpp sunucusu için sistem tepsisi uygulaması

Bu modül, uygulamanın giriş noktasıdır (entry point).
"""

import signal
import sys
import os
from PyQt6.QtCore import QLockFile, QTimer
from PyQt6.QtWidgets import QApplication
from .ui import LlamaTray
from .ui_utils import cleanup_tray_icon


import traceback

def setup_crash_handler():
    """Uygulama crash olsa bile tray ikonunu temizlemek için handler kur"""
    original_excepthook = sys.excepthook

    def custom_excepthook(exc_type, exc_value, traceback_obj):
        """Hata oluştuğunda tray'i temizle, sonra exception göster"""
        print(f"❌ CRITICAL ERROR: {exc_type.__name__}: {exc_value}")
        traceback.print_exception(exc_type, exc_value, traceback_obj)
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

    # Aynı application ID ile ikinci Qt/portal kaydı oluşmasını engelle.
    # Özellikle GNOME Wayland'de ikinci süreç xdg-desktop-portal tarafında
    # "Connection already associated with an application ID" üretebilir.
    instance_lock = None
    try:
        lock_dir = os.path.expanduser("~/.cache/llamatray")
        os.makedirs(lock_dir, exist_ok=True)
        instance_lock = QLockFile(os.path.join(lock_dir, "llamatray.lock"))
        instance_lock.setStaleLockTime(10000)
        if not instance_lock.tryLock(100):
            print("⚠ LlamaTray zaten çalışıyor; mevcut pencere kullanılmaya devam ediyor.")
            return
    except Exception as exc:
        # Kilit altyapısı kullanılamazsa uygulamayı tray desteğinden mahrum bırakma.
        print(f"⚠ Tekil uygulama kilidi oluşturulamadı: {exc}")
        instance_lock = None

    # QT_QPA_PLATFORM_THEME ortam değişkenini dinamik olarak ayarla
    # Mevcut masaüstü ortamını tespit et ve ona göre ayar yap
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "kde" in desktop:
        os.environ["QT_QPA_PLATFORM_THEME"] = "kde"
    elif "gnome" in desktop:
        os.environ["QT_QPA_PLATFORM_THEME"] = "gnome"
    # Diğer ortamlarda (XFCE, i3, Sway, vs.) varsayılan Qt tema kullanılsın

    # Qt platform (xcb) başlatması başarısız olabilir; örneğin Wayland'da eksik
    # D-Bus/tray desteği veya minimal X11 kurulumlarında eksik libxcb kütüphaneleri.
    # Kullanıcıya işe yarayan bir mesaj göster, unhandled exception fırlatma.
    try:
        app = QApplication(sys.argv)
    except Exception as exc:
        print(f"❌ Qt could not be initialized: {exc}")
        print("   Hint: install the missing Qt/XCB runtime libraries (see install.sh),")
        print("         or set QT_QPA_PLATFORM (e.g. 'xcb') and try again.")
        sys.exit(1)

    # GNOME/Wayland görev çubuğu/dock ikon gruplama: masaüstü dosya adı
    # herhangi bir pencere oluşturulmadan ÖNCE ayarlanmalıdır.
    # NOT: '.desktop' uzantısı EKLENMEZ — Qt bunu otomatik ekler; uzantılı
    # yazmak "Unable to find desktop file" uyarısına neden olur.
    try:
        app.setDesktopFileName("llamatray")
    except Exception:
        pass  # Gruplama sadece bir iyileştirme; asla crash nedeni olmasın

    # Terminal'den Ctrl+C (SIGINT) ile nazik kapatma: Qt event loop C++ tarafında
    # block'lendiği için Python signal handler'ının çalışması için 500ms'lik
    # periyodik timer ile kontrol verilmesi gerekir; aksi halde Ctrl+C unhandled
    # KeyboardInterrupt traceback'i fırlatır.
    try:
        signal.signal(signal.SIGINT, lambda sig, frame: app.quit())
    except (ValueError, OSError):
        pass  # Ana thread dışında çağrılırsa vs. — varsayılan davranış kalsın
    _sigint_yield_timer = QTimer()
    _sigint_yield_timer.timeout.connect(lambda: None)
    _sigint_yield_timer.start(500)

    tray = LlamaTray()
    tray.window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()