"""
LlamaTray - llama.cpp sunucusu için sistem tepsisi uygulaması
"""

from .version import __version__, VERSION_DISPLAY
from .ui import LlamaTray
from .ui_utils import cleanup_tray_icon, cleanup_on_exit

__all__ = [
    'LlamaTray', 'cleanup_tray_icon', 'cleanup_on_exit',
    '__version__', 'VERSION_DISPLAY',
]