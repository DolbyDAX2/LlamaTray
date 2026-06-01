# 🦙 LlamaTray - Kod Analiz Raporu

**Tarih:** 29.05.2026  
**Analiz Edilen:** Tüm Python kaynak dosyaları, konfigürasyon dosyaları, PKGBUILD  
**Not:** Hiçbir kod değişikliği yapılmamıştır, sadece analizdir.

---

## 🔴 KRİTİK HATALAR

### HATA 1: `ui_utils.cleanup_tray_icon()` çalışmıyor
**Dosya:** `LlamaTray/ui_utils.py` (satır 37-68)  
**Risk:** YÜKSEK

`cleanup_tray_icon()` fonksiyonu `_tray_instance.hide()` çağrısı yapıyor.  
`_tray_instance`, `sys.modules['LlamaTray.ui']._tray_instance` üzerinden alınıyor ve bu değer bir `LlamaTray` nesnesi (instance'ı).  
**Sorun:** `LlamaTray` sınıfının `hide()` metodunun kendisi yok. `tray_icon` attribute'u var (`self.tray_icon`), ama direkt olarak `hide()` metodu tanımlanmamış.  
**Sonuç:** `_tray_instance.hide()` çağrısı `AttributeError` fırlatır, try-except ile sessizce yutulur. Yani bu fonksiyon hiçbir zaman gerçek temizlik yapmaz. Crash handler (`main.py`) ve `atexit` ile kaydedilen temizlik işlevi boştur.

> **Alternatif görüş:** Python'da `getattr` ile fallback mümkün değil, `LlamaTray` sınıfında `hide()` metodu yok. `QSystemTrayIcon`'un `hide()` metodunu çağırmak için `_tray_instance.tray_icon.hide()` yapılması gerekirdi.

---

### HATA 2: `cleanup_on_exit()` de çalışmıyor
**Dosya:** `LlamaTray/ui_utils.py` (satır 71-86)  
**Risk:** YÜKSEK

`cleanup_on_exit()` fonksiyonu `ui_utils._tray_instance` global'ını kullanır (satır 75).  
`ui_utils._tray_instance` hiçbir yerde set edilmez (None olarak kalır).  
`_tray_instance` sadece `ui.py`'de (`LlamaTray.__init__` içinde satır 43) `ui._tray_instance = self` ile atanır, ama `ui_utils._tray_instance` asla atanmaz.  
**Sonuç:** `cleanup_on_exit()` her çağrıldığında `_tray_instance is None` olduğu için hiçbir şey yapmadan geri döner.

> İki farklı modülde aynı isimde iki ayrı global değişken var: `ui._tray_instance` (dolu) ve `ui_utils._tray_instance` (None).

---

### HATA 3: `log_model_load_error` çeviri anahtarı yanlış kullanılıyor
**Dosyalar:** `LlamaTray/ui.py` (satır 627), `LlamaTray/translations.json`  
**Risk:** YÜKSEK

`ui.py` satır 627:
```python
self.log(self.get_translated("log_model_load_error", "✓ Model yolu yüklendi: {path}").format(path=self.model_path))
```

`translations.json`'da `log_model_load_error` şöyle tanımlanmış:
```json
"log_model_load_error": "⚠ GPU katmanları değeri geçersiz, varsayılan kullanılıyor"
```

**Sonuç:** Kullanıcı model yolu yüklendiğinde "⚠ GPU katmanları değeri geçersiz..." gibi yanıltıcı bir mesaj görür. Çeviri anahtarı doğru değil, yeni bir anahtar (ör. `log_model_path_loaded`) gerekli.

---

### HATA 4: `server.cleanup_server_process()` kendi PID'ini ikinci kez öldürüyor
**Dosya:** `LlamaTray/server.py` (satır 302-308)  
**Risk:** ORTA

```python
finally:
    self.server_running = False
    pid = self.processId()
    if pid > 0:
        os.kill(pid, signal.SIGKILL)
```

Daha önce satır 287-294'te süreç `terminate()` ve ardından `kill()` ile zaten sonlandırılıyor. `finally` bloğunda aynı PID'e tekrar `SIGKILL` göndermek gereksiz. Eğer süreç zaten ölmüşse `os.kill` `ESRCH` hatası fırlatır (try-except ile yakalanıyor ama log'a yazılıyor).

---

### HATA 5: `cleanup_old_processes()` tüm sistemdeki `llama-server`'ları öldürüyor
**Dosya:** `LlamaTray/server.py` (satır 31)  
**Risk:** ORTA

```python
subprocess.run(["killall", "-9", "llama-server"], ...)
```

Kullanıcının aynı anda birden fazla llama-server çalıştırma ihtimaline karşı çok agresif. Sadece kendi başlattığı süreci temizlemeliydi.

---

## 🟡 ORTA ÖNEMLİ HATALAR

### HATA 6: Versiyon numarası 4 farklı yerde tutarsız

| Yer | Değer |
|-----|-------|
| `LlamaTray/ui.py` satır 198 | `v1.0.2` |
| `LlamaTray/ui.py` satır 322 | `v1.1.1` |
| `LlamaTray/translations.json` | `v1.1.0` |
| `arch-package/PKGBUILD` | `1.1.1` |
| `README.md`'deki örnekler | `1.0.0` |

Aynı dosya içinde bile (`ui.py`) iki farklı versiyon var: biri window title'da, biri `apply_translations`'da.

---

### HATA 7: `_init_main_window` içinde gereksiz import
**Dosya:** `LlamaTray/ui.py` (satır 126)

```python
def _init_main_window(self):
    from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFrame, QLabel, QProgressBar
```

Bu import modül seviyesinde değil, metot içinde yapılmış. Modülün tepesinde `from PyQt6.QtWidgets import ...` ile zaten birçok widget import edilmiş ama `QMainWindow`, `QWidget` gibi temel sınıflar atlanmış. Ya hepsi modül seviyesine taşınmalı ya da metot içindeki import kaldırılmalı.

---

### HATA 8: `about_dialog.py` translations.json'u her `_build_html_content` çağrısında yeniden okuyor
**Dosya:** `LlamaTray/components/about_dialog.py` (satır 90-97)

Her dil değişiminde dosyayı diskten tekrar okumak performans kaybı. `translations_func` parametresi ile gelen fonksiyon (ana uygulamadan) kullanılabilirdi.

---

### HATA 9: `profile_manager.py`'de kendi `load_profiles`/`save_profiles` metodları tanımlanmış
**Dosya:** `LlamaTray/components/profile_manager.py` (satır 62-86)

`ui.py`'de de aynı işlevi gören `load_profiles`/`save_profiles` metodları var (satır 348-366). Kod tekrarı. Bir değişiklik yapıldığında iki yerin de güncellenmesi gerekir.

---

## 🔵 DÜŞÜK ÖNEMLİ SORUNLAR

### SORUN 10: `base_widget.py` ölü kod
**Dosya:** `LlamaTray/components/base_widget.py` (tüm dosya)

`ResourceMonitorBase` sınıfı tanımlanmış ama:
- `components/__init__.py`'den export edilmiyor
- Hiçbir yerde kullanılmıyor
- `monitor_widget.py`'deki `SystemMonitorWidget` neredeyse aynı kodu elle tekrar yazıyor

---

### SORUN 11: `main_window.py` tamamen ölü kod
**Dosya:** `LlamaTray/components/main_window.py` (tüm dosya, 211 satır)

`LlamaTrayMainWindow` ve `LlamaTraySystemTray` sınıfları tanımlanmış ama:
- `components/__init__.py`'den export edilmiyor
- `ui.py`'de kullanılmıyor
- `ui.py` tüm UI'yi kendi içinde sıfırdan kuruyor (kod tekrarı)

Bu dosyadaki tüm widget tanımları (`cpu_label`, `cpu_progress`, butonlar vs.) `ui.py`'de de var.

---

### SORUN 12: `green_icon.png` iki farklı konumda
- `LlamaTray/green_icon.png`
- `LlamaTray/assets/green_icon.png`

Aynı dosyanın iki kopyası. `icon.png` için de durum aynı:
- `LlamaTray/icon.png`
- `LlamaTray/assets/icon.png`

---

### SORUN 13: `PKGBUILD` wrapper script `python -m LlamaTray.main` kullanıyor
**Dosya:** `arch-package/PKGBUILD` (satır 40)

```bash
python -m LlamaTray.main "$@"
```

`-m` flag'i bir modül adı bekler (`LlamaTray`), `LlamaTray.main` değil. `python -m LlamaTray.main` çalışabilir (çünkü `__main__.py`'i değil `main.py`'i direkt çalıştırır) ama standart değil. Doğrusu: `python -m LlamaTray` veya `python -c "from LlamaTray.main import main; main()"`.

---

### SORUN 14: `__init__.py`'de import edilenler `__all__` ile uyumlu
**Dosya:** `LlamaTray/__init__.py`

Bu bir hata değil, tutarlı. Sadece belirtmek istedim: `__init__.py`'de `cleanup_tray_icon` ve `cleanup_on_exit` import edilmiş, `__all__`'da da listelenmiş. ✅

---

### SORUN 15: `requirements.txt`'de `llama-server` binary'si yok
Bu beklenen bir durum (manuel kurulum), ama README'de belirtilmiş olsa da `requirements.txt`'nin yanında ayrıca `llama.cpp` kurulum talimatı olabilir.

---

## 🟣 TUTARSIZLIKLAR

### TUTARSIZLIK A: İki farklı `_tray_instance` global'i

| Modül | Değişken | Değer |
|-------|----------|-------|
| `ui_utils.py` | `_tray_instance` | `None` (hiç set edilmez) |
| `ui.py` | `_tray_instance` | `self` (`LlamaTray` instance'ı) |

`cleanup_tray_icon()` `sys.modules['LlamaTray.ui']._tray_instance` ile `ui.py`'dekinden alır, `cleanup_on_exit()` ise `ui_utils._tray_instance`'ı kullanır (None). İkisi farklı şeylere bakar.

---

### TUTARSIZLIK B: Birden fazla cleanup mekanizması

1. `main.py` → `atexit.register(cleanup_tray_icon)`
2. `main.py` → `app.aboutToQuit.connect(cleanup_tray_icon)`
3. `ui.py` → `app.aboutToQuit.connect(self.cleanup_tray)`
4. `ui.py` → `atexit.register(cleanup_on_exit)`
5. `ui.py` → `window_close_event` içinde `self.cleanup_tray()`

Bazıları aynı şeyi yapmaya çalışıyor, bazıları çalışmıyor (HATA 1 ve HATA 2). Çok karışık bir yapı.

---

### TUTARSIZLIK C: `about_dialog.py`'de dil hard-coded

```python
self.current_language = "tr"  # satır 26
```

Ana uygulamadan dil bilgisi alınmıyor. `translations_func` parametre olarak geliyor ama dil state'i ayrı tutuluyor.

---

## ✅ ÇALIŞAN / SORUNSUZ KISIMLAR

- **`main.py`**: Crash handler ve temel akış doğru tasarlanmış.
- **`server.py`**: `start_server` parametre validasyonu, port kontrolü, `QProcess` yönetimi genel olarak iyi.
- **`monitor.py`**: GPU tespiti için birden çok yöntem (pynvml, nvidia-smi, rocm-smi, sysfs) denenmesi iyi.
- **`ui.py`**'deki `LlamaTray` sınıfı: Profil yönetimi, config kaydetme/yükleme, dil desteği mantığı doğru.
- **`translations.json`**: Kapsamlı çeviri dosyası.
- **`PKGBUILD`**: Genel yapı doğru, sadece wrapper script'te küçük bir düzeltme gerekli.

---

## ÖZET

| Kategori | Sayı |
|----------|------|
| 🔴 Kritik Hata | 5 |
| 🟡 Orta Önemli Hata | 4 |
| 🔵 Düşük Önemli Sorun | 5 |
| 🟣 Tutarsızlık | 3 |
| **Toplam** | **17** |

En kritik bulgular:
1. `cleanup_tray_icon()` ve `cleanup_on_exit()` fonksiyonları çalışmıyor (ölü kod)
2. `log_model_load_error` çeviri anahtarı yanlış kullanılıyor (kullanıcıya yanlış mesaj)
3. `main_window.py` ve `base_widget.py` tamamen ölü kod (211 + 112 = 323 satır gereksiz kod)
4. Versiyon numaraları 4 farklı yerde tutarsız
5. İki farklı `_tray_instance` global'i kafa karışıklığı yaratıyor