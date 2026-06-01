"""
LlamaServer yönetimi modülü.
llama-server sürecini başlatma, durdurma ve yönetme işlemlerini içerir.
"""

import os
import subprocess
import shlex
import socket
import time
from PyQt6.QtCore import QProcess, QProcessEnvironment


def is_port_in_use(port):
    """Port'un kullanımda olup olmadığını kontrol et"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception:
        return False


def cleanup_old_processes(port):
    """Eski llama-server süreçlerini temizle ve port'u boşalt"""
    # Port'u kontrol et ve gerekirse force close yap
    if is_port_in_use(port):
        try:
            # lsof ile port kullanıcısını bul ve sonlandır (shell=False güvenlik)
            result = subprocess.run(
                ["bash", "-c", f"lsof -ti:{port} | xargs kill -9"],
                capture_output=True,
                text=True,
                timeout=2
            )
        except Exception:
            pass


class LlamaServerManager(QProcess):
    """Llama-server sürecini yöneten sınıf"""

    def __init__(self, log_callback=None):
        super().__init__()
        self.server_running = False
        self.host = "127.0.0.1"
        self.port = 8080
        self.log_callback = log_callback
        
        # QProcess ayarları
        self.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        
        # Sinyalleri bağla
        self.readyReadStandardOutput.connect(self.read_output)
        self.started.connect(self.on_started)
        self.finished.connect(self.on_finished)
        self.errorOccurred.connect(self.on_error)

    def log(self, message):
        """Log mesajı yaz"""
        if self.log_callback:
            self.log_callback(message)

    def read_output(self):
        """QProcess çıktısını oku ve log'a yaz"""
        try:
            data = self.readAllStandardOutput().data()
            if data:
                message = data.decode('utf-8', errors='replace').strip()
                if message:
                    self.log(message)
        except Exception as e:
            self.log(f"⚠ Output read error: {e}")

    def on_started(self):
        """Process başarıyla başlatıldığında"""
        self.server_running = True
        self.log(f"✓ Server started successfully (PID: {self.processId()})")
        self.log("=" * 60)

    def on_finished(self, exit_code, exit_status):
        """Process bittiğinde"""
        self.log(f"⚠ Server closed (Exit Code: {exit_code})")
        self.server_running = False

    def on_error(self, error):
        """Process başlatılırken hata oluştuğunda"""
        error_messages = {
            QProcess.ProcessError.FailedToStart: "❌ Error: llama-server could not be started. File not found or no execute permission.",
            QProcess.ProcessError.Crashed: "❌ Error: llama-server crashed.",
            QProcess.ProcessError.Timedout: "❌ Error: llama-server startup timed out.",
            QProcess.ProcessError.WriteError: "❌ Error: Failed to write data to server.",
            QProcess.ProcessError.ReadError: "❌ Error: Failed to read data from server.",
            QProcess.ProcessError.UnknownError: "❌ Error: Unknown error occurred.",
        }
        error_msg = error_messages.get(error, f"❌ Error: QProcess error ({error})")
        self.log(error_msg)
        self.server_running = False

    def find_llama_server(self):
        """llama-server çalıştırılabilir dosyasını bul"""
        llama_server_cmd = None

        # Önce PATH'te ara
        try:
            result = subprocess.run(
                ["which", "llama-server"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                llama_server_cmd = result.stdout.strip()
                self.log(f"✓ llama-server found: {llama_server_cmd}")
                return llama_server_cmd
        except Exception as e:
            self.log(f"⚠ PATH search failed: {e}")

        # Bulunamadıysa yaygın konumları dene
        common_paths = [
            "/usr/bin/llama-server",
            "/usr/local/bin/llama-server",
            os.path.expanduser("~/.local/bin/llama-server"),
            os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
            os.path.expanduser("~/llama.cpp/server/llama-server"),
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                self.log(f"✓ llama-server found: {path}")
                return path

        # Son çare olarak llama-server'ı doğrudan dene
        self.log("⚠ Looking for llama-server in system commands...")
        return "llama-server"

    def start_server(self, model_path, gpu_layers=99, context_size=8192, port=8080, extra_params=""):
        """
        Llama-server'ı başlat

        Args:
            model_path: GGUF model dosyasının yolu
            gpu_layers: GPU'ya yüklenecek katman sayısı
            context_size: Context boyutu
            port: Sunucu portu
            extra_params: Ek parametreler
        """
        # Ön kontroller
        if self.server_running:
            self.log("⚠ Server is already running.")
            return False

        if not model_path:
            self.log("❌ Error: Please select a model file first.")
            return False

        if not os.path.exists(model_path):
            self.log(f"❌ Error: Model file not found: {model_path}")
            return False

        # Model boyutu kontrol et
        try:
            model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
            self.log(f"📦 Model size: {model_size_mb:.2f} MB")
            if model_size_mb < 100:
                self.log(f"⚠ Warning: Model file seems very small ({model_size_mb:.2f} MB). Is it a valid GGUF file?")
        except Exception as e:
            self.log(f"⚠ Could not check model size: {e}")

        # Context size validation
        try:
            context_size = int(context_size)
            if context_size < 512 or context_size > 1000000:
                self.log(f"❌ Error: Context size invalid ({context_size}). Must be between 512 and 1000000.")
                return False
        except ValueError:
            self.log(f"❌ Error: Context size is not a number: {context_size}")
            return False

        # Port validation
        if not (1024 <= port <= 65535):
            self.log(f"❌ Error: Port invalid ({port}). Must be between 1024 and 65535.")
            return False

        # Öncesi: Eski zombi süreçleri temizle
        self.log("🧹 Cleaning up old llama-server processes and checking ports...")
        cleanup_old_processes(port)
        
        # Port'un boş olup olmadığını kontrol et (temizlik sonrası)
        time.sleep(1)
        if is_port_in_use(port):
            self.log(f"❌ Error: Port {port} could not be cleared. Try a different port or check with lsof.")
            return False
        self.log(f"✓ Port {port} is free.")
        
        # Port ve host'u kaydet
        self.port = port
        self.host = "127.0.0.1"

        llama_server_cmd = self.find_llama_server()
        if not llama_server_cmd:
            self.log("❌ Error: llama-server not found. Make sure llama.cpp is installed.")
            return False
        # Bulunan komutun çalıştırılabilir olduğunu kontrol et
        if os.path.isabs(llama_server_cmd) and not os.access(llama_server_cmd, os.X_OK):
            self.log(f"❌ Error: {llama_server_cmd} is not executable.")
            return False
        if not os.path.isabs(llama_server_cmd):
            # Göreceli yol (PATH'te aranacak) - varlığını kontrol et
            try:
                result = subprocess.run(["which", llama_server_cmd], capture_output=True, text=True, timeout=2)
                if result.returncode != 0:
                    self.log(f"❌ Error: '{llama_server_cmd}' not found in PATH. Make sure llama.cpp is installed.")
                    return False
            except Exception:
                self.log(f"❌ Error: Error searching for '{llama_server_cmd}'.")
                return False

        # Komutu oluştur
        args = ["-m", model_path]
        args.extend(["--n-gpu-layers", str(gpu_layers)])
        args.extend(["--ctx-size", str(context_size)])
        args.extend(["--port", str(port)])

        # Ek parametreleri ekle - güvenli parsing
        if extra_params:
            extra_params = extra_params.strip()
            if extra_params:
                try:
                    extra_args = shlex.split(extra_params)
                    args.extend(extra_args)
                    self.log(f"📝 Extra parameters added: {' '.join(extra_args)}")
                except ValueError as e:
                    self.log(f"❌ Error: Could not parse extra parameters: {e}. E.g.: -t 8 --flash-attn")
                    return False

        self.log(f"🚀 Starting server: {llama_server_cmd} {' '.join(args)}")
        self.log("=" * 60)

        try:
            # Ortam ayarları
            env = QProcessEnvironment.systemEnvironment()
            self.setProcessEnvironment(env)
            
            # İşlemi başlat
            self.start(llama_server_cmd, args)
            
            # Başlatma başarısı - hemen True yapma, sinyalleri bekle
            # QProcess başlatıldı, ama gerçekten başladı mı diye on_started sinyali bekleyecek
            self.log("⏳ Server startup in progress...")
            return True
            
        except FileNotFoundError as e:
            self.log(f"❌ Error: llama-server not found: {e}")
            self.server_running = False
            return False
        except Exception as e:
            self.log(f"❌ Error: Server could not be started: {type(e).__name__}: {e}")
            self.server_running = False
            return False

    def cleanup_server_process(self):
        """Sunucu sürecini temizle (zombi süreçleri önle)"""
        if not self.server_running:
            return

        self.log("🛑 Starting server cleanup...")
        try:
            # 1. Önce terminate (SIGTERM) gönder
            self.terminate()
            self.log("📤 SIGTERM signal sent...")
            
            # 2. 3 saniye bekle (timeout mekanizması)
            if not self.waitForFinished(3000):
                self.log("⚠ Server did not shut down gracefully, sending SIGKILL...")
                # 3. Hala kapanmadıysa kill (SIGKILL) ile zorla kapat
                self.kill()
                if not self.waitForFinished(5000):
                    self.log("⚠ Warning: Server could not be forcefully terminated, performing system-level cleanup...")
            else:
                self.log("✓ Server terminated successfully.")
        except Exception as e:
            self.log(f"⚠ Cleanup error: {e}")
        finally:
            self.server_running = False

    def stop_server(self):
        """Sunucuyu durdur"""
        if not self.server_running:
            self.log("ℹ Server is already stopped.")
            return

        self.log("🛑 Sending server stop request...")
        
        # 1. Önce HTTP API üzerinden nazikçe kapatmayı dene (llama-server /exit endpoint)
        try:
            import requests
            url = f"http://{self.host}:{self.port}/exit"
            self.log(f"📤 Sending HTTP API shutdown request: {url}")
            response = requests.post(url, timeout=2)
            self.log(f"✓ HTTP API shutdown request sent (Response: {response.status_code})")
        except ImportError:
            self.log("⚠ requests library not installed, skipping HTTP API shutdown.")
        except Exception as e:
            self.log(f"⚠ HTTP API shutdown failed: {e}")

        # 2. Süreç grubunu temizle (terminate + wait)
        self.cleanup_server_process()
        
        # 3. Son kontrol: port hala açık mı?
        time.sleep(1)
        if is_port_in_use(self.port):
            self.log(f"⚠ Port {self.port} is still in use, forcefully cleaning...")
            cleanup_old_processes(self.port)
        
        self.server_running = False
        self.log("=" * 60)

    def is_running(self):
        """Sunucunun çalışıp çalışmadığını kontrol et"""
        return self.server_running