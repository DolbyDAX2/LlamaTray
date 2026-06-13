"""
Gelişmiş Ayarlar Bileşeni.
GPU katmanları, context boyutu, port ve ek parametreler için ayarları içerir.
"""

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QLineEdit


class AdvancedSettingsWidget(QGroupBox):
    """Gelişmiş ayarlar grubu - GPU katmanları, context boyutu, port ve ek parametreler"""
    
    def __init__(self, translations_func=None):
        """
        Args:
            translations_func: Çeviri fonksiyonu (get_translated metodu)
        """
        super().__init__()
        self.translations_func = translations_func
        
        self._init_ui()
    
    def _init_ui(self):
        """UI'yi başlat"""
        self.setTitle(self.get_translated("advanced_group_title", "Gelişmiş Ayarlar"))
        
        layout = QVBoxLayout()
        
        # GPU Katmanları
        gpu_row = QHBoxLayout()
        self.gpu_layers_label = QLabel(self.get_translated("label_gpu_layers", "GPU Katmanları:"))
        self.gpu_layers_spinbox = QSpinBox()
        self.gpu_layers_spinbox.setRange(0, 200)
        self.gpu_layers_spinbox.setValue(99)
        self.gpu_layers_spinbox.setSuffix("")  # Suffix kaldırıldı, sadece label'da "GPU Katmanları:" görünüyor
        gpu_row.addWidget(self.gpu_layers_label)
        gpu_row.addWidget(self.gpu_layers_spinbox)
        
        # Context Boyutu
        context_row = QHBoxLayout()
        self.context_size_label = QLabel(self.get_translated("label_context_size", "Context Boyutu:"))
        self.context_size_combobox = QComboBox()
        self.context_size_combobox.addItems(["16384", "32768", "65536", "131072", "262144"])
        self.context_size_combobox.setCurrentText("32768")
        self.context_size_combobox.setEditable(True)
        from PyQt6.QtGui import QIntValidator
        self.context_size_combobox.lineEdit().setValidator(QIntValidator(512, 1000000))
        self.context_size_combobox.setCurrentIndex(0)
        context_row.addWidget(self.context_size_label)
        context_row.addWidget(self.context_size_combobox)
        
        # Port
        port_row = QHBoxLayout()
        self.port_label = QLabel(self.get_translated("label_port", "Port:"))
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1024, 65535)
        self.port_spinbox.setValue(8080)
        port_row.addWidget(self.port_label)
        port_row.addWidget(self.port_spinbox)
        
        # Ek Parametreler
        extra_row = QHBoxLayout()
        self.extra_params_label = QLabel(self.get_translated("label_extra_params", "Ek Parametreler:"))
        self.extra_params_lineedit = QLineEdit()
        self.extra_params_lineedit.setPlaceholderText(self.get_translated("placeholder_extra_params", "Örn: -t 8 --flash-attn"))
        extra_row.addWidget(self.extra_params_label)
        extra_row.addWidget(self.extra_params_lineedit)
        
        # Layout'a ekle
        layout.addLayout(gpu_row)
        layout.addLayout(context_row)
        layout.addLayout(port_row)
        layout.addLayout(extra_row)
        
        self.setLayout(layout)
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        if self.translations_func:
            return self.translations_func(key, default)
        return default
    
    def get_values(self):
        """Formdaki tüm değerleri dict olarak döndür"""
        try:
            context_size = int(self.context_size_combobox.currentText())
        except (ValueError, TypeError):
            context_size = 32768
        
        return {
            "gpu_layers": self.gpu_layers_spinbox.value(),
            "context_size": context_size,
            "port": self.port_spinbox.value(),
            "extra_args": self.extra_params_lineedit.text().strip()
        }
    
    def apply_values(self, values):
        """Dict değerlerini form alanlarına uygula"""
        # GPU katmanları
        gpu_layers = values.get("gpu_layers")
        if gpu_layers is not None:
            try:
                self.gpu_layers_spinbox.setValue(int(gpu_layers))
            except (ValueError, TypeError):
                pass
        
        # Context boyutu
        context_size = values.get("context_size")
        if context_size is not None:
            try:
                context_str = str(int(context_size))
                # Combobox'ta bu değer var mı kontrol et
                if self.context_size_combobox.findText(context_str) >= 0:
                    self.context_size_combobox.setCurrentText(context_str)
                else:
                    # Eğer listede yoksa, combobox'ı sıfırla ve sadece hazır seçenekleri ekle
                    self.context_size_combobox.blockSignals(True)
                    self.context_size_combobox.clear()
                    for item in ["16384", "32768", "65536", "131072", "262144"]:
                        self.context_size_combobox.addItem(item)
                    # Profilin custom değerini ekle (çünkü profil tarafından yükleniyor)
                    self.context_size_combobox.addItem(context_str)
                    self.context_size_combobox.setCurrentText(context_str)
                    self.context_size_combobox.blockSignals(False)
            except (ValueError, TypeError):
                pass
        
        # Port
        port = values.get("port")
        if port is not None:
            try:
                self.port_spinbox.setValue(int(port))
            except (ValueError, TypeError):
                pass
        
        # Ek parametreler
        extra_args = values.get("extra_args")
        if extra_args is not None:
            self.extra_params_lineedit.setText(str(extra_args))
    
    def get_widgets(self):
        """Tüm widget'ları döndür (dışarıdan erişim için)"""
        return {
            'gpu_layers_label': self.gpu_layers_label,
            'gpu_layers_spinbox': self.gpu_layers_spinbox,
            'context_size_label': self.context_size_label,
            'context_size_combobox': self.context_size_combobox,
            'port_label': self.port_label,
            'port_spinbox': self.port_spinbox,
            'extra_params_label': self.extra_params_label,
            'extra_params_lineedit': self.extra_params_lineedit,
        }
    
    def update_labels(self):
        """Tüm label'ları güncelle (dil değişimi için)"""
        # GroupBox başlığı
        self.setTitle(self.get_translated("advanced_group_title", "Gelişmiş Ayarlar"))
        
        # GPU Katmanları label
        self.gpu_layers_label.setText(self.get_translated("label_gpu_layers", "GPU Katmanları:"))
        
        # Context Boyutu label
        self.context_size_label.setText(self.get_translated("label_context_size", "Context Boyutu:"))
        
        # Port label
        self.port_label.setText(self.get_translated("label_port", "Port:"))
        
        # Ek Parametreler label
        self.extra_params_label.setText(self.get_translated("label_extra_params", "Ek Parametreler:"))
