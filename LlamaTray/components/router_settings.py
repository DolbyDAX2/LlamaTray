"""Router modu ayarları ve aktif model yönetimi bileşeni."""

import os

import requests
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)


class RouterApiWorker(QThread):
    """Router HTTP çağrılarını arayüzü kilitlemeden çalıştırır."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, base_url, action="list", model_id="", parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.action = action
        self.model_id = model_id

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            if self.action == "list":
                response = requests.get(f"{self.base_url}/models", timeout=4)
                response.raise_for_status()
                if not self.isInterruptionRequested():
                    self.completed.emit(response.json())
                return

            payload = {"model": self.model_id}
            endpoints = [f"/models/{self.action}", "/slots"]
            if self.action == "unload":
                payload["action"] = "unload"
            last_error = None
            for endpoint in endpoints:
                if self.isInterruptionRequested():
                    return
                try:
                    response = requests.post(f"{self.base_url}{endpoint}", json=payload, timeout=10)
                    if self.isInterruptionRequested():
                        return
                    if response.ok:
                        try:
                            result = response.json() if response.content else {}
                        except ValueError:
                            result = {"message": response.text}
                        self.completed.emit(result)
                        return
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                except requests.RequestException as exc:
                    last_error = str(exc)
            raise RuntimeError(last_error or "Router API request failed")
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))


class RouterSettingsWidget(QGroupBox):
    """Router seçeneklerini ve /models sonucunu gösterir."""

    def __init__(self, translations_func, port_func, log_func=None):
        super().__init__()
        self.translations_func = translations_func
        self.port_func = port_func
        self.log = log_func or (lambda _message: None)
        self._workers = set()
        self._server_active = False
        self._build_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.refresh_models)

    def tr(self, key, default=""):
        return self.translations_func(key, default)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        directory_row = QHBoxLayout()
        self.models_dir_label = QLabel()
        self.models_dir_lineedit = QLineEdit()
        self.models_dir_browse_button = QPushButton("📁")
        self.models_dir_browse_button.setFixedWidth(32)
        self.models_dir_browse_button.clicked.connect(self.browse_models_dir)
        directory_row.addWidget(self.models_dir_label)
        directory_row.addWidget(self.models_dir_lineedit, 1)
        directory_row.addWidget(self.models_dir_browse_button)
        layout.addLayout(directory_row)

        # Checkbox kullanıcı açısından pozitif anlam taşır. İşaretli olduğunda
        # modeller otomatik yüklenir ve --no-models-autoload eklenmez.
        self.no_autoload_checkbox = QCheckBox()
        self.no_autoload_checkbox.setChecked(False)
        self.jinja_checkbox = QCheckBox()
        self.jinja_checkbox.setChecked(True)
        layout.addWidget(self.no_autoload_checkbox)
        layout.addWidget(self.jinja_checkbox)

        title_row = QHBoxLayout()
        self.active_models_label = QLabel()
        self.refresh_button = QPushButton()
        self.refresh_button.clicked.connect(self.refresh_models)
        title_row.addWidget(self.active_models_label)
        title_row.addStretch()
        title_row.addWidget(self.refresh_button)
        layout.addLayout(title_row)

        self.models_tree = QTreeWidget()
        self.models_tree.setRootIsDecorated(False)
        self.models_tree.setMinimumHeight(130)
        self.models_tree.setUniformRowHeights(True)
        self._apply_column_modes()
        layout.addWidget(self.models_tree)
        # Durum etiketi (örn. "1 Model Bulundu") tablonun altındaki KENDİ
        # QHBoxLayout'ında tutulur; hücre içi item widget'larından ayrılır ve
        # böylece metin tablo içeriklerinin üstüne binmez.
        self.status_label = QLabel()
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)
        self.models_tree.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.update_labels()

    def _apply_column_modes(self):
        """Dinamik sütun yeniden boyutlandırma: düşük çözünürlüklerde sütunlar
        içeriğe göre uzayıp daralar, hücreler üst üste binmez.
        setHeaderLabels() modları sıfırladığı için update_labels'tan da çağrılır."""
        header = self.models_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)             # Model adı
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)    # Durum
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)             # İşlemler

    def browse_models_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr("router_select_models_dir", "Model klasörünü seç"),
            self.models_dir_lineedit.text() or os.path.expanduser("~"))
        if path:
            self.models_dir_lineedit.setText(path)

    def start_polling(self):
        self._server_active = True
        self.models_tree.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.refresh_models()
        self.refresh_timer.start()

    def stop_polling(self):
        self._server_active = False
        self.refresh_timer.stop()
        self.models_tree.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.status_label.clear()
        for worker in tuple(self._workers):
            if worker.isRunning():
                worker.requestInterruption()

    def _start_worker(self, action="list", model_id=""):
        if not self._server_active:
            return
        worker = RouterApiWorker(
            f"http://127.0.0.1:{self.port_func()}", action, model_id, self)
        self._workers.add(worker)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        if action == "list":
            worker.completed.connect(self._populate_models)
        else:
            worker.completed.connect(lambda _result: self._operation_complete(action, model_id))
        worker.failed.connect(self._api_failed)
        worker.start()

    def refresh_models(self):
        if not self._server_active:
            return
        if any(worker.isRunning() and worker.action == "list" for worker in self._workers):
            return
        self.status_label.setText(self.tr("router_loading_models", "Modeller yükleniyor..."))
        self._start_worker()

    def _extract_models(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "models", "items"):
                if isinstance(payload.get(key), list):
                    return payload[key]
        return []

    def _populate_models(self, payload):
        if not self._server_active:
            return
        self.models_tree.clear()
        models = self._extract_models(payload)
        for model in models:
            if isinstance(model, str):
                model_id = model
                status = self.tr("router_status_unknown", "Unknown")
            else:
                model_id = str(model.get("id") or model.get("model") or model.get("name") or "")
                status_data = model.get("status", model)
                if isinstance(status_data, dict):
                    status_value = status_data.get("value", "unknown")
                else:
                    status_value = status_data or "unknown"
                status_key = str(status_value).lower()
                status = self.tr(
                    f"router_status_{status_key}",
                    {"loaded": "Loaded", "unloaded": "Unloaded"}.get(status_key, "Unknown"))
            if not model_id:
                continue
            item = QTreeWidgetItem([model_id, status, ""])
            self.models_tree.addTopLevelItem(item)
            actions = QHBoxLayout()
            actions.setContentsMargins(0, 0, 0, 0)
            load_button = QPushButton(self.tr("router_load", "Yükle"))
            unload_button = QPushButton(self.tr("router_unload", "Boşalt"))
            load_button.clicked.connect(lambda _checked=False, mid=model_id: self._start_worker("load", mid))
            unload_button.clicked.connect(lambda _checked=False, mid=model_id: self._start_worker("unload", mid))
            actions.addWidget(load_button)
            actions.addWidget(unload_button)
            container = QWidget()
            container.setLayout(actions)
            self.models_tree.setItemWidget(item, 2, container)
        self.status_label.setText(
            self.tr("router_models_count", "{count} model bulundu.").format(count=len(models)))

    def _operation_complete(self, action, model_id):
        if not self._server_active:
            return
        key = "router_load_success" if action == "load" else "router_unload_success"
        fallback = "Model yüklendi: {model}" if action == "load" else "Model boşaltıldı: {model}"
        self.log(self.tr(key, fallback).format(model=model_id))
        QTimer.singleShot(500, self.refresh_models)

    def _api_failed(self, error):
        if not self._server_active:
            return
        message = self.tr("router_api_error", "Router API hatası: {error}").format(error=error)
        self.status_label.setText(message)
        self.log(f"⚠ {message}")

    def update_labels(self):
        self.setTitle(self.tr("router_group_title", "Router Ayarları"))
        self.models_dir_label.setText(self.tr("router_models_dir", "Model Klasörü:"))
        self.models_dir_lineedit.setPlaceholderText(
            self.tr("router_models_dir_placeholder", "Örn: /home/kullanici/modeller"))
        self.no_autoload_checkbox.setText(
            self.tr("router_no_autoload", "Modelleri otomatik yükle"))
        self.jinja_checkbox.setText(self.tr("router_jinja", "Jinja şablonlarını etkinleştir"))
        self.active_models_label.setText(self.tr("router_active_models", "Aktif Modeller"))
        self.refresh_button.setText(self.tr("router_refresh", "Yenile"))
        self.models_tree.setHeaderLabels([
            self.tr("router_model", "Model"), self.tr("router_status", "Durum"),
            self.tr("router_actions", "İşlemler")])
        # setHeaderLabels() sütun yeniden boyutlandırma modlarını sıfırlar; tekrar uygula.
        self._apply_column_modes()
