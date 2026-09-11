# 🦙 LlamaTray

[English](#english) | [Türkçe](#türkçe)

---

## English

LlamaTray is a lightweight and stable PyQt6-based **Llama.cpp (llama-server)** management utility designed for Linux. Seamlessly integrating into the system tray, it allows you to start, stop, and monitor local AI models with a single click while real-time tracking system resources.

### ✨ Features

- **Tabbed Interface:** Main, Settings, and Profiles tabs keep server controls, configuration, and profile management organized.
- **Single Model & Router Modes:** Run one GGUF directly or launch llama-server as a model router over an entire models directory.
- **Router Model Management:** View model states through `GET /models` and load or unload models from the application.
- **Fast HuggingFace Downloader:** Search GGUF repositories, retrieve file names and exact sizes through the HuggingFace Tree API, and download models without leaving LlamaTray.
- **Effortless Server Management:** Spin up or shut down your local AI models (`llama-server`) with a single click from the GUI.
- **Real-Time Resource Monitoring:** Track CPU, RAM, GPU, and VRAM utilization instantly via clean visual progress bars (1-second refresh interval).
- **Persistent Profiles & Settings:** Save, load, update, and delete named model configurations. Profiles and application preferences are restored automatically between sessions.
- **Advanced Configuration:** Customize GPU layers, context size, port, and extra parameters through an intuitive settings panel.
- **Web UI Integration:** One-click button to open the llama.cpp web interface in your default browser after server starts.
- **Native Linux Integration:** Native Wayland and KDE Plasma support ensuring a minimal footprint on your desktop ecosystem.
- **NVIDIA & AMD Monitoring:** GPU and VRAM metrics are collected through NVIDIA (NVML/nvidia-smi) and AMD (rocm-smi/sysfs) monitoring interfaces when available.
- **AUR Package:** Available on the Arch User Repository (AUR) for easy installation.
- **mmproj Support:** Attach a multimodal projector to compatible vision-language models through `--mmproj`.
- **Command Preview:** Real-time launch command preview showing the exact `llama-server` command before starting.

### 🆕 What's New in v1.5.0

- Cross-platform installation fixes for Ubuntu (GNOME/XFCE/MATE) and Fedora (Wayland/X11): the installer now adds `~/.local/bin` to your PATH using shell-native syntax (bash/zsh/fish aware, with config-file scanning fallback), installs missing Qt6/XCB runtime libraries on Apt-based systems, and registers the app icon and `.desktop` entry (`StartupWMClass=LlamaTray`, hicolor 256x256 icon, `gtk-update-icon-cache`).
- Proper GNOME/Wayland dock/taskbar icon grouping via `app.setDesktopFileName("llamatray.desktop")`.
- Graceful system-tray fallback: if no tray protocol (StatusNotifier D-Bus) is available on modern GNOME/Wayland sessions, LlamaTray keeps running in window mode without unhandled exceptions.
- New **"Minimize to Tray on Close"** setting: the close button hides the window into the system tray while the server keeps running. The tray menu gains a Quit action, and single/double-clicking the tray icon restores the window.
- Responsive UI: Main and Settings tabs are now `QScrollArea`-based, the dynamic minimum window size supports 1024x768 screens, and the Router "Active Models" table uses dynamic column resizing with its status label in a dedicated row so it never overlaps table items.

### 🆕 What's New in v1.4.0

- Three-tab Main / Settings / Profiles interface with collapsible settings sections.
- Router mode with models directory, auto-load, Jinja, model state, and load/unload controls.
- Context size and GPU layer settings for both Single Model and Router modes.
- HuggingFace Downloader integration with Router mode: the models directory is preselected and the model list refreshes after downloading.
- Much faster HuggingFace file listing while preserving exact GGUF file sizes.
- Turkish and English localization for all new controls and model states.

### 📦 Installation

#### Arch Linux

Install from the AUR using your favorite AUR helper:

```bash
# Using yay:
yay -S llamatray

# Or using paru:
paru -S llamatray

# Then launch from application menu or terminal:
LlamaTray
```

#### Ubuntu / Debian

```bash
# Clone the repository
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray

# Run the installation script (creates venv, installs deps, sets up launcher)
chmod +x install.sh
./install.sh

# Launch from application menu or terminal:
llamatray
```

The installer automatically detects your distribution and installs required system packages (`python3-venv`, `python3-pip`). It creates a virtual environment, installs Python dependencies, generates a launcher script at `~/.local/bin/llamatray`, and registers a `.desktop` file for your application menu. On Apt-based systems it also installs missing Qt6/XCB runtime libraries (for minimal X11 desktops such as XFCE/MATE), registers the application icon into `~/.local/share/icons/hicolor`, and adds `~/.local/bin` to your shell's PATH using shell-native syntax (bash/zsh/fish aware).

#### Fedora

```bash
# Clone the repository
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray

# Run the installation script
chmod +x install.sh
./install.sh

# Launch from application menu or terminal:
llamatray
```

The installer automatically detects Fedora and installs `python3` via `dnf` if needed.

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

### 📂 Repository Structure

```text
LlamaTray/
├── .gitignore                 # Git ignore rules
├── README.md                  # Multi-language documentation (this file)
├── install.sh                 # Automated installer (Ubuntu/Debian/Fedora/Arch)
├── requirements.txt           # Python dependencies
└── LlamaTray/                 # Main Python Package Directory
    ├── __init__.py            # Package initializer
    ├── __main__.py            # Entry point for `python -m LlamaTray`
    ├── main.py                # Application entry point
    ├── ui.py                  # PyQt6 UI, system tray integration
    ├── server.py              # Llama-server process manager (QProcess)
    ├── monitor.py             # Hardware metric polling module (CPU/RAM/GPU/VRAM)
    ├── translations.json      # Localization translations (TR/EN)
    ├── ui_utils.py            # UI helper utilities (cleanup, translation loader)
    ├── assets/                # App icons and graphics
    │   └── icon.png           # Default llama icon
    └── components/            # UI Components Directory
        ├── __init__.py        # Components package initializer
        ├── about_dialog.py    # About/credits dialog with language support
        ├── advanced_settings.py  # Advanced settings panel
        ├── command_preview.py # Live llama-server command preview
        ├── hf_downloader.py   # HuggingFace search and downloader dialog
        ├── model_selector.py  # Single-model selection controls
        ├── monitor_widget.py  # Real-time resource monitor widget
        ├── profile_manager.py # Profile save/load/delete manager
        ├── router_settings.py # Router options and model API controls
        └── server_controls.py # Start, stop, and Web UI controls
```

### 🖱️ Usage

#### Single Model Mode

1. Launch LlamaTray and keep **Single Model** selected under the Settings tab.
2. On the Main tab, select a local `.gguf` file or use **Download from HF**.
3. Configure GPU layers, context size, port, sampler preset, optional mmproj, and extra parameters.
4. Review the generated command and click **Start Server**.

#### Router Mode

1. Select **Router Mode** under the Settings tab.
2. Choose the directory containing your GGUF files.
3. Configure **Auto-load models**, **Jinja**, GPU layers, context size, port, and optional extra parameters.
4. Start the server. The active model list is refreshed automatically.
5. Use **Load** and **Unload** beside each model. Model states show Loaded, Unloaded, Loading, or Unknown.
6. **Download from HF** remains available and defaults to the configured models directory.

In either mode, use **Open Web UI** to open llama.cpp in your browser. Click **Stop Server** or close LlamaTray to terminate the server cleanly.

> **Note:** Router mode requires a llama-server build that supports `--models-dir` and the model router API. Closing the window automatically terminates the server.

### ⚙️ Advanced Settings & Profiles

| Setting | Description | Default |
|---------|-------------|---------|
| GPU Layers | Number of layers to offload to GPU | 99 |
| Context Size | Context window size (512–1,000,000) | 32768 |
| Port | Server port (1024–65535) | 8080 |
| Sampler Preset | Ready-to-use neutral, balanced, creative, and precise sampling settings | Custom |
| Extra Parameters | Additional llama-server flags | (optional) |
| mmproj File | Multimodal projector file used in Single Model mode | (optional) |

Router mode additionally provides:

| Setting | Description | Default |
|---------|-------------|---------|
| Models Directory | Directory containing the GGUF models exposed by the router | (required) |
| Auto-load Models | Automatically load router models when required | Disabled |
| Jinja | Enable Jinja chat templates | Enabled |

**Profiles** support both Single Model and Router configurations. Named profiles are stored in `~/.llamatray/profiles.json`; application settings are stored in `~/.llamatray/config.json`.

### 🧩 Dependencies

- **PyQt6** — GUI framework
- **psutil** — CPU/RAM monitoring
- **nvidia-ml-py** — NVIDIA GPU monitoring (optional, falls back to pynvml or nvidia-smi)
- **requests** — HuggingFace and llama-server Router API communication
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

- **Sekmeli Arayüz:** Ana, Ayarlar ve Profiller sekmeleri sunucu kontrollerini, yapılandırmayı ve profil yönetimini düzenli tutar.
- **Tek Model ve Router Modları:** Tek bir GGUF dosyasını doğrudan çalıştırın veya bir model klasörünü llama-server router olarak sunun.
- **Router Model Yönetimi:** `GET /models` üzerinden model durumlarını görüntüleyin ve modelleri uygulama içinden yükleyip boşaltın.
- **Hızlı HuggingFace İndirici:** GGUF depolarını arayın, dosya adlarıyla gerçek boyutlarını HuggingFace Tree API üzerinden hızla alın ve modelleri LlamaTray'den ayrılmadan indirin.
- **Kolay Sunucu Yönetimi:** Yerel AI modellerinizi (`llama-server`) tek tıkla başlatın veya durdurun.
- **Gerçek Zamanlı Kaynak İzleme:** CPU, RAM, GPU ve VRAM kullanımını görsel ilerleme çubuklarıyla anlık olarak takip edin (1 saniye aralıklı güncelleme).
- **Kalıcı Profiller ve Ayarlar:** İsimli model yapılandırmalarını kaydedin, yükleyin, güncelleyin ve silin. Profiller ile uygulama tercihleri oturumlar arasında otomatik olarak geri yüklenir.
- **Gelişmiş Yapılandırma:** GPU katmanları, context boyutu, port ve ek parametreleri sezgisel bir ayar panelinden özelleştirin.
- **Web UI Entegrasyonu:** Sunucu başladıktan sonra tek tıkla llama.cpp web arayüzünü varsayılan tarayıcınızda açın.
- **Yerel Linux Entegrasyonu:** Wayland ve KDE Plasma desteği ile masaüstü ortamınıza minimum ayak izi bırakır.
- **NVIDIA ve AMD İzleme:** GPU ve VRAM metrikleri, mevcut olduğunda NVIDIA (NVML/nvidia-smi) ve AMD (rocm-smi/sysfs) izleme arayüzlerinden alınır.
- **AUR Paketi:** Arch User Repository (AUR) üzerinden kolay kurulum imkanı.
- **mmproj Desteği:** Uyumlu görsel-dil modellerine `--mmproj` ile çok modlu projektör bağlayın.
- **Komut Önizlemesi:** Sunucu başlatılmadan önce tam `llama-server` komutunu gösteren gerçek zamanlı önizleme.

### 🆕 v1.5.0 Yenilikleri

- Ubuntu (GNOME/XFCE/MATE) ve Fedora (Wayland/X11) için çapraz platform kurulum düzeltmeleri: kurulum betiği artık `~/.local/bin` yolunu kabuğunuza özgü sözdizimiyle PATH'e ekler (bash/zsh/fish destekli, yapılandırma dosyası tarama yedeği ile), Apt tabanlı sistemlerde eksik Qt6/XCB çalışma zamanı kütüphanelerini kurar ve uygulama simgesini + `.desktop` girişini (`StartupWMClass=LlamaTray`, hicolor 256x256 simge, `gtk-update-icon-cache`) kaydeder.
- `app.setDesktopFileName("llamatray.desktop")` ile GNOME/Wayland dock/görev çubuğu ikon gruplaması.
- Zarif sistem tepsisi yedeği: modern GNOME/Wayland oturumlarında tray protokolü (StatusNotifier D-Bus) yoksa LlamaTray ele alınmamış istisna fırlatmaksızın pencere modunda çalışmaya devam eder.
- Yeni **"Kapatırken Tepside Minimize Et"** ayarı: kapatma butonu pencereyi sistem tepisine gizler, sunucu çalışmaya devam eder. Tepsi menüsüne Çıkış eylemi eklendi; tepsinin tek/tıklanması pencereyi geri açar.
- Duyarlı arayüz: Ana ve Ayarlar sekmeleri artık `QScrollArea` tabanlı, dinamik minimum pencere boyutu 1024x768 ekranları destekler ve Router "Aktif Modeller" tablosu dinamik sütun yeniden boyutlandırma kullanır; durum etiketi kendi satırında olduğu için tablo öğeleriyle üst üste binmez.

### 🆕 v1.4.0 Yenilikleri

- Daraltılabilir ayar bölümlerine sahip üç sekmeli Ana / Ayarlar / Profiller arayüzü.
- Model klasörü, otomatik yükleme, Jinja, model durumu ve yükle/boşalt kontrollerine sahip Router modu.
- Tek Model ve Router modlarında Context Boyutu ve GPU Katmanları desteği.
- HF Downloader ile Router entegrasyonu: model klasörü otomatik seçilir ve indirme sonrasında model listesi yenilenir.
- GGUF dosyalarının gerçek boyutlarını koruyan çok daha hızlı HuggingFace dosya listeleme.
- Tüm yeni kontroller ve model durumları için Türkçe/İngilizce yerelleştirme.

### 📦 Kurulum

#### Arch Linux

AUR üzerinden kurulum yapın:

```bash
# yay kullanarak:
yay -S llamatray

# veya paru kullanarak:
paru -S llamatray

# Ardından uygulama menüsünden veya terminalden başlatın:
LlamaTray
```

#### Ubuntu / Debian

```bash
# Depoyu klonlayın
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray

# Kurulum betiğini çalıştırın (venv oluşturur, bağımlılıkları yükler, başlatıcı oluşturur)
chmod +x install.sh
./install.sh

# Uygulama menüsünden veya terminalden başlatın:
llamatray
```

Kurulum betiği dağıtımınızı otomatik olarak tespit eder ve gerekli sistem paketlerini (`python3-venv`, `python3-pip`) yükler. Sanal ortam oluşturur, Python bağımlılıklarını kurar, `~/.local/bin/llamatray` başlatma betiğini oluşturur ve uygulama menünüz için `.desktop` dosyası kaydeder. Apt tabanlı sistemlerde ayrıca eksik Qt6/XCB çalışma zamanı kütüphanelerini (XFCE/MATE gibi minimal X11 masaüstleri için) kurar, uygulama simgesini `~/.local/share/icons/hicolor` altına kaydeder ve `~/.local/bin` yolunu kabuğunuza özgü sözdizimiyle PATH'e ekler (bash/zsh/fish destekli).

#### Fedora

```bash
# Depoyu klonlayın
git clone https://github.com/DolbyDAX2/LlamaTray.git
cd LlamaTray

# Kurulum betiğini çalıştırın
chmod +x install.sh
./install.sh

# Uygulama menüsünden veya terminalden başlatın:
llamatray
```

Kurulum betiği Fedora'yı otomatik olarak tespit eder ve gerekirse `dnf` ile `python3` kurulumunu yapar.

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

### 📂 Depo Yapısı

```text
LlamaTray/
├── .gitignore                 # Git ignore kuralları
├── README.md                  # Çok dilli dokümantasyon (bu dosya)
├── install.sh                 # Otomatik kurulum betiği (Ubuntu/Debian/Fedora/Arch)
├── requirements.txt           # Python bağımlılıkları
└── LlamaTray/                 # Ana Python Paket Dizini
    ├── __init__.py            # Paket başlatıcı
    ├── __main__.py            # `python -m LlamaTray` giriş noktası
    ├── main.py                # Uygulama giriş noktası
    ├── ui.py                  # PyQt6 arayüzü, sistem tepsisi entegrasyonu
    ├── server.py              # Llama-server süreç yöneticisi (QProcess)
    ├── monitor.py             # Donanım metrik toplama modülü (CPU/RAM/GPU/VRAM)
    ├── translations.json      # Yerelleştirme çevirileri (TR/EN)
    ├── ui_utils.py            # UI yardımcı araçları (temizlik, çeviri yükleyici)
    ├── assets/                # Uygulama ikonları ve grafikleri
    │   └── icon.png           # Varsayılan lama ikonu
    └── components/            # UI Bileşenleri Dizini
        ├── __init__.py        # Bileşenler paket başlatıcı
        ├── about_dialog.py    # Hakkında/kredi diyalog penceresi (dil desteği ile)
        ├── advanced_settings.py  # Gelişmiş ayarlar paneli
        ├── command_preview.py # Canlı llama-server komut önizlemesi
        ├── hf_downloader.py   # HuggingFace arama ve indirme penceresi
        ├── model_selector.py  # Tek model seçim kontrolleri
        ├── monitor_widget.py  # Gerçek zamanlı kaynak izleme bileşeni
        ├── profile_manager.py # Profil kaydet/yükle/sil yöneticisi
        ├── router_settings.py # Router ayarları ve model API kontrolleri
        └── server_controls.py # Başlatma, durdurma ve Web UI kontrolleri
```

### 🖱️ Kullanım

#### Tek Model Modu

1. LlamaTray'i başlatın ve Ayarlar sekmesinde **Tek Model** seçeneğini açık bırakın.
2. Ana sekmede yerel bir `.gguf` dosyası seçin veya **HF'den İndir** seçeneğini kullanın.
3. GPU katmanları, context boyutu, port, sampler preset, isteğe bağlı mmproj ve ek parametreleri yapılandırın.
4. Oluşturulan komutu kontrol edip **Sunucuyu Başlat** butonuna tıklayın.

#### Router Modu

1. Ayarlar sekmesinden **Router Modu** seçeneğini seçin.
2. GGUF dosyalarınızın bulunduğu model klasörünü belirleyin.
3. **Modelleri otomatik yükle**, **Jinja**, GPU katmanları, context boyutu, port ve isteğe bağlı ek parametreleri yapılandırın.
4. Sunucuyu başlatın. Aktif model listesi otomatik olarak yenilenir.
5. Her modelin yanındaki **Yükle** ve **Boşalt** butonlarını kullanın. Durum sütununda Yüklü, Boşta, Yükleniyor veya Bilinmiyor gösterilir.
6. **HF'den İndir** kullanılabilir kalır ve indirme klasörü olarak yapılandırılmış model klasörünü otomatik seçer.

Her iki modda da **Web Arayüzünü Aç** ile llama.cpp arayüzünü tarayıcıda açabilirsiniz. **Sunucuyu Durdur** butonu veya pencereyi kapatmak sunucuyu temiz şekilde sonlandırır.

> **Not:** Router modu, `--models-dir` ve model router API desteğine sahip bir llama-server derlemesi gerektirir. Pencere kapatıldığında sunucu otomatik olarak sonlandırılır.

### ⚙️ Gelişmiş Ayarlar ve Profiller

| Ayar | Açıklama | Varsayılan |
|------|----------|------------|
| GPU Katmanları | GPU'ya yüklenecek katman sayısı | 99 |
| Context Boyutu | Context penceresi boyutu (512–1.000.000) | 32768 |
| Port | Sunucu portu (1024–65535) | 8080 |
| Sampler Preset | Nötr, dengeli, yaratıcı ve kesin hazır örnekleme ayarları | Özel |
| Ek Parametreler | Ek llama-server flag'leri | (isteğe bağlı) |
| mmproj Dosyası | Tek Model modunda kullanılan çok modlu projektör dosyası | (isteğe bağlı) |

Router modu ayrıca şu ayarları sunar:

| Ayar | Açıklama | Varsayılan |
|------|----------|------------|
| Model Klasörü | Router tarafından sunulacak GGUF modellerinin bulunduğu klasör | (zorunlu) |
| Modelleri Otomatik Yükle | Gerektiğinde router modellerini otomatik yükler | Kapalı |
| Jinja | Jinja sohbet şablonlarını etkinleştirir | Açık |

**Profiller** hem Tek Model hem de Router yapılandırmalarını destekler. İsimli profiller `~/.llamatray/profiles.json`, uygulama ayarları ise `~/.llamatray/config.json` dosyasında saklanır.

### 🧩 Bağımlılıklar

- **PyQt6** — GUI framework
- **psutil** — CPU/RAM izleme
- **nvidia-ml-py** — NVIDIA GPU izleme (isteğe bağlı, pynvml veya nvidia-smi'ye düşer)
- **requests** — HuggingFace ve llama-server Router API iletişimi
- **llama-server** — [llama.cpp](https://github.com/ggerganov/llama.cpp) parçası

### 🔗 Bağlantılar

- **LlamaTray Sayfası:** [fatihdurdu.xyz/llamatray](https://www.fatihdurdu.xyz/llamatray.html)
- **GitHub:** [github.com/DolbyDAX2/LlamaTray](https://github.com/DolbyDAX2/LlamaTray)
- **Gitea Mirror:** [gitea.fatihdurdu.xyz/dolbydax2/LlamaTray](https://gitea.fatihdurdu.xyz/dolbydax2/LlamaTray)

### 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır.