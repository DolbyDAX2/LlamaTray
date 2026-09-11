"""
llama.cpp Build & Install Manager (v1.5.0).

Kullanıcının llama-server'ı kolayca derleyip kurmasını sağlayan dialog:
  - Pre-flight donanım tespiti (nvidia-smi, rocminfo, vulkaninfo, clinfo, lspci)
  - Multi-target backend seçimi (Vulkan / CUDA / ROCm-HIP / SYCL / CPU)
  - Dağıtım farkında bağımlılık kontrolü & kurulum (apt / dnf / pacman / zypper)
  - Option A: kaynak derleme (git clone + cmake + build)
  - Option B: hazır release asset indirme (GitHub Releases)
  - Sonuç binary'i LlamaTray'in otomatik bulduğu konumlara yerleştirilir
    (~/.local/bin/llama-server symlink/copy; ~/llama.cpp/build/bin)
"""

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QGroupBox, QHBoxLayout, QLabel,
                             QPlainTextEdit, QProgressBar, QRadioButton,
                             QPushButton, QVBoxLayout)

LLAMA_CPP_REPO_URL = "https://github.com/ggerganov/llama.cpp"
RELEASES_API_URL = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
BUILD_ROOT = os.path.expanduser("~/llama.cpp")
BUILD_BIN_DIR = os.path.join(BUILD_ROOT, "build", "bin")
LOCAL_BIN_DIR = os.path.expanduser("~/.local/bin")
BIN_NAME = "llama-server"

# backend key -> (UI etiketi, cmake flag'leri)
BACKENDS = {
    "vulkan": ("Vulkan (Evrensel - Önerilen)", ["-DGGML_VULKAN=ON"]),
    "cuda": ("NVIDIA CUDA", ["-DGGML_CUDA=ON"]),
    "rocm": ("AMD ROCm (HIP)", ["-DGGML_HIPBLAS=ON"]),
    "sycl": ("Intel SYCL", ["-DGGML_SYCL=ON"]),
    "cpu": ("Sadece CPU", []),
}
BACKEND_ORDER = ["vulkan", "cuda", "rocm", "sycl", "cpu"]

# package manager -> açık (group name değil) derleme paketi komutları
DEP_SPECS = {
    "apt": ["sudo", "apt", "install", "-y", "build-essential", "cmake", "git"],
    "dnf": ["sudo", "dnf", "install", "-y", "gcc-c++", "make", "cmake", "git"],
    "pacman": ["sudo", "pacman", "-S", "--needed", "base-devel", "cmake", "git"],
    "zypper": ["sudo", "zypper", "install", "-y", "gcc-c++", "make", "cmake", "git"],
}


def detect_package_manager():
    """Host dağıtımın paket yöneticisini tespit et (apt/dnf/pacman/zypper)."""
    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("zypper"):
        return "zypper"
    return None


def check_build_tools():
    """Derleme araçlarının yollarını döndür: cmake, git, g++, clang, make."""
    tools = {}
    for t in ("cmake", "git", "g++", "clang", "make"):
        p = shutil.which(t)
        if p:
            tools[t] = p
    return tools


class HardwareScanWorker(QThread):
    """Donanım/araç taramasını UI bloke etmeden çalıştırır."""

    finished_scan = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_requested = False
        self._proc = None

    def request_stop(self):
        self._stop_requested = True
        proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass

    def _run_tool(self, cmd, timeout):
        """Kısa bir tespit komutunu çalıştır; stdout'u (veya '') döndür."""
        if self._stop_requested:
            return ""
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True)
        except Exception:
            return ""
        self._proc = p
        try:
            out, _ = p.communicate(timeout=timeout)
            return out or ""
        except subprocess.TimeoutExpired:
            try:
                p.kill()
                p.communicate()
            except Exception:
                pass
            return ""
        finally:
            self._proc = None

    def run(self):
        result = {"tools": {}, "gpus": [], "vendor": None, "recommendation": "cpu"}
        tools = {}
        for t in ("nvidia-smi", "nvcc", "rocminfo", "vulkaninfo", "clinfo", "lspci"):
            tools[t] = shutil.which(t) is not None
        result["tools"] = tools
        vendor = None

        # NVIDIA: GPU listesini nvidia-smi ile dene
        if tools.get("nvidia-smi"):
            out = self._run_tool(["nvidia-smi", "-L"], timeout=6)
            for line in out.splitlines():
                if "GPU" in line:
                    result["gpus"].append(line.strip())
            if result["gpus"]:
                vendor = "nvidia"

        # lspci ile vendor tespiti (NVIDIA/AMD/Intel)
        lspci_out = ""
        if tools.get("lspci") and not self._stop_requested:
            lspci_out = self._run_tool(["lspci"], timeout=6).upper()
            if vendor is None:
                if "NVIDIA" in lspci_out:
                    vendor = "nvidia"
                elif "AMD" in lspci_out or "RADEON" in lspci_out or "ATI" in lspci_out:
                    vendor = "amd"
                elif ("INTEL" in lspci_out and any(k in lspci_out for k in
                                                   ("VGA", "DISPLAY", "3D CONTROLLER"))):
                    vendor = "intel"

        # AMD ROCm stack kontrolü
        if tools.get("rocminfo") and not self._stop_requested:
            rocm_out = self._run_tool(["rocminfo", "--devices"], timeout=8)
            if re.search(r"Card series|GPU\[\d", rocm_out):
                if vendor is None:
                    vendor = "amd"
                tools["rocm_stack"] = True

        # Öneri (deterministik)
        if vendor == "nvidia":
            rec = "cuda" if tools.get("nvcc") else "vulkan"
        elif vendor == "amd":
            rec = "rocm" if tools.get("rocm_stack") else "vulkan"
        elif vendor == "intel":
            rec = "sycl" if tools.get("clinfo") and not tools.get("vulkaninfo") else "vulkan"
        else:
            rec = "cpu"

        result["vendor"] = vendor
        result["recommendation"] = rec

        # Banner anahtarı
        banner_keys = {
            ("nvidia", "cuda"): "llm_reco_nvidia_cuda",
            ("nvidia", "vulkan"): "llm_reco_nvidia_vulkan",
            ("amd", "rocm"): "llm_reco_amd_rocm",
            ("amd", "vulkan"): "llm_reco_amd_vulkan",
        }
        result["banner_key"] = banner_keys.get((vendor, rec))
        if result["banner_key"] is None:
            if vendor == "intel":
                result["banner_key"] = "llm_reco_intel"
            else:
                result["banner_key"] = "llm_reco_cpu"
        if self._stop_requested:
            return  # dialog kapatıldı; sonuç artık istenmiyor
        self.finished_scan.emit(result)


class BuildWorker(QThread):
    """Option A: kaynak derleme (clone → cmake configure → build → ~/.local/bin'e kur)."""

    log_line = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_build = pyqtSignal(bool, str)

    def __init__(self, backend_key, parent=None):
        super().__init__(parent)
        self.backend_key = backend_key
        self._proc = None
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True
        proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass

    def _run_step(self, cmd, label, done_pct):
        """Bir komutu çalıştır, çıktısını satır satır logla; True/False döndür."""
        if self._stop_requested:
            return False
        self.log_line.emit(f"▶ {label}")
        self.log_line.emit("$ " + " ".join(cmd))
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
        except FileNotFoundError as e:
            self.log_line.emit(f"❌ Komut bulunamadı: {e.filename}")
            return False
        self._proc = proc
        try:
            for line in proc.stdout:
                if self._stop_requested:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    self.log_line.emit("⚠ Kullanıcı tarafından durduruldu.")
                    return False
                self.log_line.emit(line.rstrip())
            rc = proc.wait()
        finally:
            self._proc = None
        if rc != 0:
            self.log_line.emit(f"❌ '{label}' başarısız oldu (exit code {rc}).")
            return False
        self.progress.emit(done_pct)
        return True

    def _install_binary(self):
        """Derlenen llama-server'ı ~/.local/bin'e symlink/copy olarak kur."""
        src = os.path.join(BUILD_BIN_DIR, BIN_NAME)
        if not (os.path.exists(src) and os.access(src, os.X_OK)):
            alt = os.path.join(BUILD_ROOT, "build", BIN_NAME)
            if os.path.exists(alt) and os.access(alt, os.X_OK):
                src = alt
            else:
                return None
        try:
            os.makedirs(LOCAL_BIN_DIR, exist_ok=True)
            dst = os.path.join(LOCAL_BIN_DIR, BIN_NAME)
            if os.path.lexists(dst):
                os.remove(dst)
            try:
                os.symlink(src, dst)
            except OSError:
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)
            return dst
        except Exception as e:
            self.log_line.emit(f"⚠ ~/.local/bin kurulumu başarısız: {e}")
            return None

    def run(self):
        label, flags = BACKENDS[self.backend_key]
        try:
            # Adım 1: kaynağı klonla / güncelle
            if os.path.isdir(os.path.join(BUILD_ROOT, ".git")):
                self.log_line.emit(f"✓ Kaynak zaten mevcut: {BUILD_ROOT}")
                # Güncelleme best-effort: offline olursa mevcut checkout ile devam et.
                self._run_step(["git", "-C", BUILD_ROOT, "pull", "--ff-only"],
                               "Kaynağı güncelle (git pull)", 15)
            elif os.path.exists(BUILD_ROOT):
                self.log_line.emit(
                    f"❌ '{BUILD_ROOT}' dizini mevcut ama bir git deposu değil. "
                    f"Silip tekrar deneyin.")
                self.finished_build.emit(False, "")
                return
            else:
                ok = self._run_step(
                    ["git", "clone", "--depth", "1", LLAMA_CPP_REPO_URL, BUILD_ROOT],
                    "Kaynağı klonla (git clone)", 15)
                if not ok:
                    self.finished_build.emit(False, "")
                    return

            # Adım 2: cmake configure
            cfg = ["cmake", "-S", BUILD_ROOT, "-B", os.path.join(BUILD_ROOT, "build"),
                   "-DCMAKE_BUILD_TYPE=Release"] + flags
            if not self._run_step(cfg, f"Yapılandır (backend: {label})", 40):
                self.finished_build.emit(False, "")
                return

            # Adım 3: build
            jobs = str(max(1, os.cpu_count() or 2))
            bld = ["cmake", "--build", os.path.join(BUILD_ROOT, "build"),
                   "--target", BIN_NAME, "-j", jobs]
            if not self._run_step(bld, "Derle (llama-server)", 85):
                self.finished_build.emit(False, "")
                return

            # Adım 4: ~/.local/bin'e kur
            installed = self._install_binary()
            src = os.path.join(BUILD_BIN_DIR, BIN_NAME)
            if installed is None and os.path.exists(src):
                self.log_line.emit(f"⚠ Binary derlendi ama ~/.local/bin'e kopyalanamadı: {src}")
                self.finished_build.emit(True, src)
                return
            if installed is None:
                self.log_line.emit("❌ Derleme sonrası llama-server binary'si bulunamadı.")
                self.finished_build.emit(False, "")
                return
            self.progress.emit(100)
            self.log_line.emit(f"✓ Kuruldu: {installed}")
            self.log_line.emit(f"✓ Backend: {label} | Flag'ler: {' '.join(flags) or '(yok)'}")
            self.finished_build.emit(True, installed)
        except Exception as e:
            self.log_line.emit(f"❌ Beklenmeyen hata: {type(e).__name__}: {e}")
            self.finished_build.emit(False, "")


class PrebuiltWorker(QThread):
    """Option B: GitHub Releases'tan hazır Linux x64 asset indirip kur."""

    log_line = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_install = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_requested = False
        self._resp = None

    def request_stop(self):
        self._stop_requested = True
        resp = self._resp
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    def run(self):
        import requests
        tmpdir = None
        try:
            self.log_line.emit("📡 GitHub Releases'tan son sürümü sorgulanıyor...")
            r = requests.get(RELEASES_API_URL, timeout=30, headers={
                "Accept": "application/vnd.github+json", "User-Agent": "LlamaTray"})
            r.raise_for_status()
            assets = r.json().get("assets", [])
        except Exception as e:
            self.log_line.emit(f"❌ Release bilgisi alınamadı: {e}")
            self.finished_install.emit(False, "")
            return

        candidates = [a for a in assets
                      if re.search(r"linux.*(x64|amd64)", a.get("name", ""), re.I)]
        if not candidates:
            candidates = [a for a in assets if re.search(r"linux", a.get("name", ""), re.I)]
        if not candidates:
            self.log_line.emit("❌ Son release'te Linux x64 asset bulunamadı.")
            self.finished_install.emit(False, "")
            return

        # Vulkan derlemesini tercih et (evrensel)
        chosen = next((a for a in candidates
                       if "vulkan" in a.get("name", "").lower()), candidates[0])
        name = chosen["name"]
        url = chosen["browser_download_url"]
        size = int(chosen.get("size") or 0)
        self.log_line.emit(f"✓ Asset seçildi: {name}")

        try:
            tmpdir = tempfile.mkdtemp(prefix="llamatray-llamacpp-")
            dest = os.path.join(tmpdir, name)

            # İndir (ilerleme yüzdesi ile)
            resp = requests.get(url, stream=True, timeout=60)
            self._resp = resp
            try:
                resp.raise_for_status()
                total = int(resp.headers.get("Content-Length") or size or 0)
                done, last_pct = 0, -1
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if self._stop_requested:
                            break
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            pct = int(done * 100 / total)
                            if pct != last_pct:
                                last_pct = pct
                                self.progress.emit(pct)
            finally:
                try:
                    resp.close()
                except Exception:
                    pass
                self._resp = None

            if self._stop_requested:
                self.log_line.emit("⚠ Kullanıcı tarafından durduruldu.")
                self.finished_install.emit(False, "")
                return

            # Çıkar
            self.log_line.emit("📦 Arşiv çıkarılıyor...")
            extracted_bin = self._extract(dest, tmpdir)
            if extracted_bin is None:
                self.log_line.emit("❌ Arşivin içinde llama-server bulunamadı.")
                self.finished_install.emit(False, "")
                return

            # ~/.local/bin'e kur
            try:
                os.makedirs(LOCAL_BIN_DIR, exist_ok=True)
                dst = os.path.join(LOCAL_BIN_DIR, BIN_NAME)
                if os.path.lexists(dst):
                    os.remove(dst)
                shutil.copy2(extracted_bin, dst)
                os.chmod(dst, 0o755)
            except Exception as e:
                self.log_line.emit(f"❌ ~/.local/bin'e kopyalama hatası: {e}")
                self.finished_install.emit(False, "")
                return

            self.progress.emit(100)
            self.log_line.emit(f"✓ Hazır binary kuruldu: {dst}")
            self.finished_install.emit(True, dst)
        except Exception as e:
            self.log_line.emit(f"❌ İndirme/kurulum hatası: {type(e).__name__}: {e}")
            self.finished_install.emit(False, "")
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)

    def _extract(self, archive_path, dest_dir):
        """Arşivi aç ve içindeki llama-server binary'sinin yolunu döndür."""
        name = os.path.basename(archive_path).lower()
        try:
            if name.endswith((".tar.gz", ".tgz")):
                with tarfile.open(archive_path, "r:gz") as tf:
                    tf.extractall(dest_dir)
            elif name.endswith(".zip"):
                with zipfile.ZipFile(archive_path) as zf:
                    zf.extractall(dest_dir)
            else:
                # Ham binary olarak indirildiyse
                if os.path.basename(archive_path) == BIN_NAME:
                    return archive_path
                return None
        except Exception as e:
            self.log_line.emit(f"❌ Arşiv çıkarılamadı: {e}")
            return None
        for root, _dirs, files in os.walk(dest_dir):
            if BIN_NAME in files:
                p = os.path.join(root, BIN_NAME)
                try:
                    os.chmod(p, 0o755)
                except Exception:
                    pass
                return p
        return None


class DepInstallWorker(QThread):
    """Dağıtım paket yöneticisiyle eksik derleme paketlerini kur (sudo ister)."""

    log_line = pyqtSignal(str)
    finished_install = pyqtSignal(bool)

    def __init__(self, cmd, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self._proc = None

    def request_stop(self):
        proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass

    def run(self):
        self.log_line.emit("$ " + " ".join(self.cmd))
        try:
            proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
        except FileNotFoundError as e:
            self.log_line.emit(f"❌ Komut bulunamadı: {e.filename}")
            self.finished_install.emit(False)
            return
        self._proc = proc
        for line in proc.stdout:
            self.log_line.emit(line.rstrip())
        rc = proc.wait()
        if rc == 0:
            self.log_line.emit("✓ Bağımlılık kurulumu tamamlandı.")
            self.finished_install.emit(True)
        else:
            self.log_line.emit(f"❌ Paket yöneticisi {rc} koduyla çıktı. "
                               f"(sudo yetkisi gerekiyor olabilir.)")
            self.finished_install.emit(False)


class LlamaCppManagerDialog(QDialog):
    """llama.cpp Yöneticisi / Kurucu dialog'u."""

    def __init__(self, translations_func=None, log_func=None, parent=None):
        super().__init__(parent)
        self._translations = translations_func or (lambda k, d: d)
        self._log_func = log_func
        self.setWindowTitle(self._tr("llm_title", "llama.cpp Yöneticisi / Kurucu"))
        self.resize(780, 640)

        self._build_worker = None
        self._prebuilt_worker = None
        self._dep_worker = None
        self._scan_worker = None
        self._build_tools = {}
        self._pm = detect_package_manager()

        layout = QVBoxLayout(self)

        # 1) Donanım tespiti
        hw_group = QGroupBox(self._tr("llm_hardware_group", "Donanım Tespiti"))
        hw_layout = QVBoxLayout(hw_group)
        self.hw_status_label = QLabel(self._tr("llm_scan_running", "Donanım taranıyor..."))
        self.hw_status_label.setWordWrap(True)
        self.reco_banner = QLabel()
        self.reco_banner.setWordWrap(True)
        self.reco_banner.setStyleSheet(
            "padding: 6px; background-color: #e8f0fe; border: 1px solid #4a90d9;"
            "border-radius: 4px;")
        hw_layout.addWidget(self.hw_status_label)
        hw_layout.addWidget(self.reco_banner)
        layout.addWidget(hw_group)

        # 2) Backend seçimi
        backend_group = QGroupBox(self._tr("llm_backend_group", "Hedef Backend"))
        backend_layout = QVBoxLayout(backend_group)
        self.backend_radios = {}
        for key in BACKEND_ORDER:
            r = QRadioButton(self._tr(f"llm_backend_{key}", BACKENDS[key][0]))
            self.backend_radios[key] = r
            backend_layout.addWidget(r)
        layout.addWidget(backend_group)

        # 3) Bağımlılıklar
        deps_group = QGroupBox(self._tr("llm_deps_group", "Bağımlılıklar & Derleme Araçları"))
        deps_layout = QVBoxLayout(deps_group)
        self.pm_label = QLabel()
        self.tools_label = QLabel()
        self.tools_label.setWordWrap(True)
        self.dep_check_btn = QPushButton(self._tr("llm_deps_check", "Kontrol Et"))
        self.dep_check_btn.clicked.connect(self.refresh_dep_status)
        self.dep_install_btn = QPushButton(self._tr("llm_deps_install", "Eksikleri Yükle (sudo)"))
        self.dep_install_btn.clicked.connect(self.install_missing_deps)
        deps_btn_row = QHBoxLayout()
        deps_btn_row.addWidget(self.dep_check_btn)
        deps_btn_row.addWidget(self.dep_install_btn)
        deps_layout.addWidget(self.pm_label)
        deps_layout.addWidget(self.tools_label)
        deps_layout.addLayout(deps_btn_row)
        layout.addWidget(deps_group)

        # 4) Option A: kaynak derleme
        build_group = QGroupBox(self._tr("llm_build_group", "Kaynaktan Derle (Option A)"))
        build_layout = QHBoxLayout(build_group)
        self.build_start_btn = QPushButton(self._tr("llm_build_start", "Derlemeyi Başlat"))
        self.build_start_btn.clicked.connect(self.start_build)
        self.stop_btn = QPushButton(self._tr("llm_stop", "Durdur"))
        self.stop_btn.clicked.connect(self.stop_all)
        self.stop_btn.setEnabled(False)
        build_layout.addWidget(self.build_start_btn)
        build_layout.addWidget(self.stop_btn)
        layout.addWidget(build_group)

        # 5) Option B: hazır ikili
        pre_group = QGroupBox(self._tr("llm_prebuilt_group", "Hazır İkili İndir (Option B)"))
        pre_layout = QHBoxLayout(pre_group)
        self.prebuilt_btn = QPushButton(self._tr("llm_prebuilt_start", "İndir ve Kur"))
        self.prebuilt_btn.clicked.connect(self.start_prebuilt)
        pre_layout.addWidget(self.prebuilt_btn)
        layout.addWidget(pre_group)

        # 6) İlerleme + log
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_view, stretch=1)

        self.refresh_dep_status()
        self._append_log(self._tr("llm_intro",
                                  "Not: Derleme birkaç dakika sürebilir. İşlemlerin"
                                  " çıktısı aşağıdaki günlükte görünür."))

        # Açılışta donanım taraması
        self._scan_worker = HardwareScanWorker(self)
        self._scan_worker.finished_scan.connect(self.on_hardware_scanned)
        self._scan_worker.start()

    def _tr(self, key, default):
        return self._translations(key, default)

    def _append_log(self, text):
        self.log_view.appendPlainText(text)

    def selected_backend(self):
        for key, radio in self.backend_radios.items():
            if radio.isChecked():
                return key
        return None

    # ---------------- Donanım tespiti ----------------

    def on_hardware_scanned(self, result):
        tools = result.get("tools", {})
        vendor = result.get("vendor")
        rec = result.get("recommendation", "cpu")
        gpus = result.get("gpus", [])
        parts = [f"{'✓' if tools.get(t) else '✗'} {t}"
                 for t in ("nvidia-smi", "nvcc", "rocminfo", "vulkaninfo", "clinfo", "lspci")]
        text = " ".join(parts)
        if gpus:
            text += "\n" + "\n".join(gpus[:3])
        self.hw_status_label.setText(text)

        banner_defaults = {
            "llm_reco_nvidia_cuda":
                "NVIDIA GPU algılandı ve CUDA Toolkit bulundu — CUDA backend'i önerilir.",
            "llm_reco_nvidia_vulkan":
                "NVIDIA GPU algılandı. CUDA Toolkit bulunamadı — en iyi uyumluluk için Vulkan önerilir.",
            "llm_reco_amd_rocm":
                "AMD GPU ve ROCm stack algılandı — ROCm (HIP) backend'i önerilir; Vulkan da evrensel bir alternatiftir.",
            "llm_reco_amd_vulkan":
                "AMD GPU algılandı. En iyi uyumluluk için Vulkan backend'i önerilir.",
            "llm_reco_intel":
                "Intel GPU algılandı — Vulkan önerilir; Intel ARC/iGPU için SYCL da kullanılabilir.",
            "llm_reco_cpu":
                "GPU bulunamadı (veya tespit araçları eksik) — Sadece CPU derlemesi önerilir.",
        }
        key = result.get("banner_key", "llm_reco_cpu")
        self.reco_banner.setText(self._tr(key, banner_defaults.get(key, "")))

        # Önerilen backend'i otomatik seç
        radio = self.backend_radios.get(rec)
        if radio is not None:
            radio.setChecked(True)

    # ---------------- Bağımlılıklar ----------------

    def refresh_dep_status(self):
        tools = check_build_tools()
        self._build_tools = tools
        pm = detect_package_manager()
        self._pm = pm
        pm_text = pm if pm else self._tr("llm_pm_none", "bilinmiyor")
        self.pm_label.setText(
            f"{self._tr('llm_pm_label', 'Paket yöneticisi:')} {pm_text}")
        ok_compiler = bool(tools.get("g++") or tools.get("clang"))
        lines = [f"{'✓' if tools.get(t) else '✗'} {t}"
                 for t in ("cmake", "git", "g++", "clang", "make")]
        lines.append(f"{'✓' if ok_compiler else '✗'} " +
                     self._tr("llm_compiler_ok", "derleyici (g++ veya clang)"))
        self.tools_label.setText("\n".join(lines))
        missing = not (tools.get("cmake") and tools.get("git") and ok_compiler)
        self.dep_install_btn.setEnabled(bool(missing and pm is not None))

    def install_missing_deps(self):
        if self._dep_worker is not None and self._dep_worker.isRunning():
            return
        if not self._pm:
            self._append_log("⚠ Bilinen bir paket yöneticisi bulunamadı "
                             "(apt/dnf/pacman/zypper).")
            return
        cmd = DEP_SPECS.get(self._pm)
        if not cmd:
            return
        self.dep_install_btn.setEnabled(False)
        self._dep_worker = DepInstallWorker(cmd, self)
        self._dep_worker.log_line.connect(self._append_log)
        self._dep_worker.finished_install.connect(self.on_deps_finished)
        self._dep_worker.start()

    def on_deps_finished(self, ok):
        self.dep_install_btn.setEnabled(True)
        self.refresh_dep_status()
        if ok:
            self._append_log("✓ Bağımlılıklar kuruldu. Derlemeye hazırsınız.")
        else:
            self._append_log("⚠ Bağımlılık kurulumu başarısız oldu; log'a bakın.")

    # ---------------- Option A: Kaynak derleme ----------------

    def start_build(self):
        if self._build_worker is not None and self._build_worker.isRunning():
            return
        backend = self.selected_backend()
        if backend is None:
            self._append_log("⚠ Lütfen bir backend seçin.")
            return
        tools = check_build_tools()
        ok_compiler = bool(tools.get("g++") or tools.get("clang"))
        if not (tools.get("cmake") and tools.get("git") and ok_compiler):
            self._append_log("⚠ Uyarı: cmake/git/derleyici eksik olabilir; "
                             "önce 'Eksikleri Yükle' butonunu deneyin.")
        self.progress_bar.setValue(0)
        self._set_busy(True, kind="build")
        self._build_worker = BuildWorker(backend, self)
        self._build_worker.log_line.connect(self._append_log)
        self._build_worker.progress.connect(self.progress_bar.setValue)
        self._build_worker.finished_build.connect(self.on_build_finished)
        self._build_worker.start()

    def on_build_finished(self, ok, path):
        self._set_busy(False, kind="build")
        if ok:
            msg = f"✓ llama-server kuruldu: {path}"
            self._append_log(msg)
            if self._log_func:
                self._log_func(msg)
        else:
            self._append_log("❌ Derleme başarısız oldu. Log yukarıda.")
            if self._log_func:
                self._log_func("❌ llama.cpp derlemesi başarısız oldu.")

    # ---------------- Option B: Hazır ikili ----------------

    def start_prebuilt(self):
        if self._prebuilt_worker is not None and self._prebuilt_worker.isRunning():
            return
        self.progress_bar.setValue(0)
        self._set_busy(True, kind="prebuilt")
        self._prebuilt_worker = PrebuiltWorker(self)
        self._prebuilt_worker.log_line.connect(self._append_log)
        self._prebuilt_worker.progress.connect(self.progress_bar.setValue)
        self._prebuilt_worker.finished_install.connect(self.on_prebuilt_finished)
        self._prebuilt_worker.start()

    def on_prebuilt_finished(self, ok, path):
        self._set_busy(False, kind="prebuilt")
        if ok:
            msg = f"✓ llama-server (hazır ikili) kuruldu: {path}"
            self._append_log(msg)
            if self._log_func:
                self._log_func(msg)
        else:
            self._append_log("❌ Hazır ikili indirme/kurulum başarısız oldu. Log yukarıda.")
            if self._log_func:
                self._log_func("❌ llama.cpp hazır ikili indirme başarısız oldu.")

    # ---------------- Genel ----------------

    def _set_busy(self, busy, kind=None):
        if kind == "build" or kind is None:
            self.build_start_btn.setEnabled(not busy)
        if kind == "prebuilt" or kind is None:
            self.prebuilt_btn.setEnabled(not busy)
        any_running = ((self._build_worker is not None and self._build_worker.isRunning())
                       or (self._prebuilt_worker is not None and self._prebuilt_worker.isRunning())
                       or (self._dep_worker is not None and self._dep_worker.isRunning()))
        if kind is None:
            # stop butonu: herhangi bir worker çalışıyorsa aktif
            self.stop_btn.setEnabled(any_running)
        else:
            self.stop_btn.setEnabled(busy or any_running)

    def stop_all(self):
        for w in (self._build_worker, self._prebuilt_worker, self._dep_worker):
            if w is not None and hasattr(w, "request_stop"):
                w.request_stop()
        self._append_log("⚠ Durdurma istendi...")

    def closeEvent(self, event):
        # Dialog kapatılırken çalışan işlemleri iptal et ve thread'lerin
        # bitmesini bekle (Qt "Destroyed while thread running" uyarısını önler).
        workers = (self._build_worker, self._prebuilt_worker, self._dep_worker,
                   self._scan_worker)
        for w in workers:
            if w is not None and w.isRunning() and hasattr(w, "request_stop"):
                w.request_stop()
        for w in workers:
            if w is not None and w.isRunning():
                w.wait(5000)
        event.accept()
