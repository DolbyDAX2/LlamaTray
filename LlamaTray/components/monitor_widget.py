"""
Sistem Monitörü Bileşeni.
CPU, RAM, GPU ve VRAM kullanımını gösterir.
BaseWidget'dan türetilir.
"""

from .base_widget import ResourceMonitorBase


class SystemMonitorWidget(ResourceMonitorBase):
    """Sistem kaynaklarını (CPU, RAM, GPU, VRAM) gösteren widget"""
    
    def __init__(self, system_monitor, translations_func=None):
        """
        Args:
            system_monitor: SystemMonitor instance
            translations_func: Çeviri fonksiyonu (get_translated metodu)
        """
        super().__init__(system_monitor, translations_func)
