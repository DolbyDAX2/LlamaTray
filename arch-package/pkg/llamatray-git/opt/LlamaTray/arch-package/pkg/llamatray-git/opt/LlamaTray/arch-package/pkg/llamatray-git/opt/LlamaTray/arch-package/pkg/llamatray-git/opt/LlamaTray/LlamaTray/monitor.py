"""
Sistem kaynaklarını izleyen modül.
CPU, RAM, GPU ve VRAM kullanım bilgilerini sağlar.
"""

import os
import subprocess


class SystemMonitor:
    """Sistem kaynaklarını izleyen sınıf"""

    def __init__(self):
        self.gpu_available = False
        self.vram_available = False
        self.gpu_method = None
        self._init_gpu()

    def _init_gpu(self):
        """GPU izleme yöntemini belirle"""
        # 1. pynvml (NVIDIA) dene
        try:
            import pynvml
            pynvml.nvmlInit()
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
                    self.vram_available = True  # AMD'de genelde VRAM bilgisi var
                    return

                # Diğer card numaralarını dene
                for device in os.listdir(drm_path):
                    if device.startswith("card") and device != amd_card:
                        gpu_busy_path = os.path.join(drm_path, device, "device", "gpu_busy_percent")
                        if os.path.exists(gpu_busy_path):
                            self.gpu_available = True
                            self.gpu_method = "amdgpu_sysfs"
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

    def get_cpu_usage(self):
        """CPU kullanım yüzdesini al"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
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

    def get_gpu_usage(self):
        """GPU kullanım yüzdesini al"""
        if not self.gpu_available:
            return None

        if self.gpu_method == "nvidia":
            try:
                import pynvml
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                return pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            except Exception:
                return 0

        elif self.gpu_method == "nvidia_smi":
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return int(result.stdout.strip().split()[0])
            except Exception:
                pass

        elif self.gpu_method == "rocm_smi":
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showuse", "--csv"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    # CSV çıktısını parse et
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if "GPU activity" in line or "use" in line.lower():
                            # Değeri çıkar
                            parts = line.split(',')
                            for part in parts:
                                try:
                                    value = int(part.strip().replace('%', ''))
                                    if 0 <= value <= 100:
                                        return value
                                except ValueError:
                                    pass
            except Exception:
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
            except Exception:
                pass

        return 0

    def get_vram_usage(self):
        """VRAM kullanım yüzdesini al"""
        if not self.vram_available:
            return None

        if self.gpu_method == "nvidia":
            try:
                import pynvml
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                return (info.used / info.total) * 100
            except Exception:
                return 0

        elif self.gpu_method == "nvidia_smi":
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().replace(" MiB", "").split(", ")
                    used = float(parts[0])
                    total = float(parts[1])
                    return (used / total) * 100
            except Exception:
                pass

        elif self.gpu_method == "rocm_smi":
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showmeminfo", "vram", "--csv"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    # VRAM bilgilerini parse et
                    used = 0
                    total = 0
                    for line in result.stdout.strip().split('\n'):
                        if "VRAM Usage" in line or "vram" in line.lower():
                            parts = line.split(',')
                            for part in parts:
                                part = part.strip()
                                if "used" in part.lower():
                                    try:
                                        used = int(part.replace('MB', '').replace(',', ''))
                                    except ValueError:
                                        pass
                                elif "total" in part.lower():
                                    try:
                                        total = int(part.replace('MB', '').replace(',', ''))
                                    except ValueError:
                                        pass
                    if total > 0:
                        return (used / total) * 100
            except Exception:
                pass

        elif self.gpu_method == "amdgpu_sysfs":
            # mem_info_vram_used ve mem_info_vram_total dosyalarını oku
            try:
                drm_path = "/sys/class/drm"
                used = 0
                total = 0
                for device in os.listdir(drm_path):
                    if device.startswith("card"):
                        vram_used_path = os.path.join(drm_path, device, "device", "mem_info_vram_used")
                        vram_total_path = os.path.join(drm_path, device, "device", "mem_info_vram_total")
                        if os.path.exists(vram_used_path):
                            with open(vram_used_path, 'r') as f:
                                used = int(f.read().strip())
                        if os.path.exists(vram_total_path):
                            with open(vram_total_path, 'r') as f:
                                total = int(f.read().strip())
                        if total > 0:
                            break
                if total > 0:
                    return (used / total) * 100
            except Exception:
                pass

        return 0