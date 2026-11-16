"""
models.ini Dosya Oluşturucu ve Görsel Düzenleyici Bileşeni.
llama-server Router Modu için models.ini dosyalarını otomatik üretir,
görsel tablo ve ham metin sekmeleriyle düzenleme imkanı sağlar.
"""

import os
import re
import tempfile

from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QPlainTextEdit, QSpinBox, QComboBox, QFileDialog, QMessageBox,
    QWidget, QGroupBox
)


def clean_alias_from_filename(filename: str, parent_dir_name: str = "") -> str:
    """GGUF dosya adından temiz, okunaklı bir model alias/ID'si türetir."""
    # Eğer model kendine ait özel bir alt klasördeyse (örn. Gemma4-12b/) klasör adını baz al
    if parent_dir_name and parent_dir_name.lower() not in ("models", "ai_models", "gguf", "bin"):
        clean_dir = re.sub(r'[^\w\.-]', '-', parent_dir_name).strip('-').lower()
        if len(clean_dir) >= 3:
            return clean_dir

    name = os.path.splitext(filename)[0]
    # Sık kullanılan kuantizasyon uzantılarını temizle (-Q4_K_M, -Q8_0, -UD-IQ3_XXS vb.)
    name = re.sub(r'[-_](Q\d+_[A-Z0-9_]+|IQ\d+_[A-Z0-9_]+|UD-[A-Z0-9_]+|FP16|BF16|F16|F32)$', '', name, flags=re.IGNORECASE)
    # -Instruct, -chat, -GGUF eklerini temizle
    name = re.sub(r'[-_](Instruct|Chat|GGUF|it)$', '', name, flags=re.IGNORECASE)
    clean = re.sub(r'[^\w\.-]', '-', name).strip('-').lower()
    return clean or "model"


def parse_ini_content(text: str) -> dict:
    """
    Standart configparser'ın 'version = 1' gibi başsız satırlarda patlamasını
    önleyen, esnek ve güvenli INI ayrıştırıcı.
    
    Returns:
        {
            '__root__': {'version': '1', ...},
            '*': {'n-gpu-layers': '99', 'ctx-size': '8192', 'fa': 'on'},
            'model_alias': {'model': '...', 'n-gpu-layers': '99', ...}
        }
    """
    sections = {}
    current_sec = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        m = re.match(r'^\[(.*?)\]$', line)
        if m:
            current_sec = m.group(1).strip()
            sections[current_sec] = {}
        elif '=' in line:
            k, v = line.split('=', 1)
            k, v = k.strip().lower(), v.strip()
            if current_sec is not None:
                sections[current_sec][k] = v
            else:
                sections.setdefault('__root__', {})[k] = v
    return sections


def save_text_atomic(file_path: str, content: str) -> bool:
    """Metin içeriğini belirtilen dosyaya atomik (.tmp + replace) olarak kaydeder."""
    dir_name = os.path.dirname(os.path.abspath(file_path)) or "."
    os.makedirs(dir_name, exist_ok=True)
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix=".tmp_ini_", suffix=".ini", dir=dir_name)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, file_path)
        return True
    except Exception:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise


def generate_default_models_ini(models_dir: str, target_path: str = None) -> str:
    """
    Belirtilen klasördeki ve alt klasörlerindeki .gguf dosyalarını tarayarak
    standart bir models.ini üretir.
    
    Returns:
        Oluşturulan models.ini dosyasının mutlak yolu.
    """
    if not models_dir or not os.path.isdir(models_dir):
        raise ValueError(f"Geçersiz model klasörü: {models_dir}")

    gguf_files = []
    mmproj_files = []

    # Alt klasörleri de kapsayacak şekilde derinlemesine tara
    for root, _dirs, files in os.walk(models_dir):
        for f in sorted(files):
            full_path = os.path.join(root, f)
            lower = f.lower()
            if lower.endswith(".gguf"):
                if "mmproj" in lower:
                    mmproj_files.append(full_path)
                else:
                    gguf_files.append(full_path)
            elif lower.endswith(".mmproj"):
                mmproj_files.append(full_path)

    if not gguf_files:
        raise ValueError(f"Klasörde ve alt klasörlerde .gguf uzantılı model dosyası bulunamadı: {models_dir}")

    out_path = target_path or os.path.join(models_dir, "models.ini")

    lines = [
        "version = 1",
        "",
        "# Global defaults applied across all models",
        "[*]",
        "n-gpu-layers = 99",
        "ctx-size = 8192",
        ""
    ]

    used_aliases = set()
    for gguf in gguf_files:
        base = os.path.basename(gguf)
        parent_dir = os.path.basename(os.path.dirname(gguf))
        if os.path.abspath(os.path.dirname(gguf)) == os.path.abspath(models_dir):
            parent_dir = ""

        alias = clean_alias_from_filename(base, parent_dir)
        # Çakışma önleyici
        counter = 1
        orig_alias = alias
        while alias in used_aliases:
            alias = f"{orig_alias}-{counter}"
            counter += 1
        used_aliases.add(alias)

        lines.append(f"[{alias}]")
        lines.append(f"model = {gguf}")
        lines.append("n-gpu-layers = 99")
        lines.append("ctx-size = 8192")

        # mmproj eşleştirmesi: Önce aynı klasördekine bak, yoksa ada göre eşleştir
        matched_mmproj = None
        gguf_dir = os.path.dirname(gguf)
        for mm in mmproj_files:
            if os.path.dirname(mm) == gguf_dir:
                matched_mmproj = mm
                break
        if not matched_mmproj:
            base_no_ext = os.path.splitext(base)[0].lower()
            for mm in mmproj_files:
                mm_base = os.path.splitext(os.path.basename(mm))[0].lower()
                if mm_base in base_no_ext or base_no_ext in mm_base:
                    matched_mmproj = mm
                    break

        if matched_mmproj:
            lines.append(f"mmproj = {matched_mmproj}")

        lines.append("")

    content = "\n".join(lines).strip() + "\n"
    save_text_atomic(out_path, content)
    return out_path


class ModelsIniEditorDialog(QDialog):
    """models.ini düzenleyici — Görsel tablo ve ham metin sekmeli diyalog."""

    ini_saved = pyqtSignal(str)

    def __init__(self, ini_path: str, translations_func=None,
                 is_server_running_func=None, restart_server_func=None, parent=None):
        super().__init__(parent)
        self.ini_path = ini_path
        self.translations_func = translations_func
        self.is_server_running_func = is_server_running_func or (lambda: False)
        self.restart_server_func = restart_server_func
        self._global_extra_keys = {}
        self._table_modified = False

        self.setWindowTitle(self.tr("models_ini_editor_title", "models.ini Preset Düzenleyici"))
        self.resize(860, 560)
        self.setMinimumSize(700, 460)
        self._build_ui()
        self._load_file_into_ui()

    def tr(self, key, default=""):
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Üst bilgi
        header_layout = QHBoxLayout()
        path_label = QLabel(f"<b>{self.tr('models_ini_file', 'Dosya:')}</b> {self.ini_path}")
        header_layout.addWidget(path_label)
        layout.addLayout(header_layout)

        # Sekmeler
        self.tabs = QTabWidget()

        # 1. Sekme: Görsel Düzenleyici
        visual_tab = QWidget()
        visual_layout = QVBoxLayout(visual_tab)

        # Global Defaults [*] Kutusu
        defaults_group = QGroupBox(self.tr("models_ini_global_defaults", "Genel Varsayılanlar [*] (Dosyada belirtilmeyen modeller için)"))
        def_layout = QHBoxLayout(defaults_group)
        self.default_gpu_label = QLabel(self.tr("models_ini_col_gpu", "GPU Katmanları:"))
        self.default_gpu_spinbox = QSpinBox()
        self.default_gpu_spinbox.setRange(0, 999)
        self.default_gpu_spinbox.setValue(99)
        self.default_gpu_spinbox.valueChanged.connect(self._mark_table_modified)

        self.default_ctx_label = QLabel(self.tr("models_ini_col_ctx", "Context Boyutu:"))
        self.default_ctx_combobox = QComboBox()
        self.default_ctx_combobox.setEditable(True)
        for v in ["4096", "8192", "16384", "32768", "65536", "131072"]:
            self.default_ctx_combobox.addItem(v)
        self.default_ctx_combobox.setCurrentText("8192")
        self.default_ctx_combobox.currentTextChanged.connect(self._mark_table_modified)

        def_layout.addWidget(self.default_gpu_label)
        def_layout.addWidget(self.default_gpu_spinbox)
        def_layout.addSpacing(20)
        def_layout.addWidget(self.default_ctx_label)
        def_layout.addWidget(self.default_ctx_combobox)
        def_layout.addStretch()
        visual_layout.addWidget(defaults_group)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.tr("models_ini_col_alias", "Takma Ad (Alias)"),
            self.tr("models_ini_col_model", "Model Dosyası"),
            self.tr("models_ini_col_gpu", "GPU Katmanları"),
            self.tr("models_ini_col_ctx", "Context Boyutu"),
            self.tr("models_ini_col_mmproj", "mmproj Dosyası")
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(lambda _item: self._mark_table_modified())
        visual_layout.addWidget(self.table)

        # Tablo butonları
        btn_row = QHBoxLayout()
        add_btn = QPushButton(self.tr("models_ini_add_row", "➕ Model Ekle"))
        add_btn.clicked.connect(lambda: self._add_table_row("", "", 99, 8192, ""))
        remove_btn = QPushButton(self.tr("models_ini_remove_row", "➖ Seçiliyi Sil"))
        remove_btn.clicked.connect(self._remove_selected_row)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        visual_layout.addLayout(btn_row)

        self.tabs.addTab(visual_tab, self.tr("models_ini_tab_visual", "📊 Görsel Tablo"))

        # 2. Sekme: Ham Metin (Raw INI)
        raw_tab = QWidget()
        raw_layout = QVBoxLayout(raw_tab)
        self.raw_text_edit = QPlainTextEdit()
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.raw_text_edit.setFont(font)
        raw_layout.addWidget(self.raw_text_edit)
        self.tabs.addTab(raw_tab, self.tr("models_ini_tab_raw", "📝 Ham Metin (INI)"))

        # Sinyal bağlantısı sekmeler ve raw_text_edit oluşturulduktan SONRA yapılmalı
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs)

        # Alt Butonlar (Kaydet / Harici Editörde Aç / Yeniden Yükle / İptal)
        action_row = QHBoxLayout()
        open_ext_btn = QPushButton(self.tr("models_ini_open_external", "↗️ Harici Editörde Aç"))
        open_ext_btn.clicked.connect(self._open_in_external_editor)
        action_row.addWidget(open_ext_btn)

        reload_btn = QPushButton(self.tr("models_ini_reload", "🔄 Yeniden Yükle"))
        reload_btn.clicked.connect(self._reload_from_file)
        action_row.addWidget(reload_btn)

        action_row.addStretch()

        save_btn = QPushButton(self.tr("models_ini_save", "💾 Kaydet"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton(self.tr("hf_button_cancel", "İptal"))
        cancel_btn.clicked.connect(self.reject)
        action_row.addWidget(save_btn)
        action_row.addWidget(cancel_btn)
        layout.addLayout(action_row)

    def _mark_table_modified(self):
        self._table_modified = True

    def _open_in_external_editor(self):
        """Dosyayı sistemin varsayılan metin editöründe (Kate, Gedit, VS Code vb.) açar."""
        if not os.path.exists(self.ini_path):
            self._save_file_only()
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.ini_path))

    def _reload_from_file(self):
        """Dosyayı diskten tekrar okuyarak hem tabloyu hem metin editörünü günceller."""
        self._load_file_into_ui()
        QMessageBox.information(self, self.tr("hf_success_title", "Başarılı"),
                                self.tr("models_ini_reloaded", "Dosya diskten yeniden yüklendi."))

    def _load_file_into_ui(self):
        if not os.path.exists(self.ini_path):
            default_content = "version = 1\n\n[*]\nn-gpu-layers = 99\nctx-size = 8192\n"
            self.raw_text_edit.setPlainText(default_content)
            self._parse_raw_to_table(default_content)
            self._table_modified = False
            return

        try:
            with open(self.ini_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.raw_text_edit.setPlainText(content)
            self._parse_raw_to_table(content)
            self._table_modified = False
        except Exception as e:
            QMessageBox.warning(self, self.tr("hf_warning_title", "Uyarı"), f"Dosya okunamadı: {e}")

    def _parse_raw_to_table(self, content: str):
        """Ham INI metnini görsel tabloya ve global değişkenlere güvenle aktarır."""
        self.table.blockSignals(True)
        self.default_gpu_spinbox.blockSignals(True)
        self.default_ctx_combobox.blockSignals(True)
        self.table.setRowCount(0)
        sections = parse_ini_content(content)

        # Global defaults [*] ve kullanıcı ek parametreleri (fa = on, temp vb.)
        self._global_extra_keys = {}
        if "*" in sections:
            g_sec = sections["*"]
            try:
                self.default_gpu_spinbox.setValue(int(g_sec.get("n-gpu-layers") or g_sec.get("gpu-layers") or 99))
            except ValueError:
                self.default_gpu_spinbox.setValue(99)
            self.default_ctx_combobox.setCurrentText(str(g_sec.get("ctx-size") or "8192"))
            for k, v in g_sec.items():
                if k not in ("n-gpu-layers", "gpu-layers", "ctx-size"):
                    self._global_extra_keys[k] = v

        # Modeller
        for sec_name, sec_dict in sections.items():
            if sec_name in ("*", "__root__"):
                continue
            model = sec_dict.get("model", "")
            gpu_str = sec_dict.get("n-gpu-layers") or sec_dict.get("gpu-layers") or "99"
            ctx_str = sec_dict.get("ctx-size") or "8192"
            mmproj = sec_dict.get("mmproj", "")
            extra = {k: v for k, v in sec_dict.items() if k not in ("model", "n-gpu-layers", "gpu-layers", "ctx-size", "mmproj")}
            try:
                gpu = int(gpu_str)
            except ValueError:
                gpu = 99
            try:
                ctx = int(ctx_str)
            except ValueError:
                ctx = 8192
            self._add_table_row(sec_name, model, gpu, ctx, mmproj, extra)

        self.table.blockSignals(False)
        self.default_gpu_spinbox.blockSignals(False)
        self.default_ctx_combobox.blockSignals(False)

    def _build_raw_from_table(self) -> str:
        """Görsel tablodaki verileri ve tüm ekstra parametreleri standart INI metnine dönüştürür."""
        def_gpu = self.default_gpu_spinbox.value()
        def_ctx = self.default_ctx_combobox.currentText().strip() or "8192"

        lines = [
            "version = 1",
            "",
            "# Global defaults applied across all models",
            "[*]",
            f"n-gpu-layers = {def_gpu}",
            f"ctx-size = {def_ctx}",
        ]
        # Kullanıcının eklediği fa = on, temp vb. tüm ekstra parametreleri KORU
        for k, v in getattr(self, '_global_extra_keys', {}).items():
            lines.append(f"{k} = {v}")
        lines.append("")

        for row in range(self.table.rowCount()):
            alias_item = self.table.item(row, 0)
            alias = alias_item.text().strip() if alias_item else ""
            if not alias:
                continue

            # Model yolu
            model_widget = self.table.cellWidget(row, 1)
            model_path = model_widget.findChild(QLabel).text().strip() if model_widget else ""

            # GPU
            gpu_widget = self.table.cellWidget(row, 2)
            gpu_val = gpu_widget.value() if isinstance(gpu_widget, QSpinBox) else 99

            # Context
            ctx_widget = self.table.cellWidget(row, 3)
            ctx_val = ctx_widget.currentText().strip() if isinstance(ctx_widget, QComboBox) else "8192"

            # mmproj
            mmproj_widget = self.table.cellWidget(row, 4)
            mmproj_path = mmproj_widget.findChild(QLabel).text().strip() if mmproj_widget else ""

            lines.append(f"[{alias}]")
            if model_path:
                lines.append(f"model = {model_path}")
            lines.append(f"n-gpu-layers = {gpu_val}")
            lines.append(f"ctx-size = {ctx_val}")
            if mmproj_path:
                lines.append(f"mmproj = {mmproj_path}")

            # Modele özel ekstra anahtarları da koru
            extra = alias_item.data(Qt.ItemDataRole.UserRole) or {}
            for k, v in extra.items():
                lines.append(f"{k} = {v}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _on_tab_changed(self, index: int):
        if index == 1:
            # Görsel sekmeden Metin sekmesine geçiş: sadece tablo değiştirildiyse metni güncelle
            if self._table_modified:
                self.raw_text_edit.setPlainText(self._build_raw_from_table())
                self._table_modified = False
        else:
            # Metin sekmesinden Görsel sekmeye geçiş
            self._parse_raw_to_table(self.raw_text_edit.toPlainText())

    def _add_table_row(self, alias: str, model_path: str, gpu: int, ctx: int, mmproj: str, extra: dict = None):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 0. Alias
        alias_item = QTableWidgetItem(alias or f"model-{row + 1}")
        alias_item.setData(Qt.ItemDataRole.UserRole, extra or {})
        self.table.setItem(row, 0, alias_item)

        # 1. Model Yolu (Label + Browse Button)
        model_container = QWidget()
        m_layout = QHBoxLayout(model_container)
        m_layout.setContentsMargins(4, 2, 4, 2)
        m_label = QLabel(model_path)
        m_label.setToolTip(model_path)
        m_btn = QPushButton("📁")
        m_btn.setFixedWidth(28)
        m_btn.clicked.connect(lambda _c=False, lbl=m_label: self._browse_file(lbl, "GGUF Files (*.gguf);;All Files (*)"))
        m_layout.addWidget(m_label, 1)
        m_layout.addWidget(m_btn)
        self.table.setCellWidget(row, 1, model_container)

        # 2. GPU Layers SpinBox
        gpu_spin = QSpinBox()
        gpu_spin.setRange(0, 999)
        gpu_spin.setValue(gpu)
        gpu_spin.valueChanged.connect(self._mark_table_modified)
        self.table.setCellWidget(row, 2, gpu_spin)

        # 3. Context Size ComboBox
        ctx_combo = QComboBox()
        ctx_combo.setEditable(True)
        for val in ["4096", "8192", "16384", "32768", "65536", "131072"]:
            ctx_combo.addItem(val)
        ctx_combo.setCurrentText(str(ctx))
        ctx_combo.currentTextChanged.connect(self._mark_table_modified)
        self.table.setCellWidget(row, 3, ctx_combo)

        # 4. mmproj (Label + Browse Button)
        mm_container = QWidget()
        mm_layout = QHBoxLayout(mm_container)
        mm_layout.setContentsMargins(4, 2, 4, 2)
        mm_label = QLabel(mmproj)
        mm_label.setToolTip(mmproj)
        mm_btn = QPushButton("📁")
        mm_btn.setFixedWidth(28)
        mm_btn.clicked.connect(lambda _c=False, lbl=mm_label: self._browse_file(lbl, "mmproj Files (*.mmproj);;All Files (*)"))
        mm_layout.addWidget(mm_label, 1)
        mm_layout.addWidget(mm_btn)
        self.table.setCellWidget(row, 4, mm_container)

    def _browse_file(self, label: QLabel, file_filter: str):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("button_model_select", "Dosya Seç"),
                                              label.text() or os.path.expanduser("~"), file_filter)
        if path:
            label.setText(path)
            label.setToolTip(path)
            self._mark_table_modified()

    def _remove_selected_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._mark_table_modified()

    def _save_file_only(self):
        if self.tabs.currentIndex() == 0 and self._table_modified:
            content = self._build_raw_from_table()
        else:
            content = self.raw_text_edit.toPlainText().strip() + "\n"
        save_text_atomic(self.ini_path, content)

    def _save_and_close(self):
        try:
            self._save_file_only()
            self.ini_saved.emit(self.ini_path)

            # Sunucu o sırada aktifse kapat-aç sorusu sor
            if self.is_server_running_func():
                reply = QMessageBox.question(
                    self,
                    self.tr("models_ini_restart_title", "Sunucuyu Yeniden Başlat?"),
                    self.tr("models_ini_restart_prompt",
                            "models.ini kaydedildi. Değişikliklerin etkili olması için sunucunun yeniden başlatılması gerekir.\n\nSunucu şimdi yeniden başlatılsın mı?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes and self.restart_server_func:
                    self.restart_server_func()

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("hf_error_title", "Hata"), f"Kaydetme hatası: {e}")
