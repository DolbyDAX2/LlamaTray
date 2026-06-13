"""
Sistem kaynaklarını izleyen modül.
CPU, RAM, GPU ve VRAM kullanım bilgilerini sağlar.
"""

import os
import subprocess
import warnings
# pynvml/nvidia-ml-py FutureWarning'ini sessize al (pynvml deprecated, nvidia-ml-py öneriliyor)
warnings.filterwarnings("ignore", message="The pynvml package is deprecated")


class SystemMonitor:
    """Sistem kaynaklarını izleyen sınıf"""

    def __init__(self):
        self.gpu_available = False
        self.vram_available = False
        self.gpu_method = None
        self._nvml_initialized = False
        self._init_gpu()

    def _init_gpu(self):
        """GPU izleme yöntemini belirle"""
        # Başlangıçta varsayılan değerleri sıfırla
        self.gpu_available = False
        self.vram_available = False
        self.gpu_method = None

        # 1. pynvml (NVIDIA) dene - nvidia-ml-py de aynı import adını kullanır
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml_initialized = True
            pynvml.nvmlDeviceGetCount()
            self.gpu_available = True
            self.vram_available = True
            self.gpu_method = "nvidia"
            return
        except Exception:
            pass

        # 2. subprocess ile rocm-smi dene (AMD için öncelikli)
        try:
            result = subprocess.run(
                ["rocm-smi", "--showuse", "--csv"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "GPU" in result.stdout:
                self.gpu_available = True
                self.vram_available = True
                self.gpu_method = "rocm_smi"
                return
        except Exception:
            pass

        # 3. /sys/class/drm/ altındaki GPU'ları kontrol et (AMD/Intel)
        drm_path = "/sys/class/drm"
        if os.path.exists(drm_path):
            # Hangi card numarasının AMD GPU olduğunu bul
            amd_card = None
            for device in os.listdir(drm_path):
                if device.startswith("card"):
                    # GPU adı kontrol et (AMD mi?)
                    name_path = os.path.join(drm_path, device, "device", "name")
                    if os.path.exists(name_path):
                        try:
                            with open(name_path, 'r') as f:
                                name = f.read().strip().lower()
                                if "amd" in name or "radeon" in name or "rade" in name:
                                    amd_card = device
                                    break
                        except Exception:
                            pass

            # Eğer AMD bulunamadıysa ilk card'ı kullan
            if amd_card is None:
                for device in os.listdir(drm_path):
                    if device.startswith("card"):
                        amd_card = device
                        break

            if amd_card:
                # gpu_busy_percent dosyasını kontrol et
                gpu_busy_path = os.path.join(drm_path, amd_card, "device", "gpu_busy_percent")
                if os.path.exists(gpu_busy_path):
                    self.gpu_available = True
                    self.gpu_method = "amdgpu_sysfs"
                    # VRAM bilgisi için mem_info_vram_used dosyasını kontrol et
                    vram_used_path = os.path.join(drm_path, amd_card, "device", "mem_info_vram_used")
                    if os.path.exists(vram_used_path):
                        self.vram_available = True
                    return

                # Diğer card numaralarını dene
                for device in os.listdir(drm_path):
                    if device.startswith("card") and device != amd_card:
                        gpu_busy_path = os.path.join(drm_path, device, "device", "gpu_busy_percent")
                        if os.path.exists(gpu_busy_path):
                            self.gpu_available = True
                            self.gpu_method = "amdgpu_sysfs"
                            # VRAM bilgisi için mem_info_vram_used dosyasını kontrol et
                            vram_used_path = os.path.join(drm_path, device, "device", "mem_info_vram_used")
                            if os.path.exists(vram_used_path):
                                self.vram_available = True
                            return

        # 4. subprocess ile nvidia-smi dene
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.gpu_available = True
                self.vram_available = True
                self.gpu_method = "nvidia_smi"
                return
        except Exception:
            pass

    def _shutdown_gpu(self):
        """GPU kaynaklarını temizle (nvmlShutdown)"""
        if self._nvml_initialized:
            try:
                import pynvml
                pynvml.nvmlShutdown()
            except Exception:
                pass
            finally:
                self._nvml_initialized = False

    def get_cpu_usage(self):
        """CPU kullanım yüzdesini al (non-blocking)"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0)
        except Exception:
            return 0

    def get_ram_usage(self):
        """RAM kullanım yüzdesini al"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.percent
        except Exception:
            return 0

    def get_ram_info(self):
        """(kullanılan_GB, toplam_GB) olarak RAM bilgisini döndür"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024 ** 3)
            total_gb = mem.total / (1024 ** 3)
            return (used_gb, total_gb)
        except Exception:
            return (0, 0)

    def get_gpu_usage(self):
        """GPU kullanım yüzdesini al"""
        if not self.gpu_available:
            return None

        if self.gpu_method == "nvidia":
            try:
                import pynvml
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                return pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            except Exception as e:
                print(f"⚠ GPU usage retrieval failed (nvidia): {e}")
                return 0

        elif self.gpu_method == "nvidia_smi":
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return int(result.stdout.strip().split()[0])
            except Exception as e:
                print(f"⚠ GPU usage retrieval failed (nvidia_smi): {e}")
                pass

        elif self.gpu_method == "rocm_smi":
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showuse", "--csv"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    # CSV çıktısını parse et - başlık satırını atla, ikinci satırdan itibaren değerleri al
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # İlk satırı (başlık) atla
                        if ',' in line:
                            parts = line.split(',')
                            if len(parts) >= 2:
                                try:
                                    value = int(parts[1].strip())
                                    if 0 <= value <= 100:
                                        return value
                                except ValueError:
                                    pass
            except Exception as e:
                print(f"⚠ GPU usage retrieval failed (rocm_smi): {e}")
                pass

        elif self.gpu_method == "amdgpu_sysfs":
            # 1. gpu_busy_percent dosyasını oku
            try:
                drm_path = "/sys/class/drm"
                for device in os.listdir(drm_path):
                    if device.startswith("card"):
                        gpu_busy_path = os.path.join(drm_path, device, "device", "gpu_busy_percent")
                        if os.path.exists(gpu_busy_path):
                            with open(gpu_busy_path, 'r') as f:
                                value = int(f.read().strip())
                                if 0 <= value <= 100:
                                    return value
            except Exception as e:
                print(f"⚠ GPU usage retrieval failed (amdgpu_sysfs): {e}")
                pass

        return 0

    def get_vram_usage(self):
        """VRAM kullanım yüzdesini al"""
        if not self.vram_available:
            return None
        info = self.get_vram_info()
        if info and info[1] > 0:
            return (info[0] / info[1]) * 100
        return 0

    def get_vram_info(self):
        """(kullanılan_GB, toplam_GB) olarak VRAM bilgisini döndür"""
        if not self.vram_available:
            return (0, 0)

        if self.gpu_method == "nvidia":
            try:
                import pynvml
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                return (info.used / (1024**3), info.total / (1024**3))
            except Exception as e:
                print(f"⚠ VRAM info retrieval failed (nvidia): {e}")
                return (0, 0)

        elif self.gpu_method == "nvidia_smi":
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().replace(" MiB", "").split(", ")
                    used_mib = float(parts[0])
                    total_mib = float(parts[1])
                    return (used_mib / 1024, total_mib / 1024)
            except Exception as e:
                print(f"⚠ VRAM info retrieval failed (nvidia_smi): {e}")
                return (0, 0)

        elif self.gpu_method == "rocm_smi":
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showmeminfo", "vram", "--csv"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:
                        if ',' in line:
                            parts = line.split(',')
                            if len(parts) >= 3:
                                try:
                                    total_bytes = int(parts[1].strip())
                                    used_bytes = int(parts[2].strip())
                                    if total_bytes > 0:
                                        return (used_bytes / (1024**3), total_bytes / (1024**3))
                                except ValueError:
                                    pass
            except Exception as e:
                print(f"⚠ VRAM info retrieval failed (rocm_smi): {e}")
                return (0, 0)

        elif self.gpu_method == "amdgpu_sysfs":
            try:
                drm_path = "/sys/class/drm"
                for device in os.listdir(drm_path):
                    if device.startswith("card"):
                        vram_used_path = os.path.join(drm_path, device, "device", "mem_info_vram_used")
                        vram_total_path = os.path.join(drm_path, device, "device", "mem_info_vram_total")
                        used = 0
                        total = 0
                        if os.path.exists(vram_used_path):
                            with open(vram_used_path, 'r') as f:
                                used = int(f.read().strip())
                        if os.path.exists(vram_total_path):
                            with open(vram_total_path, 'r') as f:
                                total = int(f.read().strip())
                        if total > 0:
                            return (used / (1024**3), total / (1024**3))
            except Exception as e:
                print(f"⚠ VRAM info retrieval failed (amdgpu_sysfs): {e}")
                return (0, 0)

        return (0, 0)

    def __del__(self):
        """Kaynakları temizle - nvmlShutdown çağrısı"""
        self._shutdown_gpu()