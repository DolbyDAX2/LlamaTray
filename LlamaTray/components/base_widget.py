"""
Ortak Widget Sınıfı.
Componentlerde ortak UI elementlerini tanımlamak için base class.
"""

from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout


class ResourceMonitorBase(QFrame):
    """
    Ortak kaynak monitörü widget'ı.
    CPU, RAM, GPU ve VRAM göstergelerini içerir.
    """
    
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
    
    def update_resources(self):
        """Kaynak kullanımını güncelle"""
        try:
            cpu = self.system_monitor.get_cpu_usage()
            ram = self.system_monitor.get_ram_usage()
            
            if cpu is not None:
                self.cpu_label.setText(f"CPU Kullanımı: {cpu}%")
                self.cpu_progress.setValue(int(cpu))
            
            if ram is not None:
                self.ram_label.setText(f"RAM Kullanımı: {ram}%")
                self.ram_progress.setValue(int(ram))
            
            # GPU ve VRAM güncellemesi (opsiyonel)
            if self.system_monitor.gpu_available:
                gpu = self.system_monitor.get_gpu_usage()
                if gpu is not None:
                    self.gpu_label.setText(f"GPU Kullanımı: {gpu}%")
                    self.gpu_progress.setValue(int(gpu))
            
            if self.system_monitor.vram_available:
                vram = self.system_monitor.get_vram_usage()
                if vram is not None:
                    self.vram_label.setText(f"VRAM Kullanımı: {vram}%")
                    self.vram_progress.setValue(int(vram))
                    
        except Exception as e:
            print(f"⚠ Kaynak güncelleme hatası: {e}")
