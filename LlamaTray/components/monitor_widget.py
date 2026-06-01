"""
Sistem Monitörü Bileşeni.
CPU, RAM, GPU ve VRAM kullanımını gösterir.
BaseWidget'dan türetilir.
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
        self.cpu_label = QLabel(self.get_translated("label_cpu_usage", "CPU Usage: %0").replace("%0", "0"))
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)
        
        # RAM
        label_ram = self.get_translated("label_ram_usage", "RAM: %0 GB / %1 GB")
        self.ram_label = QLabel(label_ram.replace("%0", "0").replace("%1", "0"))
        self.ram_progress = QProgressBar()
        self.ram_progress.setRange(0, 100)
        self.ram_progress.setValue(0)
        
        # GPU
        self.gpu_label = QLabel(self.get_translated("label_gpu_usage", "GPU Usage: %0").replace("%0", "0"))
        self.gpu_progress = QProgressBar()
        self.gpu_progress.setRange(0, 100)
        self.gpu_progress.setValue(0)
        
        # VRAM
        label_vram = self.get_translated("label_vram_usage", "VRAM: %0 GB / %1 GB")
        self.vram_label = QLabel(label_vram.replace("%0", "0").replace("%1", "0"))
        self.vram_progress = QProgressBar()
        self.vram_progress.setRange(0, 100)
        self.vram_progress.setValue(0)
        
        # GPU ve VRAM desteği kontrolü
        if not self.system_monitor.gpu_available:
            self.gpu_label.setText(self.get_translated("label_gpu_not_supported", "GPU: Not Supported"))
            self.gpu_progress.setVisible(False)
        if not self.system_monitor.vram_available:
            self.vram_label.setText(self.get_translated("label_vram_not_supported", "VRAM: Not Supported"))
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
    
    def update_labels(self):
        """Label'ları geçerli dile göre güncelle (dil değiştiğinde çağrılır)"""
        # CPU
        label_cpu = self.get_translated("label_cpu_usage", "CPU Usage: %0")
        self.cpu_label.setText(label_cpu.replace("%0", "0"))
        
        # RAM
        label_ram = self.get_translated("label_ram_usage", "RAM: %0 GB / %1 GB")
        self.ram_label.setText(label_ram.replace("%0", "0").replace("%1", "0"))
        
        # GPU
        if self.system_monitor.gpu_available:
            label_gpu = self.get_translated("label_gpu_usage", "GPU Usage: %0")
            self.gpu_label.setText(label_gpu.replace("%0", "0"))
        else:
            self.gpu_label.setText(self.get_translated("label_gpu_not_supported", "GPU: Not Supported"))
        
        # VRAM
        if self.system_monitor.vram_available:
            label_vram = self.get_translated("label_vram_usage", "VRAM: %0 GB / %1 GB")
            self.vram_label.setText(label_vram.replace("%0", "0").replace("%1", "0"))
        else:
            self.vram_label.setText(self.get_translated("label_vram_not_supported", "VRAM: Not Supported"))
    
    def update_resources(self):
        """Kaynak kullanımını güncelle"""
        try:
            cpu = self.system_monitor.get_cpu_usage()
            if cpu is not None:
                label_template = self.get_translated("label_cpu_usage", "CPU Usage: %0")
                self.cpu_label.setText(label_template.replace("%0", str(cpu)))
                self.cpu_progress.setValue(int(cpu))
            
            ram_pct = self.system_monitor.get_ram_usage()
            ram_info = self.system_monitor.get_ram_info()
            if ram_pct is not None and ram_info:
                used_gb, total_gb = ram_info
                label_template = self.get_translated("label_ram_usage", "RAM Usage: %0 GB / %1 GB")
                self.ram_label.setText(label_template.replace("%0", f"{used_gb:.1f}").replace("%1", f"{total_gb:.1f}"))
                self.ram_progress.setValue(int(ram_pct))
            
            # GPU ve VRAM güncellemesi (opsiyonel)
            if self.system_monitor.gpu_available:
                gpu = self.system_monitor.get_gpu_usage()
                if gpu is not None:
                    label_template = self.get_translated("label_gpu_usage", "GPU Usage: %0")
                    self.gpu_label.setText(label_template.replace("%0", str(int(gpu))))
                    self.gpu_progress.setValue(int(gpu))
            
            if self.system_monitor.vram_available:
                vram_pct = self.system_monitor.get_vram_usage()
                vram_info = self.system_monitor.get_vram_info()
                if vram_pct is not None and vram_info:
                    used_gb, total_gb = vram_info
                    label_template = self.get_translated("label_vram_usage", "VRAM Usage: %0 GB / %1 GB")
                    self.vram_label.setText(label_template.replace("%0", f"{used_gb:.1f}").replace("%1", f"{total_gb:.1f}"))
                    self.vram_progress.setValue(int(vram_pct))
                    
        except Exception as e:
            print(f"⚠ Resource update error: {e}")
