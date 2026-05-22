# 🦙 LlamaTray

[English](#english) | [Türkçe](#türkçe)

---

## English

LlamaTray is a lightweight and stable PyQt6-based **Llama.cpp (llama-server)** management utility designed for Linux (specifically Arch Linux / CachyOS). Seamlessly integrating into the system tray, it allows you to start, stop, and monitor local AI models with a single click while real-time tracking system resources.

### ✨ Features

- **Effortless Server Management:** Spin up or shut down your local AI models (`llama-server`) with a single click from the GUI.
- **Zombie Process Prevention:** When closed via the top-right (X) button or the tray icon, the background `llama-server` process is automatically terminated, cleanly freeing up VRAM and CPU. Crash-safe cleanup mechanism included.
- **Real-Time Resource Monitoring:** Track CPU, RAM, GPU, and VRAM utilization instantly via clean visual progress bars (1-second refresh interval).
- **Profile Management:** Save, load, and delete named profiles for different model configurations. Quickly switch between setups.
- **Advanced Configuration:** Customize GPU layers, context size, port, and extra parameters through an intuitive settings panel.
- **Web UI Integration:** One-click button to open the llama.cpp web interface in your default browser after server starts.
- **Persistent Settings & Profiles:** All preferences and profiles are automatically saved to `~/.llamatray/config.json` and `~/.llamatray/profiles.json`, restored on next launch.
- **Native Linux Integration:** Native Wayland and KDE Plasma support ensuring a minimal footprint on your desktop ecosystem.
- **GPU Agnostic:** Supports NVIDIA (via pynvml/nvidia-smi), AMD (via rocm-smi/sysfs), and integrated GPUs.
- **Arch Linux Package:** Pre-built `.pkg.tar.zst` package available for easy installation via `pacman -U`.
- **Crash Handler:** Custom exception hook that cleans up the tray icon and server process even if the application crashes.

### 📦 Installation

#### Arch Linux (Recommended)

Download the latest `.pkg.tar.zst` from the [Releases](https://github.com/DolbyDAX2/LlamaTray/releases) page:

```bash
sudo pacman -U llamatray-1.0.0-1-any.pkg.tar.zst

# Then launch from application menu or terminal:
LlamaTray
```

#### Manual Installation

```bash
# Clone the repository
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray

# (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m LlamaTray
```

#### Build from PKGBUILD

```bash
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray/arch-package
makepkg -si
```

### 📂 Repository Structure

```text
LlamaTray/
├── LlamaTray/                 # Main Python Package Directory
│   ├── __init__.py            # Package initializer
│   ├── __main__.py            # Entry point for `python -m LlamaTray`
│   ├── main.py                # Application entry point with crash handler
│   ├── ui.py                  # PyQt6 UI, system tray, profile management
│   ├── server.py              # Llama-server process manager (QProcess)
│   ├── monitor.py             # Hardware metric polling module
│   └── assets/                # App icons and graphics
│       ├── icon.png           # Default silver llama icon
│       └── green_icon.png     # Green llama icon (reserved)
├── arch-package/              # Arch Linux PKGBUILD and build artifacts
│   └── PKGBUILD               # Package build script for `llamatray`
├── requirements.txt           # Python dependencies
└── README.md                  # Multi-language documentation (this file)
```

### 🖱️ Usage

1. Launch LlamaTray from your application menu or terminal (`LlamaTray`).
2. Click **"Model Seç" (Browse)** to select a `.gguf` model file.
3. (Optional) Adjust advanced settings: GPU layers, context size, port, extra parameters.
4. **Profile Management:** Save your current configuration as a named profile for quick switching between different model setups.
5. Click **"Sunucuyu Başlat" (Start Server)** to launch `llama-server`.
6. Monitor CPU, RAM, GPU, VRAM usage in real-time.
7. Click **"Sunucuyu Durdur" (Stop Server)** or close the window to terminate — no zombie processes left behind.
8. Click **"Web Arayüzünü Aç"** to open the llama.cpp web UI in your browser.

> **Note:** Closing the window automatically terminates the llama-server process. The application also cleans up on crash via the built-in crash handler.

### ⚙️ Advanced Settings & Profiles

| Setting | Description | Default |
|---------|-------------|---------|
| GPU Layers | Number of layers to offload to GPU | 99 |
| Context Size | Context window size (512–1,000,000) | 32768 |
| Port | Server port (1024–65535) | 8080 |
| Extra Parameters | Additional llama-server flags | (optional) |

**Profiles** allow you to save named configurations and instantly restore them via the dropdown. Profiles are stored in `~/.llamatray/profiles.json`.

### 🧩 Dependencies

- **PyQt6** — GUI framework
- **psutil** — CPU/RAM monitoring
- **pynvml** — NVIDIA GPU monitoring (optional, falls back to nvidia-smi)
- **llama-server** — Part of [llama.cpp](https://github.com/ggerganov/llama.cpp)

### 🔗 Links

- **LlamaTray Page:** [fatihdurdu.xyz/llamatray](https://www.fatihdurdu.xyz/llamatray.html)
- **GitHub:** [github.com/DolbyDAX2/LlamaTray](https://github.com/DolbyDAX2/LlamaTray)
- **Gitea Mirror:** [gitea.fatihdurdu.xyz/dolbydax2/LlamaTray](https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray)

### 📄 License

This project is licensed under the MIT License.

---

## Türkçe

LlamaTray, Linux (özellikle Arch Linux / CachyOS) için geliştirilmiş, PyQt6 tabanlı hafif ve kararlı bir **Llama.cpp (llama-server)** yönetim aracıdır. Sistem tepsisine sorunsuz bir şekilde entegre olarak, yerel yapay zeka modellerinizi tek tıkla başlatmanıza, durdurmanıza ve izlemenize olanak tanır.

### ✨ Özellikler

- **Kolay Sunucu Yönetimi:** Yerel AI modellerinizi (`llama-server`) tek tıkla başlatın veya durdurun.
- **Zombi Süreç Koruması:** Pencere kapatıldığında (X butonu) veya tepsi ikonundan çıkıldığında, arka plandaki `llama-server` süreci otomatik olarak sonlandırılır, VRAM ve CPU temizlenir. Crash durumunda da temizlik yapan mekanizma.
- **Gerçek Zamanlı Kaynak İzleme:** CPU, RAM, GPU ve VRAM kullanımını görsel ilerleme çubuklarıyla anlık olarak takip edin (1 saniye aralıklı güncelleme).
- **Profil Yönetimi:** Farklı model yapılandırmaları için isimli profiller kaydedin, yükleyin ve silin. Ayarlar arasında hızlıca geçiş yapın.
- **Gelişmiş Yapılandırma:** GPU katmanları, context boyutu, port ve ek parametreleri sezgisel bir ayar panelinden özelleştirin.
- **Web UI Entegrasyonu:** Sunucu başladıktan sonra tek tıkla llama.cpp web arayüzünü varsayılan tarayıcınızda açın.
- **Kalıcı Ayarlar ve Profiller:** Tüm tercihler otomatik olarak `~/.llamatray/config.json` ve `~/.llamatray/profiles.json` dosyalarına kaydedilir ve bir sonraki açılışta geri yüklenir.
- **Yerel Linux Entegrasyonu:** Wayland ve KDE Plasma desteği ile masaüstü ortamınıza minimum ayak izi bırakır.
- **GPU Bağımsız:** NVIDIA (pynvml/nvidia-smi), AMD (rocm-smi/sysfs) ve tümleşik GPU'ları destekler.
- **Arch Linux Paketi:** Derlenmiş `.pkg.tar.zst` paketi `pacman -U` ile kolay kurulum imkanı.
- **Crash Handler:** Uygulama çökse bile tepsi ikonunu ve sunucu sürecini temizleyen özel hata yakalama mekanizması.

### 📦 Kurulum

#### Arch Linux (Önerilen)

En son `.pkg.tar.zst` dosyasını [Sürümler](https://github.com/DolbyDAX2/LlamaTray/releases) sayfasından indirin:

```bash
sudo pacman -U llamatray-1.0.0-1-any.pkg.tar.zst

# Ardından uygulama menüsünden veya terminalden çalıştırın:
LlamaTray
```

#### Manuel Kurulum

```bash
# Depoyu klonlayın
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray

# (İsteğe bağlı) Sanal ortam oluşturun ve etkinleştirin
python -m venv venv
source venv/bin/activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Uygulamayı çalıştırın
python -m LlamaTray
```

#### PKGBUILD ile Derleme

```bash
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray/arch-package
makepkg -si
```

### 📂 Depo Yapısı

```text
LlamaTray/
├── LlamaTray/                 # Ana Python Paket Dizini
│   ├── __init__.py            # Paket başlatıcı
│   ├── __main__.py            # `python -m LlamaTray` giriş noktası
│   ├── main.py                # Crash handler ile uygulama giriş noktası
│   ├── ui.py                  # PyQt6 arayüzü, sistem tepsisi, profil yönetimi
│   ├── server.py              # Llama-server süreç yöneticisi (QProcess)
│   ├── monitor.py             # Donanım metrik toplama modülü
│   └── assets/                # Uygulama ikonları ve grafikleri
│       ├── icon.png           # Varsayılan gümüş lama ikonu
│       └── green_icon.png     # Yeşil lama ikonu (yedek)
├── arch-package/              # Arch Linux PKGBUILD ve derleme çıktıları
│   └── PKGBUILD               # `llamatray` paketi için derleme betiği
├── requirements.txt           # Python bağımlılıkları
└── README.md                  # Çok dilli dokümantasyon (bu dosya)
```

### 🖱️ Kullanım

1. LlamaTray'i uygulama menünüzden veya terminalden başlatın (`LlamaTray`).
2. **"Model Seç"** butonuna tıklayarak bir `.gguf` model dosyası seçin.
3. (İsteğe bağlı) Gelişmiş ayarları yapılandırın: GPU katmanları, context boyutu, port, ek parametreler.
4. **Profil Yönetimi:** Mevcut yapılandırmanızı isimli bir profil olarak kaydedin, farklı model kurulumları arasında hızlı geçiş yapın.
5. **"Sunucuyu Başlat"** butonuna tıklayarak `llama-server`'ı başlatın.
6. CPU, RAM, GPU, VRAM kullanımını gerçek zamanlı olarak izleyin.
7. **"Sunucuyu Durdur"** butonuna tıklayarak veya pencereyi kapatarak sunucuyu sonlandırın — arka planda zombi süreç kalmaz.
8. **"Web Arayüzünü Aç"** butonu ile llama.cpp web arayüzünü tarayıcınızda açın.

> **Not:** Pencere kapatıldığında llama-server süreci otomatik olarak sonlandırılır. Crash handler sayesinde uygulama çökse bile temizlik yapılır.

### ⚙️ Gelişmiş Ayarlar ve Profiller

| Ayar | Açıklama | Varsayılan |
|------|----------|------------|
| GPU Katmanları | GPU'ya yüklenecek katman sayısı | 99 |
| Context Boyutu | Context penceresi boyutu (512–1.000.000) | 32768 |
| Port | Sunucu portu (1024–65535) | 8080 |
| Ek Parametreler | Ek llama-server flag'leri | (isteğe bağlı) |

**Profiller** sayesinde farklı yapılandırmaları isimlendirip kaydedebilir, açılır menüden anında yükleyebilirsiniz. Profiller `~/.llamatray/profiles.json` dosyasında saklanır.

### 🧩 Bağımlılıklar

- **PyQt6** — GUI framework
- **psutil** — CPU/RAM izleme
- **pynvml** — NVIDIA GPU izleme (isteğe bağlı, nvidia-smi'ye düşer)
- **llama-server** — [llama.cpp](https://github.com/ggerganov/llama.cpp) parçası

### 🔗 Bağlantılar

- **LlamaTray Sayfası:** [fatihdurdu.xyz/llamatray](https://www.fatihdurdu.xyz/llamatray.html)
- **GitHub:** [github.com/DolbyDAX2/LlamaTray](https://github.com/DolbyDAX2/LlamaTray)
- **Gitea Mirror:** [gitea.fatihdurdu.xyz/dolbydax2/LlamaTray](https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray)

### 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır.