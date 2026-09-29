"""
LlamaTray UI Yardımcı Modülleri.
Translation, cleanup ve diğer ortak fonksiyonları içerir.
"""

import os
import json
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from PyQt6.QtCore import QUrl


# Translation dosya yolu
TRANSLATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations.json")

# İkon yolu - sadece varsayılan ikon
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(CURRENT_DIR, "assets", "llamatray.png")
ICON_PATH_ON = os.path.join(CURRENT_DIR, "assets", "llamatray (on).png")
ICON_PATH_ICO = os.path.join(CURRENT_DIR, "assets", "llamatray.ico")
ICON_PATH_ON_ICO = os.path.join(CURRENT_DIR, "assets", "llamatray (on).ico")

if not os.path.exists(ICON_PATH):
    print(f"!!! WARNING: Icon not found, searched at: {ICON_PATH}")


# Global referans - tek kaynak (ui.py __init__ içinde atanır)
_tray_instance = None
_logger = None


def get_log_file_path():
    """XDG uyumlu log dosyasının tam yolunu döndürür (~/.local/state/llamatray/llamatray.log)."""
    state_home = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    log_dir = os.path.join(state_home, "llamatray")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "llamatray.log")


def get_file_logger():
    """
    XDG uyumlu disk loglayıcı döndürür.
    Boyut sınırı: dosya başına 2 MB, 3 yedek dosya (maksimum ~8 MB).
    """
    global _logger
    if _logger is not None:
        return _logger

    log_path = get_log_file_path()
    logger = logging.getLogger("LlamaTray")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _logger = logger
    return _logger


def save_json_atomic(file_path, data, indent=2, ensure_ascii=False):
    """
    JSON verisini belirtilen dosyaya atomik olarak kaydeder.
    
    Veri önce hedef dosya ile aynı dizinde geçici bir dosyaya yazılır,
    flush ve fsync edilerek diske yazılması garanti edilir ve ardından
    os.replace ile atomik olarak asıl dosyanın üzerine taşınır.
    Bu işlem, ani çökmelerde verinin 0 bayt kalmasını engeller.
    """
    dir_name = os.path.dirname(os.path.abspath(file_path)) or "."
    os.makedirs(dir_name, exist_ok=True)
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix=".tmp_",
            suffix=".json",
            dir=dir_name
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, file_path)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise


def load_translations():
    """Translation dosyasını yükle"""
    try:
        with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ Translation file could not be loaded: {e}")
        return {"tr": {}, "en": {}}


def cleanup_tray_icon():
    """Sistem tepsisindeki ikonları temizle - uygulama crash olsa bile çalıştırılmalı"""
    global _tray_instance
    try:
        if _tray_instance is not None:
            # Tray ikonunu gizle (Wayland/KDE uyumluluğu)
            try:
                if hasattr(_tray_instance, 'tray_icon'):
                    _tray_instance.tray_icon.hide()
            except Exception:
                pass

            # Tray ikonunu bellekten sil
            try:
                if hasattr(_tray_instance, 'tray_icon'):
                    _tray_instance.tray_icon.deleteLater()
            except Exception:
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
    """Normal (sunucu kapalı) ikon yolunu döndür"""
    return ICON_PATH


def get_on_icon_path():
    """Sunucu açık durumundaki yeşil ikon yolunu döndür"""
    return ICON_PATH_ON


def get_tray_icon_path(server_running=False):
    """Tepsi için çoklu çözünürlüklü ikon yolunu döndür."""
    ico_path = ICON_PATH_ON_ICO if server_running else ICON_PATH_ICO
    png_path = ICON_PATH_ON if server_running else ICON_PATH
    return ico_path if os.path.exists(ico_path) else png_path