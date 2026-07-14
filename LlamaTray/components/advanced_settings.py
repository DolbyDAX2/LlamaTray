"""
Gelişmiş Ayarlar Bileşeni.
GPU katmanları, context boyutu, port ve ek parametreler için ayarları içerir.
"""

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox,
    QLineEdit, QPushButton, QFileDialog
)
from PyQt6.QtCore import QVariant

# Sampler preset değerleri - dil bağımsız anahtarlar kullanılır
SAMPLER_PRESETS = {
    "neutral": "--temp 0.7 --top-p 0.9 --top-k 40 --min-p 0.0 --repeat-penalty 1.0",
    "balanced": "--temp 0.5 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.05",
    "creative": "--temp 1.0 --top-p 0.99 --top-k 100 --min-p 0.0 --repeat-penalty 1.0",
    "precise": "--temp 0.1 --top-p 0.5 --top-k 10 --min-p 0.0 --repeat-penalty 1.1",
}

# Preset anahtar sırası: custom, neutral, balanced, creative, precise
SAMPLER_PRESET_KEYS = ["custom", "neutral", "balanced", "creative", "precise"]


class AdvancedSettingsWidget(QGroupBox):
    """Gelişmiş ayarlar grubu - GPU katmanları, context boyutu, port ve ek parametreler"""
    
    def __init__(self, translations_func=None):
        """
        Args:
            translations_func: Çeviri fonksiyonu (get_translated metodu)
        """
        super().__init__()
        self.translations_func = translations_func
        self._current_preset_key = "custom"  # Dil bağımsız mevcut preset anahtarı
        
        self._init_ui()
    
    def _on_preset_changed(self, preset_name):
        """Preset değişince ek parametreleri otomatik doldur"""
        # userData'dan dil bağımsız anahtarı al
        key = self.preset_combobox.currentData()
        if key and key in SAMPLER_PRESETS:
            self._current_preset_key = key
            self.extra_params_lineedit.blockSignals(True)
            self.extra_params_lineedit.setText(SAMPLER_PRESETS[key])
            self.extra_params_lineedit.blockSignals(False)
    
    def _on_extra_params_changed(self, text):
        """Kullanıcı ek parametreleri elle değiştirdiğinde preset'i 'custom'a çek"""
        current_key = self._current_preset_key
        if current_key in SAMPLER_PRESETS and text != SAMPLER_PRESETS[current_key]:
            self.preset_combobox.blockSignals(True)
            # custom anahtarının index'i 0'dır
            self.preset_combobox.setCurrentIndex(0)
            self._current_preset_key = "custom"
            self.preset_combobox.blockSignals(False)
    
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
        
        # Sampler Preset Dropdown (Ek Parametrelerin üstüne)
        preset_row = QHBoxLayout()
        self.preset_label = QLabel(self.get_translated("preset_label", "Sampler Preset:"))
        self.preset_combobox = QComboBox()
        # Dil bağımsız anahtarlarla öğeleri ekle, userData olarak anahtarı sakla
        for key in SAMPLER_PRESET_KEYS:
            if key == "custom":
                display_text = self.get_translated("preset_custom", "Özel")
            else:
                translation_key = f"preset_{key}"
                fallback = {"neutral": "Nötr", "balanced": "Dengeli", "creative": "Yaratıcı", "precise": "Kesin"}[key]
                display_text = self.get_translated(translation_key, fallback)
            self.preset_combobox.addItem(display_text, QVariant(key))
        self.preset_combobox.setCurrentIndex(0)
        self.preset_combobox.currentTextChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self.preset_label)
        preset_row.addWidget(self.preset_combobox)
        
        # Ek Parametreler
        extra_row = QHBoxLayout()
        self.extra_params_label = QLabel(self.get_translated("label_extra_params", "Ek Parametreler:"))
        self.extra_params_lineedit = QLineEdit()
        self.extra_params_lineedit.setPlaceholderText(self.get_translated("placeholder_extra_params", "Örn: -t 8 --flash-attn"))
        self.extra_params_lineedit.textChanged.connect(self._on_extra_params_changed)
        extra_row.addWidget(self.extra_params_label)
        extra_row.addWidget(self.extra_params_lineedit)
        
        # mmproj Dosyası
        mmproj_row = QHBoxLayout()
        self.mmproj_label = QLabel(self.get_translated("label_mmproj", "mmproj Dosyası:"))
        self.mmproj_lineedit = QLineEdit()
        self.mmproj_lineedit.setPlaceholderText(self.get_translated("placeholder_mmproj", "Örn: /home/kullanici/model.gguf"))
        self.mmproj_browse_button = QPushButton("📁")
        self.mmproj_browse_button.setFixedWidth(32)
        self.mmproj_browse_button.clicked.connect(self.browse_mmproj_file)
        mmproj_row.addWidget(self.mmproj_label)
        mmproj_row.addWidget(self.mmproj_lineedit)
        mmproj_row.addWidget(self.mmproj_browse_button)
        
        # Layout'a ekle
        layout.addLayout(gpu_row)
        layout.addLayout(context_row)
        layout.addLayout(port_row)
        layout.addLayout(preset_row)
        layout.addLayout(extra_row)
        layout.addLayout(mmproj_row)
        
        self.setLayout(layout)
    
    def get_translated(self, key, default=""):
        """Verilen anahtar için çeviriyi döndür"""
        if self.translations_func:
            return self.translations_func(key, default)
        return default
    
    def browse_mmproj_file(self):
        """mmproj dosyası seç"""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "GGUF Dosyası Seç",
            "",
            "GGUF Files (*.gguf);;All Files (*)"
        )
        if file_path:
            self.mmproj_lineedit.setText(file_path)
    
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
            self.extra_params_lineedit.blockSignals(True)
            self.extra_params_lineedit.setText(str(extra_args))
            self.extra_params_lineedit.blockSignals(False)
            
            # Parametreye uygun preset'i bul ve seç
            matched_key = None
            for key, value in SAMPLER_PRESETS.items():
                if str(extra_args) == value:
                    matched_key = key
                    break
            
            if matched_key:
                self.preset_combobox.blockSignals(True)
                self._current_preset_key = matched_key
                # userData'ya göre doğru index'i bul
                for i in range(self.preset_combobox.count()):
                    if self.preset_combobox.itemData(i) == matched_key:
                        self.preset_combobox.setCurrentIndex(i)
                        break
                self.preset_combobox.blockSignals(False)
            else:
                # Hiçbir preset'e uymuyor, custom seç
                self.preset_combobox.blockSignals(True)
                self._current_preset_key = "custom"
                self.preset_combobox.setCurrentIndex(0)
                self.preset_combobox.blockSignals(False)
        
        # mmproj dosyası
        mmproj_path = values.get("mmproj_path")
        if mmproj_path is not None:
            self.mmproj_lineedit.setText(str(mmproj_path))
    
    def get_widgets(self):
        """Tüm widget'ları döndür (dışarıdan erişim için)"""
        return {
            'gpu_layers_label': self.gpu_layers_label,
            'gpu_layers_spinbox': self.gpu_layers_spinbox,
            'context_size_label': self.context_size_label,
            'context_size_combobox': self.context_size_combobox,
            'port_label': self.port_label,
            'port_spinbox': self.port_spinbox,
            'preset_label': self.preset_label,
            'preset_combobox': self.preset_combobox,
            'extra_params_label': self.extra_params_label,
            'extra_params_lineedit': self.extra_params_lineedit,
            'mmproj_label': self.mmproj_label,
            'mmproj_lineedit': self.mmproj_lineedit,
            'mmproj_browse_button': self.mmproj_browse_button,
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
        
        # Sampler Preset label
        self.preset_label.setText(self.get_translated("preset_label", "Sampler Preset:"))
        # Preset combobox öğelerini güncelle - mevcut preset anahtarını koru
        self.preset_combobox.blockSignals(True)
        self.preset_combobox.clear()
        
        for key in SAMPLER_PRESET_KEYS:
            if key == "custom":
                display_text = self.get_translated("preset_custom", "Özel")
            else:
                translation_key = f"preset_{key}"
                fallback = {"neutral": "Nötr", "balanced": "Dengeli", "creative": "Yaratıcı", "precise": "Kesin"}[key]
                display_text = self.get_translated(translation_key, fallback)
            self.preset_combobox.addItem(display_text, QVariant(key))
        
        # Mevcut preset anahtarına göre doğru index'i bul ve seç
        current_key = self._current_preset_key
        for i in range(self.preset_combobox.count()):
            if self.preset_combobox.itemData(i) == current_key:
                self.preset_combobox.setCurrentIndex(i)
                break
        else:
            self.preset_combobox.setCurrentIndex(0)  # Varsayılan: Özel
        
        self.preset_combobox.blockSignals(False)
        
        # Ek Parametreler label
        self.extra_params_label.setText(self.get_translated("label_extra_params", "Ek Parametreler:"))
        self.extra_params_lineedit.setPlaceholderText(self.get_translated("placeholder_extra_params", "Örn: -t 8 --flash-attn"))
        
        # mmproj Dosyası label
        self.mmproj_label.setText(self.get_translated("label_mmproj", "mmproj Dosyası:"))
        self.mmproj_lineedit.setPlaceholderText(self.get_translated("placeholder_mmproj", "Örn: /home/kullanici/model.gguf"))
