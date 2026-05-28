"""
LlamaTray UI Yardımcı Modülleri.
Translation, cleanup ve diğer ortak fonksiyonları içerir.
"""

import os
import json
import atexit
from PyQt6.QtCore import QUrl


# Translation dosya yolu
TRANSLATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations.json")

# İkon yolu - sadece varsayılan ikon
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(CURRENT_DIR, "assets", "icon.png")

if not os.path.exists(ICON_PATH):
    print(f"!!! DIKKAT: İkon bulunamadi, aranan konum: {ICON_PATH}")


# Global referans - atexit için (ui.py ile senkronize)
_tray_instance = None


def load_translations():
    """Translation dosyasını yükle"""
    try:
        with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ Translation dosyası yüklenemedi: {e}")
        return {"tr": {}, "en": {}}


def cleanup_tray_icon():
    """Sistem tepsisindeki ikonları temizle - uygulama crash olsa bile çalıştırılmalı"""
    # ui.py'deki _tray_instance'ı kullan (senkronize)
    import sys
    global _tray_instance
    if 'LlamaTray.ui' in sys.modules:
        _tray_instance = sys.modules['LlamaTray.ui']._tray_instance
    try:
        if _tray_instance is not None:
            # Tray ikonunu gizle (Wayland/KDE uyumluluğu)
            try:
                _tray_instance.hide()
            except Exception as e:
                pass
            
            # Tray ikonunu bellekten sil
            try:
                _tray_instance.deleteLater()
            except Exception as e:
                pass
            
            # Eğer context menu varsa onu da sil
            try:
                if hasattr(_tray_instance, 'menu') and _tray_instance.menu:
                    _tray_instance.menu.close()
                    _tray_instance.menu.deleteLater()
            except Exception:
                pass
    except Exception:
        pass
    finally:
        _tray_instance = None


def cleanup_on_exit():
    """Uygulama çıkışında tüm süreçleri ve tray ikonunu temizle"""
    global _tray_instance
    try:
        if _tray_instance is not None:
            # Sunucuyu kapat
            try:
                if hasattr(_tray_instance, 'cleanup_server_process'):
                    _tray_instance.cleanup_server_process()
            except Exception:
                pass
            
            # Tray ikonunu temizle
            cleanup_tray_icon()
    except Exception:
        pass


def get_icon_path():
    """İkon yolunu döndür"""
    return ICON_PATH
