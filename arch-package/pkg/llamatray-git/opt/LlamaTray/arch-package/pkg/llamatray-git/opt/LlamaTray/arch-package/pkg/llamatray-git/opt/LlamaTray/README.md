# 🦙 LlamaTray

[English](#english) | [Türkçe](#türkçe)

---

## English

LlamaTray is a lightweight and stable PyQt6-based **Llama.cpp (llama-server)** management utility designed for Linux (specifically Arch Linux / CachyOS). Seamlessly integrating into the system tray, it allows you to start, stop, and monitor local AI models with a single click while real-time tracking system resources.

### ✨ Features

- **Effortless Server Management:** Spin up or shut down your local AI models (`llama-server`) with a single click from the GUI.
- **Zombie Process Prevention:** When closed via the top-right (X) button or the tray icon, the background `llama-server` process is automatically terminated, cleanly freeing up VRAM and CPU.
- **Real-Time Resource Monitoring:** Track CPU, RAM, GPU, and VRAM utilization instantly via clean visual progress bars.
- **Advanced Configuration:** Customize GPU layers, context size, port, and extra parameters through an intuitive settings panel.
- **Persistent Settings:** All preferences are automatically saved to `~/.llamatray/config.json` and restored on next launch.
- **Native Linux Integration:** Native Wayland and KDE Plasma support ensuring a minimal footprint on your desktop ecosystem.
- **GPU Agnostic:** Supports NVIDIA (via pynvml/nvidia-smi), AMD (via rocm-smi/sysfs), and integrated GPUs.

### 📂 Repository Structure

```text
LlamaTray/
├── LlamaTray/             # Main Python Package Directory
│   ├── __init__.py        # Package initializer
│   ├── main.py            # Entry point
│   ├── ui.py              # PyQt6 UI & System tray logic
│   ├── server.py          # Llama-server process manager
│   ├── monitor.py         # Hardware metric polling module
│   └── assets/            # App icons and graphics
│       ├── icon.png       # Default silver llama icon
│       └── green_icon.png # Green llama icon (unused in static mode)
├── requirements.txt       # Python dependencies
└── README.md              # Multi-language documentation (this file)
```

### 🚀 Quick Start

#### Prerequisites

- Python 3.10+
- llama.cpp installed with `llama-server` in your PATH
- A GGUF model file

#### Installation

```bash
# Clone the repository
git clone https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray.git
cd LlamaTray

# (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m LlamaTray.main
```

#### Arch Linux (via PKGBUILD)

If you have cloned the repository including the `arch-package/` directory:

```bash
cd arch-package
makepkg -si
```

### 🖱️ Usage

1. Launch LlamaTray from your application menu or terminal.
2. Click **"Model Seç" (Browse)** to select a `.gguf` model file.
3. (Optional) Adjust advanced settings: GPU layers, context size, port, extra parameters.
4. Click **"Sunucuyu Başlat" (Start Server)** to launch `llama-server`.
5. Monitor CPU, RAM, GPU, VRAM usage in real-time.
6. Click **"Sunucuyu Durdur" (Stop Server)** or close the window to terminate.

> **Note:** Closing the window automatically terminates the llama-server process — no zombie processes left behind.

### ⚙️ Advanced Settings

| Setting | Description | Default |
|---------|-------------|---------|
| GPU Layers | Number of layers to offload to GPU | 99 |
| Context Size | Context window size (512-1,000,000) | 32768 |
| Port | Server port (1024-65535) | 8080 |
| Extra Parameters | Additional llama-server flags | (optional) |

### 🧩 Dependencies

- **PyQt6** — GUI framework
- **psutil** — CPU/RAM monitoring
- **pynvml** — NVIDIA GPU monitoring (optional, falls back to nvidia-smi)
- **llama-server** — Part of [llama.cpp](https://github.com/ggerganov/llama.cpp)

### 📄 License

This project is licensed under the MIT License.

---

## Türkçe

LlamaTray, Linux (özellikle Arch Linux / CachyOS) için geliştirilmiş, PyQt6 tabanlı hafif ve kararlı bir **Llama.cpp (llama-server)** yönetim aracıdır. Sistem tepsisine sorunsuz bir şekilde entegre olarak, yerel yapay zeka modellerinizi tek tıkla başlatmanıza, durdurmanıza ve izlemenize olanak tanır.

### ✨ Özellikler

- **Kolay Sunucu Yönetimi:** Yerel AI modellerinizi (`llama-server`) tek tıkla başlatın veya durdurun.
- **Zombi Süreç Koruması:** Pencere kapatıldığında (X butonu) veya tepsi ikonundan çıkıldığında, arka plandaki `llama-server` süreci otomatik olarak sonlandırılır, VRAM ve CPU temizlenir.
- **Gerçek Zamanlı Kaynak İzleme:** CPU, RAM, GPU ve VRAM kullanımını görsel ilerleme çubuklarıyla anlık olarak takip edin.
- **Gelişmiş Yapılandırma:** GPU katmanları, context boyutu, port ve ek parametreleri sezgisel bir ayar panelinden özelleştirin.
- **Kalıcı Ayarlar:** Tüm tercihler otomatik olarak `~/.llamatray/config.json` dosyasına kaydedilir ve bir sonraki açılışta geri yüklenir.
- **Yerel Linux Entegrasyonu:** Wayland ve KDE Plasma desteği ile masaüstü ortamınıza minimum ayak izi bırakır.
- **GPU Bağımsız:** NVIDIA (pynvml/nvidia-smi), AMD (rocm-smi/sysfs) ve tümleşik GPU'ları destekler.

### 📂 Depo Yapısı

```text
LlamaTray/
├── LlamaTray/             # Ana Python Paket Dizini
│   ├── __init__.py        # Paket başlatıcı
│   ├── main.py            # Giriş noktası
│   ├── ui.py              # PyQt6 arayüzü ve sistem tepsisi mantığı
│   ├── server.py          # Llama-server süreç yöneticisi
│   ├── monitor.py         # Donanım metrik toplama modülü
│   └── assets/            # Uygulama ikonları ve grafikleri
│       ├── icon.png       # Varsayılan gümüş lama ikonu
│       └── green_icon.png # Yeşil lama ikonu (statik modda kullanılmaz)
├── requirements.txt       # Python bağımlılıkları
└── README.md              # Çok dilli dokümantasyon (bu dosya)
```

### 🚀 Hızlı Başlangıç

#### Ön Gereksinimler

- Python 3.10+
- `llama-server` PATH'te olacak şekilde llama.cpp kurulu
- Bir GGUF model dosyası

#### Kurulum

```bash
# Depoyu klonlayın
git clone https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray.git
cd LlamaTray

# (İsteğe bağlı) Sanal ortam oluşturun ve etkinleştirin
python -m venv venv
source venv/bin/activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Uygulamayı çalıştırın
python -m LlamaTray.main
```

### 🖱️ Kullanım

1. LlamaTray'i uygulama menünüzden veya terminalden başlatın.
2. **"Model Seç"** butonuna tıklayarak bir `.gguf` model dosyası seçin.
3. (İsteğe bağlı) Gelişmiş ayarları yapılandırın: GPU katmanları, context boyutu, port, ek parametreler.
4. **"Sunucuyu Başlat"** butonuna tıklayarak `llama-server`'ı başlatın.
5. CPU, RAM, GPU, VRAM kullanımını gerçek zamanlı olarak izleyin.
6. **"Sunucuyu Durdur"** butonuna tıklayarak veya pencereyi kapatarak sunucuyu sonlandırın.

> **Not:** Pencere kapatıldığında llama-server süreci otomatik olarak sonlandırılır — arka planda zombi süreç kalmaz.

### ⚙️ Gelişmiş Ayarlar

| Ayar | Açıklama | Varsayılan |
|------|----------|------------|
| GPU Katmanları | GPU'ya yüklenecek katman sayısı | 99 |
| Context Boyutu | Context penceresi boyutu (512-1.000.000) | 32768 |
| Port | Sunucu portu (1024-65535) | 8080 |
| Ek Parametreler | Ek llama-server flag'leri | (isteğe bağlı) |

### 🧩 Bağımlılıklar

- **PyQt6** — GUI framework
- **psutil** — CPU/RAM izleme
- **pynvml** — NVIDIA GPU izleme (isteğe bağlı, nvidia-smi'ye düşer)
- **llama-server** — [llama.cpp](https://github.com/ggerganov/llama.cpp) parçası

### 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır.