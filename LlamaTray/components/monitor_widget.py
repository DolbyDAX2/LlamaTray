"""
Sistem Monitörü Bileşeni.
CPU, RAM, GPU ve VRAM kullanımını gösterir.
"""

from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout


class SystemMonitorWidget(QFrame):
    """Sistem kaynaklarını (CPU, RAM, GPU, VRAM) gösteren widget"""
    
    def __init__(self, system_monitor, translations_func=None):
        """
        Args:
            system_monitor: SystemMonitor instance
            translations_func: Çeviri fonksiyonu (get_translated metodu)
        """
        super().__init__()
        self.system_monitor = system_monitor
        self.translations_func = translations_func
        
        self._init_ui()
    
    def _init_ui(self):
        """UI'yi başlat"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # CPU
        self.cpu_label = QLabel("CPU Kullanımı: %0")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)
        
        # RAM
        self.ram_label = QLabel("RAM Kullanımı: %0")
        self.ram_progress = QProgressBar()
        self.ram_progress.setRange(0, 100)
        self.ram_progress.setValue(0)
        
        # GPU
        self.gpu_label = QLabel("GPU Kullanımı: %0")
        self.gpu_progress = QProgressBar()
        self.gpu_progress.setRange(0, 100)
        self.gpu_progress.setValue(0)
        
        # VRAM
        self.vram_label = QLabel("VRAM Kullanımı: %0")
        self.vram_progress = QProgressBar()
        self.vram_progress.setRange(0, 100)
        self.vram_progress.setValue(0)
        
        # GPU ve VRAM desteği kontrolü
        if not self.system_monitor.gpu_available:
            self.gpu_label.setText(self.get_translated("label_gpu_not_supported", "GPU: Desteklenmiyor"))
            self.gpu_progress.setVisible(False)
        if not self.system_monitor.vram_available:
            self.vram_label.setText(self.get_translated("label_vram_not_supported", "VRAM: Desteklenmiyor"))
            self.vram_progress.setVisible(False)
        
        # Layout'a ekle
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_progress)
        layout.addWidget(self.ram_label)
        layout.addWidget(self.ram_progress)
        layout.addWidget(self.gpu_label)
        layout.addWidget(self.gpu_progress)
        layout.addWidget(self.vram_label)
        layout.addWidget(self.vram_progress)
        
        self.setLayout(layout)
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        if self.translations_func:
            return self.translations_func(key, default)
        return default
    
    def update_monitor(self):
        """Sistem monitörünü güncelle"""
        try:
            # CPU
            try:
                cpu_usage = self.system_monitor.get_cpu_usage()
                label_text = self.get_translated("label_cpu_usage", "CPU Kullanımı: %0").replace("%0", f"{cpu_usage:.1f}")
                self.cpu_label.setText(label_text)
                self.cpu_progress.setValue(int(cpu_usage))
            except Exception:
                pass
            
            # RAM
            try:
                ram_usage = self.system_monitor.get_ram_usage()
                label_text = self.get_translated("label_ram_usage", "RAM Kullanımı: %0").replace("%0", f"{ram_usage:.1f}")
                self.ram_label.setText(label_text)
                self.ram_progress.setValue(int(ram_usage))
            except Exception:
                pass
            
            # GPU
            if self.system_monitor.gpu_available:
                try:
                    gpu_usage = self.system_monitor.get_gpu_usage()
                    if gpu_usage is not None:
                        label_text = self.get_translated("label_gpu_usage", "GPU Kullanımı: %0").replace("%0", f"{gpu_usage:.1f}")
                        self.gpu_label.setText(label_text)
                        self.gpu_progress.setValue(int(gpu_usage))
                except Exception:
                    pass
            
            # VRAM
            if self.system_monitor.vram_available:
                try:
                    vram_usage = self.system_monitor.get_vram_usage()
                    if vram_usage is not None:
                        label_text = self.get_translated("label_vram_usage", "VRAM Kullanımı: %0").replace("%0", f"{vram_usage:.1f}")
                        self.vram_label.setText(label_text)
                        self.vram_progress.setValue(int(vram_usage))
                except Exception:
                    pass
        except Exception:
            # Hata olursa sessiz kalsın
            pass
    
    def get_widgets(self):
        """Tüm progress bar widget'larını döndür (dışarıdan erişim için)"""
        return {
            'cpu_label': self.cpu_label,
            'cpu_progress': self.cpu_progress,
            'ram_label': self.ram_label,
            'ram_progress': self.ram_progress,
            'gpu_label': self.gpu_label,
            'gpu_progress': self.gpu_progress,
            'vram_label': self.vram_label,
            'vram_progress': self.vram_progress,
        }
    
    def update_labels(self):
        """Tüm label'ları güncelle (dil değişimi için)"""
        # CPU
        self.cpu_label.setText(self.get_translated("label_cpu_usage", "CPU Kullanımı: %0").replace("%0", "0"))
        
        # RAM
        self.ram_label.setText(self.get_translated("label_ram_usage", "RAM Kullanımı: %0").replace("%0", "0"))
        
        # GPU
        if self.system_monitor.gpu_available:
            self.gpu_label.setText(self.get_translated("label_gpu_usage", "GPU Kullanımı: %0").replace("%0", "0"))
        else:
            self.gpu_label.setText(self.get_translated("label_gpu_not_supported", "GPU: Desteklenmiyor"))
        
        # VRAM
        if self.system_monitor.vram_available:
            self.vram_label.setText(self.get_translated("label_vram_usage", "VRAM Kullanımı: %0").replace("%0", "0"))
        else:
            self.vram_label.setText(self.get_translated("label_vram_not_supported", "VRAM: Desteklenmiyor"))
