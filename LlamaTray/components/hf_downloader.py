"""
HuggingFace Model İndirici Dialogu.
HuggingFace Hub'dan model dosyalarını aramak, listelemek ve indirmek için kullanılır.
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, NamedTuple, Optional, Tuple

import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QProgressBar, QMessageBox,
    QTabWidget, QListWidget, QListWidgetItem, QSplitter, QWidget,
    QComboBox, QButtonGroup, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor


# ---------------------------------------------------------------------------
# Veri Yapıları ve Tema Yardımcıları
# ---------------------------------------------------------------------------

class HfModelInfo(NamedTuple):
    """HuggingFace model arama sonucu veri yapısı."""
    id: str
    downloads: int = 0
    likes: int = 0
    gated: bool = False
    last_modified: str = ""


def fmt_downloads(count: int) -> str:
    """Download ve beğeni sayısını okunabilir formata çevir."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def fmt_size(size_bytes: int) -> str:
    """Byte cinsinden boyutu okunabilir formata çevir."""
    if size_bytes >= 1_073_741_824:  # 1 GB
        return f"{size_bytes / 1_073_741_824:.2f} GB"
    elif size_bytes >= 1_048_576:  # 1 MB
        return f"{size_bytes / 1_048_576:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def is_recommended_quant(filename: str) -> bool:
    """Q4_K_M ve Q5_K_M gibi yaygın ve dengeli quantization'ları tespit eder."""
    fn = filename.upper()
    return bool(re.search(r'(?:^|[_\-.])(Q4_K_M|Q5_K_M)(?:[_\-.]|$)', fn))


def match_quant_filter(filename: str, filter_category: str) -> bool:
    """
    Dosya adının belirtilen quantization filtresi ile eşleşip eşleşmediğini kontrol eder.
    filter_category: 'all', 'q4', 'q5', 'q8', 'small'
    """
    if filter_category == "all":
        return True
    fn = filename.upper()
    if filter_category == "q4":
        return bool(re.search(r'(?:^|[_\-.])(?:I?Q4(?:_[A-Z0-9]+)?)(?:[_\-.]|$)', fn) or "Q4_" in fn or "IQ4" in fn)
    elif filter_category == "q5":
        return bool(re.search(r'(?:^|[_\-.])(?:I?Q5(?:_[A-Z0-9]+)?)(?:[_\-.]|$)', fn) or "Q5_" in fn or "IQ5" in fn)
    elif filter_category == "q8":
        return bool(re.search(r'(?:^|[_\-.])(?:I?Q8(?:_[A-Z0-9]+)?)(?:[_\-.]|$)', fn) or "Q8_" in fn or "IQ8" in fn or "Q8_0" in fn)
    elif filter_category == "small":
        return any(q in fn for q in ("Q2_", "IQ2", "Q3_", "IQ3")) or bool(re.search(r'(?:^|[_\-.])(?:I?Q[23](?:_[A-Z0-9]+)?)(?:[_\-.]|$)', fn))
    return True


def is_dark_theme(widget: Optional[QWidget] = None) -> bool:
    """Widget veya uygulama paletinin koyu (dark) tema olup olmadığını belirler."""
    palette = widget.palette() if widget is not None else QApplication.palette()
    bg = palette.color(palette.ColorRole.Window)
    lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
    return lum < 128


class ThemeColors:
    """Açık ve koyu tema için yüksek kontrastlı modern renk tanımları."""
    @staticmethod
    def get(dark: bool = True) -> dict:
        if dark:
            return {
                "card_bg": "rgba(255, 255, 255, 0.05)",
                "card_border": "rgba(255, 255, 255, 0.12)",
                "card_hover": "rgba(255, 255, 255, 0.09)",
                "text_primary": "#f3f4f6",
                "text_secondary": "#9ca3af",
                "badge_pub_bg": "rgba(255, 255, 255, 0.09)",
                "badge_pub_text": "#e2e8f0",
                "badge_pub_border": "rgba(255, 255, 255, 0.16)",
                "badge_dl_bg": "rgba(59, 130, 246, 0.22)",
                "badge_dl_text": "#60a5fa",
                "badge_dl_border": "rgba(96, 165, 250, 0.35)",
                "badge_likes_bg": "rgba(239, 68, 68, 0.22)",
                "badge_likes_text": "#f87171",
                "badge_likes_border": "rgba(248, 113, 113, 0.35)",
                "badge_gated_bg": "rgba(245, 158, 11, 0.22)",
                "badge_gated_text": "#fbbf24",
                "badge_gated_border": "rgba(251, 191, 36, 0.40)",
                "badge_reco_bg": "rgba(234, 179, 8, 0.25)",
                "badge_reco_text": "#fde047",
                "badge_reco_border": "rgba(253, 224, 71, 0.45)",
                "badge_size_bg": "rgba(255, 255, 255, 0.09)",
                "badge_size_text": "#e2e8f0",
                "badge_size_border": "rgba(255, 255, 255, 0.16)",
                "status_info": "#38bdf8",
                "status_success": "#4ade80",
                "status_warning": "#fbbf24",
                "status_error": "#f87171",
                "summary_bg": "rgba(255, 255, 255, 0.05)",
                "summary_border": "rgba(255, 255, 255, 0.14)",
                "summary_title": "#9ca3af",
                "filter_active_bg": "rgba(59, 130, 246, 0.35)",
                "filter_active_border": "#60a5fa",
                "filter_active_text": "#ffffff",
                "list_bg": "rgba(255, 255, 255, 0.02)",
                "list_border": "rgba(255, 255, 255, 0.10)",
            }
        else:
            return {
                "card_bg": "rgba(0, 0, 0, 0.03)",
                "card_border": "rgba(0, 0, 0, 0.10)",
                "card_hover": "rgba(0, 0, 0, 0.06)",
                "text_primary": "#111827",
                "text_secondary": "#6b7280",
                "badge_pub_bg": "rgba(0, 0, 0, 0.06)",
                "badge_pub_text": "#374151",
                "badge_pub_border": "rgba(0, 0, 0, 0.12)",
                "badge_dl_bg": "rgba(59, 130, 246, 0.12)",
                "badge_dl_text": "#1d4ed8",
                "badge_dl_border": "rgba(29, 78, 216, 0.25)",
                "badge_likes_bg": "rgba(239, 68, 68, 0.12)",
                "badge_likes_text": "#dc2626",
                "badge_likes_border": "rgba(220, 38, 38, 0.25)",
                "badge_gated_bg": "rgba(245, 158, 11, 0.15)",
                "badge_gated_text": "#b45309",
                "badge_gated_border": "rgba(180, 83, 9, 0.30)",
                "badge_reco_bg": "rgba(234, 179, 8, 0.18)",
                "badge_reco_text": "#854d0e",
                "badge_reco_border": "rgba(133, 77, 14, 0.35)",
                "badge_size_bg": "rgba(0, 0, 0, 0.06)",
                "badge_size_text": "#374151",
                "badge_size_border": "rgba(0, 0, 0, 0.12)",
                "status_info": "#0284c7",
                "status_success": "#16a34a",
                "status_warning": "#d97706",
                "status_error": "#dc2626",
                "summary_bg": "rgba(0, 0, 0, 0.03)",
                "summary_border": "rgba(0, 0, 0, 0.10)",
                "summary_title": "#6b7280",
                "filter_active_bg": "rgba(59, 130, 246, 0.18)",
                "filter_active_border": "#2563eb",
                "filter_active_text": "#1d4ed8",
                "list_bg": "rgba(0, 0, 0, 0.01)",
                "list_border": "rgba(0, 0, 0, 0.08)",
            }


def get_hf_token_path() -> str:
    """Kullanıcıya özel HF token dosyasının yolunu döndürür."""
    config_dir = os.path.join(os.path.expanduser("~"), ".llamatray")
    return os.path.join(config_dir, "hf_token")


def load_saved_hf_token() -> str:
    """Kaydedilmiş HF tokenını oku: önce ~/.llamatray/hf_token, sonra env var, sonra ~/.cache/huggingface/token."""
    token_file = get_hf_token_path()
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if token:
                    return token
        except OSError:
            pass
    env_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if env_token:
        return env_token.strip()
    hf_cache_token = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "token")
    if os.path.exists(hf_cache_token):
        try:
            with open(hf_cache_token, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if token:
                    return token
        except OSError:
            pass
    return ""


def save_hf_token(token: str):
    """HF tokenını güvenli izinle (~/.llamatray/hf_token, 0600) diske kaydeder."""
    token = token.strip()
    token_file = get_hf_token_path()
    config_dir = os.path.dirname(token_file)
    try:
        os.makedirs(config_dir, exist_ok=True)
        if not token:
            if os.path.exists(token_file):
                os.remove(token_file)
            return
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o600
        fd = os.open(token_file, flags, mode)
        with open(fd, "w", encoding="utf-8") as f:
            f.write(token)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Özel Widget'lar (Görsel Kartlar ve Etiketler)
# ---------------------------------------------------------------------------

class ElidedLabel(QLabel):
    """Genişliği aşan metinleri sağdan üç nokta (...) ile elide eden ve tooltip sunan etiket."""
    def __init__(self, text: str = "", text_color: str = "", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self._text_color = text_color
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(20)

    def setTextColor(self, color_str: str):
        self._text_color = color_str
        self.update()

    def setText(self, text: str):
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, max(10, self.width()))
        painter.setFont(self.font())
        if self._text_color:
            painter.setPen(QColor(self._text_color))
        else:
            painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.rect(), self.alignment() | Qt.AlignmentFlag.AlignVCenter, elided)


class RepoCardWidget(QFrame):
    """Hugging Face repo görsel kartı: üstte belirgin model adı, altta rozetler."""
    def __init__(self, repo_id: str, downloads: int = 0, likes: int = 0, is_gated: bool = False,
                 is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.repo_id = repo_id
        colors = ThemeColors.get(is_dark)

        self.setObjectName("RepoCardWidget")
        self.setStyleSheet(f"""
            #RepoCardWidget {{
                background-color: {colors["card_bg"]};
                border: 1px solid {colors["card_border"]};
                border-radius: 6px;
            }}
            #RepoCardWidget:hover {{
                background-color: {colors["card_hover"]};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(5)

        # Üst Satır: Model Adı (repo ID'nin / sonrası kısmı)
        parts = repo_id.split("/", 1)
        publisher = parts[0] if len(parts) > 1 else ""
        model_name = parts[1] if len(parts) > 1 else repo_id

        self.name_label = ElidedLabel(model_name, text_color=colors["text_primary"])
        font = self.name_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self.name_label.setFont(font)
        self.name_label.setToolTip(repo_id)
        self.name_label.setStyleSheet("border: none; background: transparent;")
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.name_label)

        # Alt Satır: Rozetler
        badge_layout = QHBoxLayout()
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(6)

        # Yayıncı rozeti: 👤 @publisher
        if publisher:
            pub_label = QLabel(f"👤 @{publisher}")
            pub_label.setStyleSheet(f"""
                background-color: {colors['badge_pub_bg']};
                color: {colors['badge_pub_text']};
                border: 1px solid {colors['badge_pub_border']};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 500;
            """)
            pub_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            badge_layout.addWidget(pub_label)

        # İndirme sayısı: ⬇️ 45.2K
        dl_str = fmt_downloads(downloads)
        dl_label = QLabel(f"⬇ {dl_str}")
        dl_label.setStyleSheet(f"""
            background-color: {colors['badge_dl_bg']};
            color: {colors['badge_dl_text']};
            border: 1px solid {colors['badge_dl_border']};
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: 600;
        """)
        dl_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        badge_layout.addWidget(dl_label)

        # Beğeni sayısı: ❤️ 120
        likes_str = fmt_downloads(likes)
        likes_label = QLabel(f"❤️ {likes_str}")
        likes_label.setStyleSheet(f"""
            background-color: {colors['badge_likes_bg']};
            color: {colors['badge_likes_text']};
            border: 1px solid {colors['badge_likes_border']};
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: 600;
        """)
        likes_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        badge_layout.addWidget(likes_label)

        # Gated rozeti: 🔒 Gated
        if is_gated:
            gated_label = QLabel("🔒 Gated")
            gated_label.setStyleSheet(f"""
                background-color: {colors['badge_gated_bg']};
                color: {colors['badge_gated_text']};
                border: 1px solid {colors['badge_gated_border']};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 700;
            """)
            gated_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            badge_layout.addWidget(gated_label)

        badge_layout.addStretch()
        layout.addLayout(badge_layout)


class GgufFileCardWidget(QFrame):
    """GGUF dosya kartı: dosya adı, ⭐ Önerilen rozeti ve boyut rozeti."""
    def __init__(self, filename: str, size_bytes: int, is_recommended: bool = False,
                 size_str: str = "", reco_text: str = "⭐ Önerilen", is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.filename = filename
        colors = ThemeColors.get(is_dark)

        self.setObjectName("GgufFileCardWidget")
        self.setStyleSheet(f"""
            #GgufFileCardWidget {{
                background-color: {colors['card_bg']};
                border: 1px solid {colors['card_border']};
                border-radius: 5px;
            }}
            #GgufFileCardWidget:hover {{
                background-color: {colors['card_hover']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Dosya Adı
        self.name_label = ElidedLabel(filename, text_color=colors["text_primary"])
        font = self.name_label.font()
        if is_recommended:
            font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet("border: none; background: transparent;")
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.name_label, 1)

        # ⭐ Önerilen rozeti
        if is_recommended:
            reco_badge = QLabel(reco_text)
            reco_badge.setStyleSheet(f"""
                background-color: {colors['badge_reco_bg']};
                color: {colors['badge_reco_text']};
                border: 1px solid {colors['badge_reco_border']};
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 11px;
                font-weight: 700;
            """)
            reco_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout.addWidget(reco_badge)

        # Boyut rozeti
        size_badge = QLabel(size_str)
        size_badge.setStyleSheet(f"""
            background-color: {colors['badge_size_bg']};
            color: {colors['badge_size_text']};
            border: 1px solid {colors['badge_size_border']};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
        """)
        size_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(size_badge)


# ---------------------------------------------------------------------------
# Thread'ler
# ---------------------------------------------------------------------------

class DownloadThread(QThread):
    """
    Arka planda dosya indirme işlemini yapan thread.
    - 1 MB tampon boyutu (chunk_size)
    - 150 ms UI sinyal throttle koruması (gigabit indirmelerde GUI kilitlenmesini engeller)
    - HTTP Range ile kesilen indirmeyi kaldığı yerden sürdürme (resume)
    - İsteğe bağlı Bearer token yetkilendirme (gated modeller için)
    """
    progress = pyqtSignal(int, str)  # percentage, status_message
    finished = pyqtSignal(str)       # download_path
    error = pyqtSignal(str)          # error_message

    def __init__(self, url: str, save_path: str, token: str = "", translations_func=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.token = token.strip() if token else ""
        self._cancel = False
        self.translations_func = translations_func

    def cancel(self):
        self._cancel = True

    def get_translated(self, key: str, default: str = "") -> str:
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def run(self):
        part_path = self.save_path + ".part"
        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            # Eğer hedef dosya tam olarak zaten inmişse baştan indirmeyi atla
            if os.path.exists(self.save_path) and not os.path.exists(part_path):
                try:
                    head_resp = requests.head(self.url, headers=headers, timeout=15, allow_redirects=True)
                    if head_resp.status_code == 200:
                        remote_len = int(head_resp.headers.get("content-length", 0))
                        local_len = os.path.getsize(self.save_path)
                        if remote_len > 0 and local_len == remote_len:
                            tot_mb = remote_len / (1024 * 1024)
                            self.progress.emit(100, f"{tot_mb:.1f}/{tot_mb:.1f} MB (100%)")
                            self.finished.emit(self.save_path)
                            return
                        elif remote_len > 0 and local_len < remote_len:
                            # Eski sürümden kalan kısmi inmiş dosyayı part_path'e taşı
                            os.replace(self.save_path, part_path)
                except Exception:
                    pass

            existing_bytes = os.path.getsize(part_path) if os.path.exists(part_path) else 0

            req_headers = dict(headers)
            if existing_bytes > 0:
                req_headers["Range"] = f"bytes={existing_bytes}-"

            response = requests.get(self.url, headers=req_headers, stream=True, timeout=30)

            # 416 Range Not Satisfiable: dosya zaten tam boyutuna ulaşmış olabilir
            if response.status_code == 416 and existing_bytes > 0:
                if os.path.exists(part_path):
                    os.replace(part_path, self.save_path)
                self.finished.emit(self.save_path)
                return

            # Gated / Yetki hataları (401 / 403)
            if response.status_code in (401, 403):
                gated_err = self.get_translated(
                    "hf_error_gated",
                    "Bu modele erişim izni gerekiyor. Lütfen geçerli bir Hugging Face Token girin."
                )
                self.error.emit(f"HTTP {response.status_code}: {gated_err}")
                return

            if response.status_code not in (200, 206):
                server_err = self.get_translated("hf_server_error", "Server error")
                self.error.emit(f"HTTP {response.status_code}: {server_err}")
                return

            # 206 = Kısmi içerik (Range kabul edildi), 200 = Tam içerik (sıfırdan)
            if response.status_code == 206:
                content_range = response.headers.get("content-range", "")
                if "/" in content_range:
                    try:
                        total = int(content_range.split("/")[-1])
                    except ValueError:
                        total = existing_bytes + int(response.headers.get("content-length", 0))
                else:
                    total = existing_bytes + int(response.headers.get("content-length", 0))
                file_mode = "ab"
                downloaded = existing_bytes
            else:
                total = int(response.headers.get("content-length", 0))
                file_mode = "wb"
                downloaded = 0

            start_time = time.time()
            last_emit_time = 0.0
            chunk_size = 1024 * 1024  # 1 MB chunk

            with open(part_path, file_mode) as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._cancel:
                        # İptal edildiğinde dosyayı silme, kaldığı yerden devam için koru
                        self.error.emit("cancelled")
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        # UI sinyalini 150 ms aralıkla throttle et
                        if now - last_emit_time >= 0.15:
                            elapsed = now - start_time
                            bytes_this_session = (downloaded - existing_bytes) if file_mode == "ab" else downloaded
                            speed_mbps = (bytes_this_session / (1024 * 1024)) / elapsed if elapsed > 0 else 0

                            if total > 0:
                                pct = int((downloaded / total) * 100)
                                dl_mb = downloaded / (1024 * 1024)
                                tot_mb = total / (1024 * 1024)
                                self.progress.emit(pct, f"{dl_mb:.1f}/{tot_mb:.1f} MB ({speed_mbps:.1f} MB/s)")
                            else:
                                dl_mb = downloaded / (1024 * 1024)
                                self.progress.emit(0, f"{dl_mb:.1f} MB ({speed_mbps:.1f} MB/s)")
                            last_emit_time = now

            # İndirme başarıyla tamamlandı, .part uzantısını kaldır
            os.replace(part_path, self.save_path)
            if total > 0:
                tot_mb = total / (1024 * 1024)
                self.progress.emit(100, f"{tot_mb:.1f}/{tot_mb:.1f} MB (100%)")
            self.finished.emit(self.save_path)

        except requests.exceptions.RequestException as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))


class SearchThread(QThread):
    """HuggingFace API'den model arama thread'i (trendingScore, downloads, likes, gated ve sıralama desteği)."""
    progress = pyqtSignal(str)   # status message
    finished = pyqtSignal(list)  # list of HfModelInfo
    error = pyqtSignal(str)

    def __init__(self, query: str = "", limit: int = 30, sort_by: str = "trendingScore",
                 token: str = "", translations_func=None):
        super().__init__()
        self.query = query.strip() if query else ""
        self.limit = limit
        self.sort_by = sort_by
        self.token = token.strip() if token else ""
        self.translations_func = translations_func

    def get_translated(self, key: str, default: str = "") -> str:
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def run(self):
        try:
            if self.query:
                self.progress.emit(self.get_translated("hf_searching", "Searching..."))
            else:
                self.progress.emit(self.get_translated("hf_trending_loading", "Loading featured & trending models..."))
            url = "https://huggingface.co/api/models"
            params = {
                "filter": "gguf",
                "sort": self.sort_by,
                "direction": "-1",
                "limit": self.limit,
                "expand": ["downloads", "likes", "gated", "lastModified"],
            }
            if self.query:
                params["search"] = self.query

            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code != 200:
                api_err = self.get_translated("hf_api_error", "API error")
                self.error.emit(f"HTTP {response.status_code}: {api_err}")
                return

            data = response.json()
            results = []
            for model in data:
                repo_id = model.get("id", "")
                if not repo_id:
                    continue
                downloads = int(model.get("downloads", 0) or 0)
                likes = int(model.get("likes", 0) or 0)
                gated_val = model.get("gated", False)
                is_gated = bool(gated_val) if gated_val is not None else False
                last_mod = model.get("lastModified", "") or ""
                results.append(HfModelInfo(
                    id=repo_id,
                    downloads=downloads,
                    likes=likes,
                    gated=is_gated,
                    last_modified=last_mod
                ))
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FilesThread(QThread):
    """HuggingFace API'den repo dosyalarını ve boyutlarını çeken thread."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)  # list of (filename, size_bytes) tuples
    error = pyqtSignal(str)
    _cache = {}

    def __init__(self, repo_id: str, token: str = "", translations_func=None):
        super().__init__()
        self.repo_id = repo_id
        self.token = token.strip() if token else ""
        self.translations_func = translations_func

    def get_translated(self, key: str, default: str = "") -> str:
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def _get_headers(self) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_file_size(self, fname: str) -> int:
        """HEAD isteği ile dosya boyutunu al — redirect takip + GET fallback."""
        url = f"https://huggingface.co/{self.repo_id}/resolve/main/{fname}"
        headers = self._get_headers()
        try:
            resp = requests.head(url, headers=headers, timeout=15, allow_redirects=True)
            if resp.status_code in (200, 206):
                cl = resp.headers.get("content-length")
                if cl and int(cl) > 0:
                    return int(cl)
        except Exception:
            pass
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=15)
            cl = resp.headers.get("content-length")
            if cl and int(cl) > 0:
                resp.close()
                return int(cl)
        except Exception:
            pass
        return 0

    def _get_files_from_tree_api(self):
        """Tree API ile tüm dosya adlarını ve boyutlarını toplu olarak al."""
        url = f"https://huggingface.co/api/models/{self.repo_id}/tree/main"
        params = {"recursive": "true", "expand": "false"}
        files = []
        session = requests.Session()
        session.headers.update(self._get_headers())

        while url:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            entries = response.json()
            if not isinstance(entries, list):
                raise ValueError("Unexpected HuggingFace Tree API response")

            for entry in entries:
                fname = entry.get("path", "")
                if entry.get("type") == "file" and fname.lower().endswith(".gguf"):
                    size = entry.get("size") or (entry.get("lfs") or {}).get("size") or 0
                    files.append((fname, int(size)))

            next_link = response.links.get("next", {}).get("url")
            url = next_link
            params = None

        return files

    def _get_files_from_model_api(self):
        """Tree API kullanılamazsa model metadata endpoint'ine geri dön."""
        url = f"https://huggingface.co/api/models/{self.repo_id}"
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        response.raise_for_status()
        siblings = response.json().get("siblings", [])
        files = []
        missing = []
        for sibling in siblings:
            fname = sibling.get("rfilename", "")
            if not fname.lower().endswith(".gguf"):
                continue
            size = sibling.get("size") or (sibling.get("lfs") or {}).get("size") or 0
            if size:
                files.append((fname, int(size)))
            else:
                missing.append(fname)

        if missing:
            with ThreadPoolExecutor(max_workers=min(8, len(missing))) as executor:
                futures = {executor.submit(self._get_file_size, name): name for name in missing}
                for future in as_completed(futures):
                    files.append((futures[future], future.result()))
        return files

    def run(self):
        try:
            self.progress.emit(self.get_translated("hf_loading_files", "Loading files..."))
            cached = self._cache.get(self.repo_id)
            if cached is not None:
                self.finished.emit(list(cached))
                return

            try:
                gguf_files = self._get_files_from_tree_api()
            except (requests.RequestException, ValueError):
                gguf_files = self._get_files_from_model_api()

            gguf_files.sort(key=lambda item: item[0].lower())
            self._cache[self.repo_id] = list(gguf_files)
            self.finished.emit(gguf_files)
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            api_err = self.get_translated("hf_api_error", "API error")
            self.error.emit(f"HTTP {status}: {api_err}")
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Ana Dialog
# ---------------------------------------------------------------------------

class HfDownloaderDialog(QDialog):
    """
    HuggingFace'den model indirme dialogu.
    Görsel mikro-kart tasarımlı model ve dosya listesi, hızlı quantization filtreleri,
    seçim özet paneli ve doğrudan arama sekmesinden indirme desteği sunar.
    """

    def __init__(self, translations_func=None, parent=None, initial_folder=""):
        super().__init__(parent)
        self.translations_func = translations_func
        self.initial_folder = initial_folder
        self.download_thread = None
        self.search_thread = None
        self.files_thread = None

        self.selected_repo = ""
        self.selected_file = ""
        self.selected_file_size = 0
        self.all_repo_files: List[Tuple[str, int]] = []

        self._build_ui()
        # İlk açılışta canlı trend modelleri otomatik yükle
        QTimer.singleShot(50, self._do_search)

    # ---- helpers ----

    def is_dark(self) -> bool:
        """Koyu tema aktifliğini belirler."""
        return is_dark_theme(self)

    def get_theme_colors(self) -> dict:
        """Mevcut temanın renk haritasını döndürür."""
        return ThemeColors.get(self.is_dark())

    def set_status(self, text: str, level: str = "info"):
        """
        Durum bildirimini yüksek kontrastlı modern renklerle gösterir.
        level: 'info', 'success', 'warning', 'error'
        """
        colors = self.get_theme_colors()
        color = colors.get(f"status_{level}", colors["status_info"])
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 500; font-style: italic; padding: 4px;")

    def get_translated(self, key: str, default: str = "") -> str:
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def _fmt_downloads(self, count: int) -> str:
        return fmt_downloads(count)

    def _fmt_size(self, size_bytes: int) -> str:
        return fmt_size(size_bytes)

    # ---- UI oluşturma ----

    def _build_ui(self):
        self.setWindowTitle(self.get_translated("dialog_hf_download_title", "HuggingFace'den Model İndir"))
        self.setMinimumSize(880, 620)
        self.resize(920, 660)

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

        # ---------- Ortak: HF Token (İsteğe Bağlı / Gated Modeller) ----------
        token_layout = QHBoxLayout()
        self.token_label = QLabel(self.get_translated("hf_token_label", "HF Token (isteğe bağlı):"))
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText(
            self.get_translated("hf_token_placeholder", "Gated modeller için token (hf_...)")
        )
        saved_tok = load_saved_hf_token()
        if saved_tok:
            self.token_input.setText(saved_tok)

        self.token_toggle_btn = QPushButton("👁")
        self.token_toggle_btn.setFixedWidth(32)
        self.token_toggle_btn.setToolTip("Tokenı göster / gizle")
        self.token_toggle_btn.clicked.connect(self._toggle_token_visibility)

        token_layout.addWidget(self.token_label)
        token_layout.addWidget(self.token_input)
        token_layout.addWidget(self.token_toggle_btn)
        main_layout.addLayout(token_layout)

        # ---------- Ortak: İndirme Klasörü ----------
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel(self.get_translated("hf_label_folder", "İndirme Klasörü:"))
        self.folder_input = QLineEdit()
        if self.initial_folder:
            self.folder_input.setText(self.initial_folder)
        self.folder_browse = QPushButton("📁")
        self.folder_browse.setFixedWidth(32)
        self.folder_browse.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.folder_browse)
        main_layout.addLayout(folder_layout)

        # ---------- Ortak: Progress Bar ----------
        self.status_label = QLabel("")
        self.set_status("", "info")
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
        colors = self.get_theme_colors()

        # Üst Arama ve Sıralama Barı
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            self.get_translated("hf_placeholder_search", "Örn: Qwen3 27B, gemma 4, llava")
        )
        self.search_input.returnPressed.connect(self._do_search)
        top_bar.addWidget(self.search_input, 2)

        self.sort_label = QLabel(self.get_translated("hf_sort_label", "Sırala:"))
        top_bar.addWidget(self.sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem(self.get_translated("hf_sort_trending", "🔥 Trend Olanlar"), "trendingScore")
        self.sort_combo.addItem(self.get_translated("hf_sort_downloads", "⬇️ En Çok İndirilenler"), "downloads")
        self.sort_combo.addItem(self.get_translated("hf_sort_likes", "❤️ En Çok Beğenilenler"), "likes")
        self.sort_combo.addItem(self.get_translated("hf_sort_modified", "🕒 En Son Güncellenenler"), "lastModified")
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        top_bar.addWidget(self.sort_combo)

        self.search_button = QPushButton(self.get_translated("hf_button_search", "Ara"))
        self.search_button.clicked.connect(self._do_search)
        top_bar.addWidget(self.search_button)
        layout.addLayout(top_bar)

        # Splitter: Sol (Modeller) / Sağ (Dosyalar)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Liste Stili: Yüksek kontrastlı kenarlık ve belirgin seçim
        list_style = f"""
            QListWidget {{
                background-color: transparent;
                border: 1px solid {colors['list_border']};
                border-radius: 6px;
                outline: none;
            }}
            QListWidget::item {{
                margin: 2px 3px;
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background-color: rgba(59, 130, 246, 0.35);
                border: 1px solid #60a5fa;
            }}
        """

        # --- Sol: Model Listesi (Görsel Kartlar) ---
        sol_layout = QVBoxLayout()
        sol_layout.setContentsMargins(0, 0, 0, 0)
        self.model_header = QLabel(self.get_translated("hf_model_list_title", "Modeller (downloads'a göre)"))
        self.model_header.setStyleSheet("font-weight: bold; padding: 4px;")
        self.model_list = QListWidget()
        self.model_list.setSpacing(3)
        self.model_list.setStyleSheet(list_style)
        self.model_list.itemClicked.connect(self._on_model_clicked)
        sol_layout.addWidget(self.model_header)
        sol_layout.addWidget(self.model_list)
        sol_widget = QWidget()
        sol_widget.setLayout(sol_layout)
        splitter.addWidget(sol_widget)

        # --- Sağ: GGUF Dosyaları ve Hızlı Filtreleme ---
        sag_layout = QVBoxLayout()
        sag_layout.setContentsMargins(0, 0, 0, 0)
        sag_layout.setSpacing(6)

        self.file_header = QLabel(self.get_translated("hf_file_list_title", "GGUF Dosyaları"))
        self.file_header.setStyleSheet("font-weight: bold; padding: 4px;")
        sag_layout.addWidget(self.file_header)

        # Hızlı Quantization Filtre Butonları + Dosya Arama
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(4)

        self.filter_buttons = {}
        self.filter_btn_group = QButtonGroup(self)
        self.filter_btn_group.setExclusive(True)

        categories = [
            ("all", self.get_translated("hf_filter_all", "Tümü")),
            ("q4", self.get_translated("hf_filter_q4", "Q4 (Önerilen)")),
            ("q5", self.get_translated("hf_filter_q5", "Q5")),
            ("q8", self.get_translated("hf_filter_q8", "Q8")),
            ("small", self.get_translated("hf_filter_small", "Küçük (Q2-Q3)")),
        ]

        filter_btn_style = f"""
            QPushButton {{
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:checked {{
                background-color: {colors['filter_active_bg']};
                border: 1px solid {colors['filter_active_border']};
                color: {colors['filter_active_text']};
                font-weight: bold;
            }}
        """

        for cat_id, label_text in categories:
            btn = QPushButton(label_text)
            btn.setCheckable(True)
            btn.setStyleSheet(filter_btn_style)
            if cat_id == "all":
                btn.setChecked(True)
            self.filter_btn_group.addButton(btn)
            self.filter_buttons[cat_id] = btn
            btn.clicked.connect(self._apply_files_filter)
            filter_layout.addWidget(btn)

        sag_layout.addLayout(filter_layout)

        # Anlık Dosya Arama / Filtreleme Kutusu
        self.file_search_input = QLineEdit()
        self.file_search_input.setPlaceholderText(
            self.get_translated("hf_filter_search_placeholder", "🔍 Dosya filtrele...")
        )
        self.file_search_input.textChanged.connect(self._apply_files_filter)
        sag_layout.addWidget(self.file_search_input)

        # Dosya Listesi
        self.file_list = QListWidget()
        self.file_list.setSpacing(3)
        self.file_list.setStyleSheet(list_style)
        self.file_list.itemClicked.connect(self._on_file_clicked)
        sag_layout.addWidget(self.file_list)

        sag_widget = QWidget()
        sag_widget.setLayout(sag_layout)
        splitter.addWidget(sag_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([380, 500])
        layout.addWidget(splitter)

        # --- Alt: Kesintisiz UX Seçim Özet Paneli ---
        self.summary_box = QFrame()
        self.summary_box.setFrameShape(QFrame.Shape.StyledPanel)
        self.summary_box.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['summary_bg']};
                border: 1px solid {colors['summary_border']};
                border-radius: 6px;
                padding: 5px 10px;
            }}
        """)
        summary_layout = QVBoxLayout(self.summary_box)
        summary_layout.setContentsMargins(4, 4, 4, 4)
        summary_layout.setSpacing(2)

        self.summary_title = QLabel(self.get_translated("hf_summary_title", "Seçilen Model ve Dosya:"))
        font = self.summary_title.font()
        font.setBold(True)
        font.setPointSize(max(8, font.pointSize() - 1))
        self.summary_title.setFont(font)
        self.summary_title.setStyleSheet(f"color: {colors['summary_title']}; font-weight: bold; border: none; background: transparent;")

        self.summary_desc = QLabel(self.get_translated("hf_summary_no_selection", "Henüz bir model ve dosya seçilmedi."))
        self.summary_desc.setStyleSheet(f"color: {colors['text_primary']}; font-weight: 600; border: none; background: transparent;")

        summary_layout.addWidget(self.summary_title)
        summary_layout.addWidget(self.summary_desc)
        layout.addWidget(self.summary_box)

        # İpucu
        self.search_hint = QLabel(self.get_translated("hf_search_hint",
            "💡 Bir modele tıklayın → GGUF dosyaları sağda listelenir. Dosyaya tıklayın → Alanlar otomatik dolar."))
        self.search_hint.setStyleSheet(f"font-size: 11px; color: {colors['text_secondary']}; padding: 2px;")
        layout.addWidget(self.search_hint)

        tab_widget = QWidget()
        tab_widget.setLayout(layout)
        return tab_widget

    # ---- Manual Tab ----

    def _build_manual_tab(self) -> QWidget:
        layout = QVBoxLayout()
        layout.setSpacing(8)
        colors = self.get_theme_colors()

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
        self.manual_hint = QLabel(self.get_translated("hf_manual_hint",
            "💡 Repo ve dosya adını elle yazın veya 'Ara' sekmesinden otomatik seçin."))
        self.manual_hint.setStyleSheet(f"font-size: 11px; color: {colors['text_secondary']}; padding: 4px;")
        layout.addWidget(self.manual_hint)

        layout.addStretch()

        tab_widget = QWidget()
        tab_widget.setLayout(layout)
        return tab_widget

    # ---- Arama işlemleri ----

    def _on_sort_changed(self):
        """Sıralama seçeneği değiştiğinde aramayı yenile."""
        self._do_search()

    def _do_search(self):
        query = self.search_input.text().strip()

        # UI'yi kilitle
        self.search_button.setEnabled(False)
        self.search_input.setEnabled(False)
        self.sort_combo.setEnabled(False)
        self.model_list.clear()
        self.file_list.clear()
        self.all_repo_files = []

        if query:
            self.set_status(self.get_translated("hf_searching", "Aranıyor..."), "info")
            self.model_header.setText(self.get_translated("hf_model_list_title", "Modeller"))
        else:
            self.set_status(self.get_translated("hf_trending_loading", "Öne çıkan ve trend modeller yükleniyor..."), "info")
            self.model_header.setText(self.get_translated("hf_model_list_trending", "Öne Çıkan & Trend Modeller"))

        sort_by = self.sort_combo.currentData() or "trendingScore"
        token = self.token_input.text().strip()

        self.search_thread = SearchThread(
            query=query,
            limit=30,
            sort_by=sort_by,
            token=token,
            translations_func=self.translations_func
        )
        self.search_thread.progress.connect(lambda msg: self.set_status(msg, "info"))
        self.search_thread.finished.connect(self._on_search_results)
        self.search_thread.error.connect(self._on_search_error)
        self.search_thread.start()

    def _on_search_results(self, results: list):
        """Sonuçlar: list of HfModelInfo veya geriye uyumluluk için (repo_id, downloads)."""
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.wait()
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)
        self.sort_combo.setEnabled(True)

        is_dark = self.is_dark()
        self.model_list.clear()
        for item_data in results:
            if isinstance(item_data, HfModelInfo):
                repo_id = item_data.id
                downloads = item_data.downloads
                likes = item_data.likes
                is_gated = item_data.gated
            elif isinstance(item_data, (tuple, list)):
                repo_id = item_data[0]
                downloads = item_data[1] if len(item_data) > 1 else 0
                likes = item_data[2] if len(item_data) > 2 else 0
                is_gated = bool(item_data[3]) if len(item_data) > 3 else False
            else:
                repo_id = str(item_data)
                downloads, likes, is_gated = 0, 0, False

            item = QListWidgetItem()
            widget = RepoCardWidget(
                repo_id=repo_id,
                downloads=downloads,
                likes=likes,
                is_gated=is_gated,
                is_dark=is_dark
            )
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, repo_id)
            self.model_list.addItem(item)
            self.model_list.setItemWidget(item, widget)

        if not results:
            self.set_status(self.get_translated("hf_no_results", "Sonuç bulunamadı."), "warning")
        else:
            self.set_status(
                self.get_translated("hf_results_found", "✓ {count} sonuç bulundu. Bir model seçin.").format(count=len(results)),
                "success"
            )

    def _on_search_error(self, error_msg: str):
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.wait()
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)
        self.sort_combo.setEnabled(True)
        self.set_status(
            self.get_translated("hf_search_error_status", "❌ Arama hatası: {error}").format(error=error_msg),
            "error"
        )
        QMessageBox.critical(
            self,
            self.get_translated("hf_search_error_title", "Arama Hatası"),
            error_msg
        )

    def _on_model_clicked(self, item: QListWidgetItem):
        """Model seçildi → dosyalarını çek ve özet paneline yansıt."""
        repo_id = item.data(Qt.ItemDataRole.UserRole)
        if not repo_id:
            return
        if self.files_thread and self.files_thread.isRunning():
            return

        self.selected_repo = repo_id
        self.selected_file = ""
        self.selected_file_size = 0

        # Manuel repo alanını senkronize et
        self.repo_input.setText(repo_id)

        # Özet panelini güncelle
        colors = self.get_theme_colors()
        no_file_text = self.get_translated("hf_summary_no_selection", "Henüz bir model ve dosya seçilmedi.")
        self.summary_desc.setText(f"📦 {repo_id}   ▶   ({no_file_text})")
        self.summary_desc.setStyleSheet(f"font-weight: 500; color: {colors['text_secondary']};")

        self.model_list.setEnabled(False)
        self.file_list.clear()
        self.all_repo_files = []
        self.set_status(self.get_translated("hf_loading_files", "Dosyalar yükleniyor..."), "info")

        token = self.token_input.text().strip()
        self.files_thread = FilesThread(repo_id, token=token, translations_func=self.translations_func)
        self.files_thread.progress.connect(lambda msg: self.set_status(msg, "info"))
        self.files_thread.finished.connect(self._on_files_results)
        self.files_thread.error.connect(self._on_files_error)
        self.files_thread.start()

    def _apply_files_filter(self):
        """Sağ dosya listesine aktif quantization ve metin arama filtresini uygula."""
        active_cat = "all"
        for cat_id, btn in self.filter_buttons.items():
            if btn.isChecked():
                active_cat = cat_id
                break

        query = self.file_search_input.text().strip().lower()
        self.file_list.clear()

        filtered = []
        for fname, size in self.all_repo_files:
            if not match_quant_filter(fname, active_cat):
                continue
            if query and query not in fname.lower():
                continue
            filtered.append((fname, size))

        is_dark = self.is_dark()
        reco_text = self.get_translated("hf_recommended_badge", "⭐ Önerilen")
        for fname, size in filtered:
            item = QListWidgetItem()
            is_reco = is_recommended_quant(fname)
            widget = GgufFileCardWidget(
                filename=fname,
                size_bytes=size,
                is_recommended=is_reco,
                size_str=self._fmt_size(size),
                reco_text=reco_text,
                is_dark=is_dark
            )
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, fname)
            item.setData(Qt.ItemDataRole.UserRole + 1, size)
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, widget)

        # Başlık sayacını güncelle
        base_title = self.get_translated("hf_file_list_title", "GGUF Dosyaları")
        if self.all_repo_files:
            self.file_header.setText(f"{base_title} ({len(filtered)}/{len(self.all_repo_files)})")
        else:
            self.file_header.setText(base_title)

    def _on_files_results(self, files: list):
        """files: list of (filename, size_bytes) tuples"""
        if self.files_thread and self.files_thread.isRunning():
            self.files_thread.wait()
        self.model_list.setEnabled(True)
        self.all_repo_files = list(files)
        self._apply_files_filter()

        if not files:
            self.set_status(
                self.get_translated("hf_no_gguf_files", "Bu repoda .gguf dosyası bulunamadı."),
                "warning"
            )
        else:
            self.set_status(
                self.get_translated("hf_files_found", "✓ {count} GGUF dosyası bulundu.").format(count=len(files)),
                "success"
            )

    def _on_files_error(self, error_msg: str):
        if self.files_thread and self.files_thread.isRunning():
            self.files_thread.wait()
        self.model_list.setEnabled(True)
        self.set_status(
            self.get_translated("hf_files_error_status", "❌ Dosya listesi hatası: {error}").format(error=error_msg),
            "error"
        )
        QMessageBox.critical(
            self,
            self.get_translated("hf_files_error_title", "Dosya Listesi Hatası"),
            error_msg
        )

    def _on_file_clicked(self, item: QListWidgetItem):
        """
        Dosya seçildiğinde:
        - Özet panelini güncelle
        - Manuel sekme inputlarını doldur
        - KESİNTİSİZ AKIŞ: Kullanıcıyı zorla manuel sekmeye atma (tab switch kaldırıldı)
        """
        filename = item.data(Qt.ItemDataRole.UserRole) or item.text()
        size = item.data(Qt.ItemDataRole.UserRole + 1) or 0
        self.selected_file = filename
        self.selected_file_size = size

        # Manuel sekme için senkronize et
        self.file_input.setText(filename)
        if self.selected_repo:
            self.repo_input.setText(self.selected_repo)

        # Özet panelini güncelle
        colors = self.get_theme_colors()
        size_str = self._fmt_size(size)
        repo_display = self.selected_repo or self.repo_input.text().strip()
        self.summary_desc.setText(f"📦 {repo_display}   ▶   📄 {filename}  ({size_str})")
        self.summary_desc.setStyleSheet(f"font-weight: bold; color: {colors['text_primary']}; border: none; background: transparent;")

        self.set_status(
            self.get_translated(
                "hf_file_selected_ready",
                "✓ {filename} seçildi. İndirme klasörünü kontrol edip 'İndir'e basın."
            ).format(filename=filename),
            "success"
        )

    # ---- İndirme İşlemleri ----

    def _toggle_token_visibility(self):
        """HF token şifre görünürlüğünü aç/kapat."""
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.token_toggle_btn.setText("🔒")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.token_toggle_btn.setText("👁")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            self.get_translated("hf_folder_browse_title", "İndirme Klasörü Seç")
        )
        if folder:
            self.folder_input.setText(folder)

    def _start_download(self):
        """
        Aktif sekmeden bağımsız olarak indirme başlat.
        Arama sekmesinde seçilen model veya Manuel sekmede girilen bilgiler kullanılır.
        """
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:  # Arama Sekmesi
            repo = (self.selected_repo or self.repo_input.text()).strip()
            filename = (self.selected_file or self.file_input.text()).strip()
            if not repo or not filename:
                QMessageBox.warning(
                    self,
                    self.get_translated("hf_warning_title", "Uyarı"),
                    self.get_translated("hf_no_selection_warning", "Lütfen indirmek için bir model ve GGUF dosyası seçin.")
                )
                return
        else:  # Manuel Sekme
            repo = self.repo_input.text().strip()
            filename = self.file_input.text().strip()
            if not repo or "/" not in repo:
                QMessageBox.warning(
                    self,
                    self.get_translated("hf_warning_title", "Uyarı"),
                    self.get_translated("hf_invalid_repo", "⚠ Geçersiz repo formatı. 'user/repo' şeklinde olmalıdır.")
                )
                return
            if not filename:
                QMessageBox.warning(
                    self,
                    self.get_translated("hf_error_title", "Hata"),
                    self.get_translated("hf_filename_empty", "Dosya adı boş olamaz.")
                )
                return

        folder = self.folder_input.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(
                self,
                self.get_translated("hf_error_title", "Hata"),
                self.get_translated("hf_invalid_folder", "Geçerli bir indirme klasörü seçin.")
            )
            return

        # Token girilmişse diske güvenle kaydet
        token = self.token_input.text().strip()
        if token:
            save_hf_token(token)

        # URL oluştur
        url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
        save_path = os.path.join(folder, filename)

        self._set_download_state(True)
        self.set_status(self.get_translated("hf_downloading", "İndiriliyor..."), "info")

        self.download_thread = DownloadThread(
            url=url,
            save_path=save_path,
            token=token,
            translations_func=self.translations_func
        )
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.finished.connect(self._on_finished)
        self.download_thread.error.connect(self._on_error)
        self.download_thread.start()

    def _set_download_state(self, downloading: bool):
        """İndirme sırasında UI bileşenlerini kilitle / aç."""
        enabled = not downloading
        self.download_button.setEnabled(enabled)
        self.cancel_button.setEnabled(downloading)
        self.repo_input.setEnabled(enabled)
        self.file_input.setEnabled(enabled)
        self.folder_input.setEnabled(enabled)
        self.folder_browse.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.search_button.setEnabled(enabled)
        self.sort_combo.setEnabled(enabled)
        self.token_input.setEnabled(enabled)
        self.token_toggle_btn.setEnabled(enabled)

    def _cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.set_status(
                f"{self.get_translated('hf_downloading', 'İndiriliyor...')} - {self.get_translated('hf_cancelling', 'İptal ediliyor...')}",
                "warning"
            )

    def _on_progress(self, pct: int, message: str):
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{message}  (%p%)")
        self.set_status(
            f"{self.get_translated('hf_downloading', 'İndiriliyor...')} — {message}",
            "info"
        )

    def _on_finished(self, path: str):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.wait()
        self._set_download_state(False)
        self.progress_bar.setValue(100)
        complete_msg = self.get_translated("hf_download_complete", "✓ İndirme tamamlandı!")
        self.set_status(complete_msg, "success")

        QMessageBox.information(
            self,
            self.get_translated("hf_success_title", "Başarılı"),
            f"{complete_msg}\n\n{path}"
        )

        self.setProperty("downloaded_path", path)
        self.accept()

    def _on_error(self, error_msg: str):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.wait()
        self._set_download_state(False)

        if error_msg == "cancelled":
            self.set_status(
                self.get_translated(
                    "hf_download_paused",
                    "⚠ İndirme durduruldu. Tekrar 'İndir'e basarak devam edebilirsiniz."
                ),
                "warning"
            )
        else:
            msg = self.get_translated("hf_download_error", "❌ İndirme hatası: {error}").format(error=error_msg)
            self.set_status(msg, "error")
            QMessageBox.critical(
                self,
                self.get_translated("hf_download_error_title", "İndirme Hatası"),
                msg
            )

    def get_downloaded_path(self) -> str:
        return self.property("downloaded_path") or ""

    # ---- Dil güncelleme ----

    def update_labels(self):
        """Çeviri etiketlerini güncelle (çalışma anında dil değişimi için)."""
        self.setWindowTitle(self.get_translated("dialog_hf_download_title", "HuggingFace'den Model İndir"))
        colors = self.get_theme_colors()

        # Tab başlıkları
        self.tabs.setTabText(0, self.get_translated("hf_tab_search", "🔍 Ara"))
        self.tabs.setTabText(1, self.get_translated("hf_tab_manual", "✏️ Manuel"))

        # Manuel sekme
        self.repo_label.setText(self.get_translated("hf_label_repo", "HuggingFace Repo:"))
        self.repo_input.setPlaceholderText(
            self.get_translated("hf_placeholder_repo", "Örn: unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF")
        )
        self.file_label.setText(self.get_translated("hf_label_filename", "Dosya Adı:"))
        self.file_input.setPlaceholderText(
            self.get_translated("hf_placeholder_filename", "Örn: Qwen3-VL-30B-A3B-Instruct-UD-IQ3_XXS.gguf")
        )
        if hasattr(self, "manual_hint"):
            self.manual_hint.setText(
                self.get_translated("hf_manual_hint", "💡 Repo ve dosya adını elle yazın veya 'Ara' sekmesinden otomatik seçin.")
            )
            self.manual_hint.setStyleSheet(f"font-size: 11px; color: {colors['text_secondary']}; padding: 4px;")

        # Arama sekme
        self.search_input.setPlaceholderText(
            self.get_translated("hf_placeholder_search", "Örn: Qwen3 27B, gemma 4, llava")
        )
        self.search_button.setText(self.get_translated("hf_button_search", "Ara"))
        if hasattr(self, "sort_label"):
            self.sort_label.setText(self.get_translated("hf_sort_label", "Sırala:"))
        if hasattr(self, "sort_combo"):
            self.sort_combo.setItemText(0, self.get_translated("hf_sort_trending", "🔥 Trend Olanlar"))
            self.sort_combo.setItemText(1, self.get_translated("hf_sort_downloads", "⬇️ En Çok İndirilenler"))
            self.sort_combo.setItemText(2, self.get_translated("hf_sort_likes", "❤️ En Çok Beğenilenler"))
            self.sort_combo.setItemText(3, self.get_translated("hf_sort_modified", "🕒 En Son Güncellenenler"))
        if hasattr(self, "model_header"):
            if self.search_input.text().strip():
                self.model_header.setText(self.get_translated("hf_model_list_title", "Modeller"))
            else:
                self.model_header.setText(self.get_translated("hf_model_list_trending", "Öne Çıkan & Trend Modeller"))
        if hasattr(self, "file_header"):
            base_title = self.get_translated("hf_file_list_title", "GGUF Dosyaları")
            count_info = f" ({self.file_list.count()}/{len(self.all_repo_files)})" if self.all_repo_files else ""
            self.file_header.setText(f"{base_title}{count_info}")
        if hasattr(self, "search_hint"):
            self.search_hint.setText(
                self.get_translated("hf_search_hint", "💡 Bir modele tıklayın → GGUF dosyaları sağda listelenir. Dosyaya tıklayın → Alanlar otomatik dolar.")
            )
            self.search_hint.setStyleSheet(f"font-size: 11px; color: {colors['text_secondary']}; padding: 2px;")

        # Filtre butonları
        for cat_id, btn in getattr(self, "filter_buttons", {}).items():
            if cat_id == "all":
                btn.setText(self.get_translated("hf_filter_all", "Tümü"))
            elif cat_id == "q4":
                btn.setText(self.get_translated("hf_filter_q4", "Q4 (Önerilen)"))
            elif cat_id == "q5":
                btn.setText(self.get_translated("hf_filter_q5", "Q5"))
            elif cat_id == "q8":
                btn.setText(self.get_translated("hf_filter_q8", "Q8"))
            elif cat_id == "small":
                btn.setText(self.get_translated("hf_filter_small", "Küçük (Q2-Q3)"))

        if hasattr(self, "file_search_input"):
            self.file_search_input.setPlaceholderText(
                self.get_translated("hf_filter_search_placeholder", "🔍 Dosya filtrele...")
            )

        # Özet kutusu
        if hasattr(self, "summary_title"):
            self.summary_title.setText(self.get_translated("hf_summary_title", "Seçilen Model ve Dosya:"))
            self.summary_title.setStyleSheet(f"color: {colors['summary_title']}; font-weight: bold; border: none; background: transparent;")
        if hasattr(self, "summary_desc") and not self.selected_file:
            self.summary_desc.setText(self.get_translated("hf_summary_no_selection", "Henüz bir model ve dosya seçilmedi."))
            self.summary_desc.setStyleSheet(f"color: {colors['text_secondary']}; font-weight: 500; border: none; background: transparent;")

        # Ortak alanlar
        if hasattr(self, "token_label"):
            self.token_label.setText(self.get_translated("hf_token_label", "HF Token (isteğe bağlı):"))
        if hasattr(self, "token_input"):
            self.token_input.setPlaceholderText(
                self.get_translated("hf_token_placeholder", "Gated modeller için token (hf_...)")
            )
        self.folder_label.setText(self.get_translated("hf_label_folder", "İndirme Klasörü:"))
        self.download_button.setText(self.get_translated("hf_button_download", "İndir"))
        self.cancel_button.setText(self.get_translated("hf_button_cancel", "İptal"))
