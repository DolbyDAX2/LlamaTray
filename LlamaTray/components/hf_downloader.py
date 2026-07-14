"""
HuggingFace Model İndirici Dialogu.
HuggingFace Hub'dan model dosyalarını indirmek için kullanılır.
v1.3.0 — Model arama özelliği eklenmiştir.
"""

import os
import time
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QProgressBar, QMessageBox,
    QTabWidget, QListWidget, QListWidgetItem, QSplitter, QWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont


# ---------------------------------------------------------------------------
# Thread'ler
# ---------------------------------------------------------------------------

class DownloadThread(QThread):
    """Arka planda dosya indirme işlemini yapan thread"""
    progress = pyqtSignal(int, str)  # percentage, status_message
    finished = pyqtSignal(str)  # download_path
    error = pyqtSignal(str)  # error_message

    def __init__(self, url, save_path, translations_func=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self._cancel = False
        self.translations_func = translations_func

    def cancel(self):
        self._cancel = True

    def get_translated(self, key, default=""):
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=30)
            if response.status_code != 200:
                server_err = self.get_translated("hf_server_error", "Server error")
                self.error.emit(f"HTTP {response.status_code}: {server_err}")
                return

            total = int(response.headers.get('content-length', 0))
            downloaded = 0
            start_time = time.time()

            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancel:
                        try:
                            os.remove(self.save_path)
                        except OSError:
                            pass
                        self.error.emit("cancelled")
                        return

                    f.write(chunk)
                    downloaded += len(chunk)

                    elapsed = time.time() - start_time
                    speed_mbps = (downloaded / (1024 * 1024)) / elapsed if elapsed > 0 else 0

                    if total > 0:
                        pct = int((downloaded / total) * 100)
                        dl_mb = downloaded / (1024 * 1024)
                        tot_mb = total / (1024 * 1024)
                        self.progress.emit(pct, f"{dl_mb:.1f}/{tot_mb:.1f} MB ({speed_mbps:.1f} MB/s)")
                    else:
                        dl_mb = downloaded / (1024 * 1024)
                        self.progress.emit(0, f"{dl_mb:.1f} MB ({speed_mbps:.1f} MB/s)")

            self.finished.emit(self.save_path)
        except requests.exceptions.CancelledError:
            try:
                os.remove(self.save_path)
            except OSError:
                pass
            self.error.emit("cancelled")
        except Exception as e:
            try:
                os.remove(self.save_path)
            except OSError:
                pass
            self.error.emit(str(e))


class SearchThread(QThread):
    """HuggingFace API'den model arama thread'i"""
    progress = pyqtSignal(str)  # status message
    finished = pyqtSignal(list)  # list of (repo_id, downloads) tuples
    error = pyqtSignal(str)

    def __init__(self, query: str, limit: int = 20, translations_func=None):
        super().__init__()
        self.query = query
        self.limit = limit
        self.translations_func = translations_func

    def get_translated(self, key, default=""):
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def run(self):
        try:
            self.progress.emit(self.get_translated("hf_searching", "Searching..."))
            url = f"https://huggingface.co/api/models"
            params = {
                "search": self.query,
                "filter": "gguf",
                "sort": "downloads",
                "direction": "-1",
                "limit": self.limit,
            }
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                api_err = self.get_translated("hf_api_error", "API error")
                self.error.emit(f"HTTP {response.status_code}: {api_err}")
                return

            data = response.json()
            results = []
            for model in data:
                repo_id = model.get("id", "")
                downloads = model.get("downloads", 0)
                results.append((repo_id, downloads))
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FilesThread(QThread):
    """HuggingFace API'den repo dosyalarını çeken thread"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)  # list of (filename, size_bytes) tuples
    error = pyqtSignal(str)

    def __init__(self, repo_id: str, translations_func=None):
        super().__init__()
        self.repo_id = repo_id
        self.translations_func = translations_func

    def get_translated(self, key, default=""):
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def _get_file_size(self, fname: str) -> int:
        """HEAD isteği ile dosya boyutunu al — redirect takip + GET fallback"""
        url = f"https://huggingface.co/{self.repo_id}/resolve/main/{fname}"
        # 1. HEAD + redirect takibi
        try:
            resp = requests.head(url, timeout=15, allow_redirects=True)
            if resp.status_code in (200, 206):
                cl = resp.headers.get("content-length")
                if cl and int(cl) > 0:
                    return int(cl)
        except Exception:
            pass
        # 2. GET ile streaming başlatma (ilk chunk'tan sonra iptal et)
        try:
            resp = requests.get(url, stream=True, timeout=15)
            cl = resp.headers.get("content-length")
            if cl and int(cl) > 0:
                resp.close()
                return int(cl)
        except Exception:
            pass
        return 0

    def run(self):
        try:
            self.progress.emit(self.get_translated("hf_loading_files", "Loading files..."))
            url = f"https://huggingface.co/api/models/{self.repo_id}"
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                api_err = self.get_translated("hf_api_error", "API error")
                self.error.emit(f"HTTP {response.status_code}: {api_err}")
                return

            data = response.json()
            siblings = data.get("siblings", [])
            gguf_files = []
            for sibling in siblings:
                fname = sibling.get("rfilename", "")
                if fname.lower().endswith(".gguf"):
                    # HF API'de 'size' genellikle yok; HEAD ile al
                    size = sibling.get("size") or self._get_file_size(fname)
                    gguf_files.append((fname, size))
            # Sort alphabetically by filename
            gguf_files.sort(key=lambda x: x[0])
            self.finished.emit(gguf_files)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Ana Dialog
# ---------------------------------------------------------------------------

class HfDownloaderDialog(QDialog):
    """HuggingFace'den model indirme dialogu — Arama + Manuel sekmeler"""

    def __init__(self, translations_func=None, parent=None):
        super().__init__(parent)
        self.translations_func = translations_func
        self.download_thread = None
        self.search_thread = None
        self.files_thread = None
        self._build_ui()

    # ---- helpers ----

    def get_translated(self, key, default=""):
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def _fmt_downloads(self, count: int) -> str:
        """Download sayısını okunabilir formata çevir"""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K"
        return str(count)

    def _fmt_size(self, size_bytes: int) -> str:
        """Byte cinsinden boyutu okunabilir formata çevir"""
        if size_bytes >= 1_073_741_824:  # 1 GB
            return f"{size_bytes / 1_073_741_824:.2f} GB"
        elif size_bytes >= 1_048_576:  # 1 MB
            return f"{size_bytes / 1_048_576:.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"

    # ---- UI oluşturma ----

    def _build_ui(self):
        self.setWindowTitle(self.get_translated("dialog_hf_download_title", "HuggingFace'den Model İndir"))
        self.setMinimumSize(650, 550)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # ---------- QTabWidget ----------
        self.tabs = QTabWidget()

        # --- Sekme 1: Ara (Search) ---
        search_tab = self._build_search_tab()
        self.tabs.addTab(search_tab, self.get_translated("hf_tab_search", "🔍 Ara"))

        # --- Sekme 2: Manuel (Manual) ---
        manual_tab = self._build_manual_tab()
        self.tabs.addTab(manual_tab, self.get_translated("hf_tab_manual", "✏️ Manuel"))

        main_layout.addWidget(self.tabs)

        # ---------- Ortak: İndirme Klasörü ----------
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel(self.get_translated("hf_label_folder", "İndirme Klasörü:"))
        self.folder_input = QLineEdit()
        self.folder_browse = QPushButton("📁")
        self.folder_browse.setFixedWidth(32)
        self.folder_browse.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.folder_browse)
        main_layout.addLayout(folder_layout)

        # ---------- Ortak: Progress Bar ----------
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-style: italic; color: gray; padding: 4px;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)

        # ---------- Ortak: Butonlar ----------
        button_layout = QHBoxLayout()
        self.download_button = QPushButton(self.get_translated("hf_button_download", "İndir"))
        self.download_button.clicked.connect(self._start_download)
        self.cancel_button = QPushButton(self.get_translated("hf_button_cancel", "İptal"))
        self.cancel_button.clicked.connect(self._cancel_download)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    # ---- Search Tab ----

    def _build_search_tab(self) -> QWidget:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Arama çubuğu
        search_bar = QHBoxLayout()
        search_bar.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            self.get_translated("hf_placeholder_search", "Örn: Qwen3 27B, gemma 4, llava")
        )
        self.search_input.returnPressed.connect(self._do_search)
        search_bar.addWidget(self.search_input)

        self.search_button = QPushButton(
            self.get_translated("hf_button_search", "Ara")
        )
        self.search_button.clicked.connect(self._do_search)
        search_bar.addWidget(self.search_button)
        layout.addLayout(search_bar)

        # Splitter: Sol (modeller) / Sağ (dosyalar)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sol: Model listesi
        self.model_list = QListWidget()
        self.model_list.itemClicked.connect(self._on_model_clicked)
        model_header = QLabel(
            self.get_translated("hf_model_list_title", "Modeller (downloads'a göre)")
        )
        model_header.setStyleSheet("font-weight: bold; padding: 4px;")
        sol_layout = QVBoxLayout()
        sol_layout.setContentsMargins(0, 0, 0, 0)
        sol_layout.addWidget(model_header)
        sol_layout.addWidget(self.model_list)
        sol_widget = QWidget()
        sol_widget.setLayout(sol_layout)
        splitter.addWidget(sol_widget)

        # Sağ: Dosya listesi
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._on_file_clicked)
        file_header = QLabel(
            self.get_translated("hf_file_list_title", "GGUF Dosyaları")
        )
        file_header.setStyleSheet("font-weight: bold; padding: 4px;")
        sag_layout = QVBoxLayout()
        sag_layout.setContentsMargins(0, 0, 0, 0)
        sag_layout.addWidget(file_header)
        sag_layout.addWidget(self.file_list)
        sag_widget = QWidget()
        sag_widget.setLayout(sag_layout)
        splitter.addWidget(sag_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # İpucu
        hint = QLabel(self.get_translated("hf_search_hint",
            "💡 Bir modele tıklayın → GGUF dosyaları sağda listelenir. Dosyaya tıklayın → Alanlar otomatik dolar."))
        hint.setStyleSheet("font-size: 11px; color: gray; padding: 4px;")
        layout.addWidget(hint)

        tab_widget = QWidget()
        tab_widget.setLayout(layout)
        return tab_widget

    # ---- Manual Tab ----

    def _build_manual_tab(self) -> QWidget:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # HuggingFace Repo
        repo_layout = QHBoxLayout()
        self.repo_label = QLabel(self.get_translated("hf_label_repo", "HuggingFace Repo:"))
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText(
            self.get_translated("hf_placeholder_repo", "Örn: unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF")
        )
        repo_layout.addWidget(self.repo_label)
        repo_layout.addWidget(self.repo_input)

        # Dosya Adı
        file_layout = QHBoxLayout()
        self.file_label = QLabel(self.get_translated("hf_label_filename", "Dosya Adı:"))
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText(
            self.get_translated("hf_placeholder_filename", "Örn: Qwen3-VL-30B-A3B-Instruct-UD-IQ3_XXS.gguf")
        )
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_input)

        layout.addLayout(repo_layout)
        layout.addLayout(file_layout)

        # İpucu
        hint = QLabel(self.get_translated("hf_manual_hint",
            "💡 Repo ve dosya adını elle yazın veya 'Ara' sekmesinden otomatik seçin."))
        hint.setStyleSheet("font-size: 11px; color: gray; padding: 4px;")
        layout.addWidget(hint)

        tab_widget = QWidget()
        tab_widget.setLayout(layout)
        return tab_widget

    # ---- Arama işlemleri ----

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self,
                self.get_translated("hf_warning_title", "Uyarı"),
                self.get_translated("hf_search_empty", "⚠ Arama terimi boş olamaz."))
            return

        # UI'yi kilitle
        self.search_button.setEnabled(False)
        self.search_input.setEnabled(False)
        self.model_list.clear()
        self.file_list.clear()
        self.status_label.setText(self.get_translated("hf_searching", "Aranıyor..."))
        self.status_label.setStyleSheet("color: blue; font-style: italic;")

        self.search_thread = SearchThread(query, translations_func=self.translations_func)
        self.search_thread.progress.connect(
            lambda msg: self.status_label.setText(msg))
        self.search_thread.finished.connect(self._on_search_results)
        self.search_thread.error.connect(self._on_search_error)
        self.search_thread.start()

    def _on_search_results(self, results: list):
        """results: list of (repo_id, downloads)"""
        self.search_thread.wait()
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)

        self.model_list.clear()
        for repo_id, downloads in results:
            display = f"{repo_id}  ({self._fmt_downloads(downloads)} ⬇)"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, repo_id)
            self.model_list.addItem(item)

        if not results:
            self.status_label.setText(self.get_translated("hf_no_results", "Sonuç bulunamadı."))
            self.status_label.setStyleSheet("color: orange; font-style: italic;")
        else:
            self.status_label.setText(
                self.get_translated("hf_results_found", "✓ {count} sonuç bulundu. Bir model seçin.").format(count=len(results)))
            self.status_label.setStyleSheet("color: green; font-style: italic;")

    def _on_search_error(self, error_msg):
        self.search_thread.wait()
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)
        self.status_label.setText(
            self.get_translated("hf_search_error_status", "❌ Arama hatası: {error}").format(error=error_msg))
        self.status_label.setStyleSheet("color: red; font-style: italic;")
        QMessageBox.critical(self,
            self.get_translated("hf_search_error_title", "Arama Hatası"), error_msg)

    def _on_model_clicked(self, item: QListWidgetItem):
        """Model seçildi → dosyalarını çek"""
        repo_id = item.data(Qt.ItemDataRole.UserRole)
        self.file_list.clear()
        self.status_label.setText(self.get_translated("hf_loading_files", "Dosyalar yükleniyor..."))
        self.status_label.setStyleSheet("color: blue; font-style: italic;")

        # Repo inputunu doldur (manuel sekmede de görünür)
        self.repo_input.setText(repo_id)

        self.files_thread = FilesThread(repo_id, translations_func=self.translations_func)
        self.files_thread.progress.connect(
            lambda msg: self.status_label.setText(msg))
        self.files_thread.finished.connect(self._on_files_results)
        self.files_thread.error.connect(self._on_files_error)
        self.files_thread.start()

    def _on_files_results(self, files: list):
        """files: list of (filename, size_bytes) tuples"""
        self.files_thread.wait()
        self.file_list.clear()
        for fname, size in files:
            display = f"{fname}  ({self._fmt_size(size)})"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, fname)
            self.file_list.addItem(item)

        if not files:
            self.status_label.setText(
                self.get_translated("hf_no_gguf_files", "Bu repoda .gguf dosyası bulunamadı."))
            self.status_label.setStyleSheet("color: orange; font-style: italic;")
        else:
            self.status_label.setText(
                self.get_translated("hf_files_found", "✓ {count} GGUF dosyası bulundu.").format(count=len(files)))
            self.status_label.setStyleSheet("color: green; font-style: italic;")

    def _on_files_error(self, error_msg):
        self.files_thread.wait()
        self.status_label.setText(
            self.get_translated("hf_files_error_status", "❌ Dosya listesi hatası: {error}").format(error=error_msg))
        self.status_label.setStyleSheet("color: red; font-style: italic;")
        QMessageBox.critical(self,
            self.get_translated("hf_files_error_title", "Dosya Listesi Hatası"), error_msg)

    def _on_file_clicked(self, item: QListWidgetItem):
        """Dosya seçildi → file_input'u doldur"""
        filename = item.data(Qt.ItemDataRole.UserRole) or item.text()
        self.file_input.setText(filename)
        # Manuel sekmeye geç
        self.tabs.setCurrentIndex(1)
        self.status_label.setText(
            self.get_translated("hf_file_selected", "✓ {filename} seçildi. İndirme klasörü seçip 'İndir'e basın.").format(filename=filename))
        self.status_label.setStyleSheet("color: green; font-style: italic;")

    # ---- İndirme işlemleri (mevcut kod korunur) ----

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self,
            self.get_translated("hf_folder_browse_title", "İndirme Klasörü Seç"))
        if folder:
            self.folder_input.setText(folder)

    def _start_download(self):
        repo = self.repo_input.text().strip()
        filename = self.file_input.text().strip()
        folder = self.folder_input.text().strip()

        # Validasyon
        if not repo or "/" not in repo:
            QMessageBox.warning(self,
                self.get_translated("hf_warning_title", "Uyarı"),
                self.get_translated("hf_invalid_repo", "⚠ Geçersiz repo formatı. 'user/repo' şeklinde olmalıdır."))
            return

        if not filename:
            QMessageBox.warning(self,
                self.get_translated("hf_error_title", "Hata"),
                self.get_translated("hf_filename_empty", "Dosya adı boş olamaz."))
            return

        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self,
                self.get_translated("hf_error_title", "Hata"),
                self.get_translated("hf_invalid_folder", "Geçerli bir indirme klasörü seçin."))
            return

        # URL oluştur
        url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
        save_path = os.path.join(folder, filename)

        self._set_download_state(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(self.get_translated("hf_downloading", "İndiriliyor..."))
        self.status_label.setStyleSheet("color: blue; font-style: italic;")

        self.download_thread = DownloadThread(url, save_path, translations_func=self.translations_func)
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.finished.connect(self._on_finished)
        self.download_thread.error.connect(self._on_error)
        self.download_thread.start()

    def _set_download_state(self, downloading: bool):
        """İndirme sırasında UI kilitle / aç"""
        enabled = not downloading
        self.download_button.setEnabled(enabled)
        self.cancel_button.setEnabled(downloading)
        self.repo_input.setEnabled(enabled)
        self.file_input.setEnabled(enabled)
        self.folder_input.setEnabled(enabled)
        self.folder_browse.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.search_button.setEnabled(enabled)

    def _cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.status_label.setText(
                f"{self.get_translated('hf_downloading', 'İndiriliyor...')} - {self.get_translated('hf_cancelling', 'İptal ediliyor...')}")

    def _on_progress(self, pct, message):
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{message}  (%p%)")
        self.status_label.setText(
            f"{self.get_translated('hf_downloading', 'İndiriliyor...')} — {message}")

    def _on_finished(self, path):
        self.download_thread.wait()
        self._set_download_state(False)
        self.progress_bar.setValue(100)
        complete_msg = self.get_translated("hf_download_complete", "✓ İndirme tamamlandı!")
        self.status_label.setText(complete_msg)
        self.status_label.setStyleSheet("color: green; font-style: italic;")

        QMessageBox.information(self,
            self.get_translated("hf_success_title", "Başarılı"),
            f"{complete_msg}\n\n{path}")

        self.setProperty("downloaded_path", path)
        self.accept()

    def _on_error(self, error_msg):
        self.download_thread.wait()
        self._set_download_state(False)

        if error_msg == "cancelled":
            self.status_label.setText(
                self.get_translated("hf_download_cancelled", "⚠ İndirme iptal edildi."))
            self.status_label.setStyleSheet("color: orange; font-style: italic;")
            self.progress_bar.setValue(0)
        else:
            msg = self.get_translated("hf_download_error", "❌ İndirme hatası: {error}").format(error=error_msg)
            self.status_label.setText(msg)
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            QMessageBox.critical(self,
                self.get_translated("hf_download_error_title", "İndirme Hatası"), msg)

    def get_downloaded_path(self):
        return self.property("downloaded_path") or ""

    # ---- Dil güncelleme ----

    def update_labels(self):
        """Çeviri etiketlerini güncelle (dil değişimi için)"""
        self.setWindowTitle(self.get_translated("dialog_hf_download_title", "HuggingFace'den Model İndir"))

        # Tab başlıkları
        self.tabs.setTabText(0, self.get_translated("hf_tab_search", "🔍 Ara"))
        self.tabs.setTabText(1, self.get_translated("hf_tab_manual", "✏️ Manuel"))

        # Manuel sekme
        self.repo_label.setText(self.get_translated("hf_label_repo", "HuggingFace Repo:"))
        self.repo_input.setPlaceholderText(
            self.get_translated("hf_placeholder_repo", "Örn: unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF"))
        self.file_label.setText(self.get_translated("hf_label_filename", "Dosya Adı:"))
        self.file_input.setPlaceholderText(
            self.get_translated("hf_placeholder_filename", "Örn: Qwen3-VL-30B-A3B-Instruct-UD-IQ3_XXS.gguf"))

        # Arama sekme
        self.search_input.setPlaceholderText(
            self.get_translated("hf_placeholder_search", "Örn: Qwen3 27B, gemma 4, llava"))
        self.search_button.setText(self.get_translated("hf_button_search", "Ara"))

        # Ortak
        self.folder_label.setText(self.get_translated("hf_label_folder", "İndirme Klasörü:"))
        self.download_button.setText(self.get_translated("hf_button_download", "İndir"))
        self.cancel_button.setText(self.get_translated("hf_button_cancel", "İptal"))
