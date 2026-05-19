"""
LlamaServer yönetimi modülü.
llama-server sürecini başlatma, durdurma ve yönetme işlemlerini içerir.
"""

import os
import subprocess
import shlex
import signal


class LlamaServerManager:
    """Llama-server sürecini yöneten sınıf"""

    def __init__(self, log_callback=None):
        self.server_process = None
        self.server_running = False
        self.host = "127.0.0.1"
        self.port = 8080
        self.log_callback = log_callback

    def log(self, message):
        """Log mesajı yaz"""
        if self.log_callback:
            self.log_callback(message)

    def find_llama_server(self):
        """llama-server çalıştırılabilir dosyasını bul"""
        llama_server_cmd = None

        # Önce PATH'te ara
        try:
            result = subprocess.run(
                ["which", "llama-server"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                llama_server_cmd = result.stdout.strip()
        except Exception:
            pass

        # Bulunamadıysa yaygın konumları dene
        if not llama_server_cmd:
            common_paths = [
                "/usr/bin/llama-server",
                "/usr/local/bin/llama-server",
                os.path.expanduser("~/.local/bin/llama-server"),
                os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
                os.path.expanduser("~/llama.cpp/server/llama-server"),
            ]
            for path in common_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    llama_server_cmd = path
                    break

        if not llama_server_cmd:
            # Son çare olarak llama-server'ı doğrudan dene
            llama_server_cmd = "llama-server"

        return llama_server_cmd

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
        if self.server_running:
            self.log("Sunucu zaten çalışıyor.")
            return False

        if not model_path:
            self.log("Lütfen önce bir model dosyası seçin.")
            return False

        if not os.path.exists(model_path):
            self.log(f"Model dosyası bulunamadı: {model_path}")
            return False

        # Port ve host'u kaydet (HTTP API çağrıları için)
        self.port = port
        self.host = "127.0.0.1"

        llama_server_cmd = self.find_llama_server()

        # Komutu oluştur
        cmd = [llama_server_cmd, "-m", model_path]
        cmd.extend(["--n-gpu-layers", str(gpu_layers)])
        cmd.extend(["--ctx-size", str(context_size)])
        cmd.extend(["--port", str(port)])

        # Ek parametreleri ekle
        if extra_params:
            try:
                extra_args = shlex.split(extra_params)
                cmd.extend(extra_args)
            except ValueError:
                self.log(f"Ek parametreler ayrıştırılamadı: {extra_params}")

        self.log(f"Sunucu başlatılıyor: {' '.join(cmd)}")

        try:
            # preexec_fn=os.setsid ile süreç grubu oluştur
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            self.server_running = True
            self.log("Sunucu başarıyla başlatıldı.")
            return True
        except FileNotFoundError:
            self.log("Hata: llama-server bulunamadı. llama.cpp'in kurulu olduğundan emin olun.")
        except Exception as e:
            self.log(f"Sunucu başlatılamadı: {e}")

        return False

    def cleanup_server_process(self):
        """Sunucu sürecini temizle (zombi süreçleri önle)"""
        if self.server_process is None:
            return

        try:
            # Süreç hala çalışıyor mu kontrol et
            if self.server_process.poll() is None:
                # 1. Önce SIGTERM gönder (nazik kapatma)
                try:
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                except (ProcessLookupError, OSError):
                    pass

                # 2. 2 saniye bekle
                try:
                    self.server_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # 3. Hala kapanmadıysa SIGKILL ile zorla kapat
                    try:
                        os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                        self.server_process.wait(timeout=1)
                    except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
                        pass

                self.log("✓ Temizlik tamamlandı, tüm süreçler sonlandırıldı.")
        except Exception:
            pass
        finally:
            self.server_process = None
            self.server_running = False

    def stop_server(self):
        """Sunucuyu durdur"""
        if not self.server_running:
            self.log("Sunucu zaten durmuş.")
            return

        # 1. Önce HTTP API üzerinden nazikçe kapatmayı dene (llama-server /exit endpoint)
        try:
            import requests
            url = f"http://{self.host}:{self.port}/exit"
            self.log(f"🛑 HTTP API ile kapatma isteği gönderiliyor: {url}")
            requests.post(url, timeout=2)
            self.log("✓ HTTP API kapatma isteği başarıyla gönderildi.")
        except ImportError:
            self.log("⚠ requests kütüphanesi bulunamadı, HTTP API kapatma atlanıyor.")
        except Exception:
            pass

        # 2. Süreç grubunu temizle
        self.cleanup_server_process()
        self.server_running = False

        # 3. Son çare: sistemdeki tüm llama-server süreçlerini zorla sonlandır
        try:
            os.system("killall -9 llama-server 2>/dev/null")
        except Exception:
            pass

    def is_running(self):
        """Sunucunun çalışıp çalışmadığını kontrol et"""
        return self.server_running