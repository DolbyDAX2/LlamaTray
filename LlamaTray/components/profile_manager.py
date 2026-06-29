"""
Profil Yönetimi Bileşeni.
Kayıtlı profilleri listeleme, kaydetme, güncelleme ve silme işlevlerini içerir.
"""

import os
import json
from PyQt6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QComboBox,
                              QPushButton, QMessageBox, QInputDialog)


class ProfileManagerWidget(QGroupBox):
    """Profil yönetimi grubu - profilleri kaydet, güncelle ve sil"""

    def __init__(self, translations_func=None, callbacks=None):
        """
        Args:
            translations_func: Çeviri fonksiyonu (get_translated metodu)
            callbacks: {
                'log': log fonksiyonu,
                'get_form_values': form değerlerini dict olarak döndüren fonksiyon,
                'apply_profile_values': profil verisini forma uygulayan fonksiyon,
                'get_profiles_path': profiles.json yolunu döndüren fonksiyon,
                'save_profiles': profilleri JSON'a yazan fonksiyon,
                'load_profiles: profilleri JSON'dan yükleyen fonksiyon,
                'window': ana pencere referansı (diyalog parent'ı için),
            }
        """
        super().__init__()
        self.translations_func = translations_func
        self.callbacks = callbacks or {}
        self._init_ui()

    def _init_ui(self):
        self.setTitle(self.get_translated("profile_group_title", "Profil Yönetimi"))
        layout = QVBoxLayout()
        profile_select_layout = QHBoxLayout()
        self.profile_combobox = QComboBox()
        self.profile_combobox.setMinimumHeight(28)
        profile_select_layout.addWidget(self.profile_combobox, 1)
        self.save_profile_button = QPushButton(self.get_translated("button_save_profile", "💾 Profili Kaydet"))
        self.save_profile_button.setFixedHeight(28)
        self.update_profile_button = QPushButton(self.get_translated("button_update_profile", "🔄 Profili Güncelle"))
        self.update_profile_button.setFixedHeight(28)
        self.delete_profile_button = QPushButton(self.get_translated("button_delete_profile", "🗑️ Profili Sil"))
        self.delete_profile_button.setFixedHeight(28)
        profile_buttons_layout = QHBoxLayout()
        profile_buttons_layout.addWidget(self.save_profile_button)
        profile_buttons_layout.addWidget(self.update_profile_button)
        profile_buttons_layout.addWidget(self.delete_profile_button)
        layout.addLayout(profile_select_layout)
        layout.addLayout(profile_buttons_layout)
        self.setLayout(layout)

    def get_translated(self, key, default=""):
        if self.translations_func:
            return self.translations_func(key, default)
        return default

    def _log(self, msg):
        log_fn = self.callbacks.get('log')
        if log_fn:
            log_fn(msg)

    def _load_profiles(self):
        fn = self.callbacks.get('load_profiles')
        if fn: return fn()
        pp = self.callbacks.get('get_profiles_path', lambda: "")
        if os.path.exists(pp):
            try:
                with open(pp, "r", encoding="utf-8") as f: return json.load(f)
            except Exception as e: self._log(f"⚠ Profiller yüklenemedi: {e}")
        return {}

    def _save_profiles(self, profiles):
        fn = self.callbacks.get('save_profiles')
        if fn: return fn(profiles)
        pp = self.callbacks.get('get_profiles_path', lambda: "")
        try:
            with open(pp, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
        except Exception as e: self._log(f"❌ Profiller kaydedilemedi: {e}")

    def refresh_combobox(self):
        """Combobox'ı kayıtlı profillerle doldur"""
        current_name = self.profile_combobox.currentText()
        self.profile_combobox.blockSignals(True)
        self.profile_combobox.clear()
        profiles = self._load_profiles()
        if profiles:
            self.profile_combobox.addItems(sorted(profiles.keys()))
            idx = self.profile_combobox.findText(current_name)
            if idx >= 0: self.profile_combobox.setCurrentIndex(idx)
        else:
            self.profile_combobox.addItem(self.get_translated("no_profile", "(Profil yok)"))
        self.profile_combobox.blockSignals(False)

    def save_profile(self):
        """Mevcut form değerlerini bir profile kaydet"""
        name, ok = QInputDialog.getText(
            self.callbacks.get('window'),
            self.get_translated("dialog_save_profile_title", "Profili Kaydet"),
            self.get_translated("dialog_save_profile_prompt", "Profil adı:"))
        if not ok or not name or not name.strip(): return
        name = name.strip()
        if not name:
            self._log(self.get_translated("log_profile_name_empty", "⚠ Profil adı boş olamaz.")); return
        fn = self.callbacks.get('get_form_values')
        if fn: values = fn()
        else: values = {}
        values["profile_name"] = name
        profiles = self._load_profiles()
        is_upd = name in profiles
        profiles[name] = values
        self._save_profiles(profiles)
        self.refresh_combobox()
        idx = self.profile_combobox.findText(name)
        if idx >= 0: self.profile_combobox.setCurrentIndex(idx)
        self._log(self.get_translated("log_profile_updated" if is_upd else "log_profile_saved",
               "✓ Profil güncellendi/kaydedildi: '{profile_name}'").format(profile_name=name))

    def load_profile(self, index):
        """Combobox'tan profil seçildiğinde form alanlarını doldur"""
        if index < 0: return
        pn = self.profile_combobox.currentText()
        if not pn or pn == self.get_translated("no_profile", "(Profil yok)"): return
        profiles = self._load_profiles()
        pd = profiles.get(pn)
        if pd:
            fn = self.callbacks.get('apply_profile_values')
            if fn: fn(pd)
            self._log(self.get_translated("log_profile_loaded", "✓ Profil yüklendi: '{profile_name}'").format(profile_name=pn))

    def update_profile(self):
        """Seçili profili güncelle"""
        pn = self.profile_combobox.currentText()
        if not pn or pn == self.get_translated("no_profile", "(Profil yok)"):
            self._log(self.get_translated("log_no_profile_to_update", "⚠ Güncellenecek profil seçilmedi.")); return
        fn = self.callbacks.get('get_form_values')
        values = fn() if fn else {}
        profiles = self._load_profiles()
        if pn in profiles:
            profiles[pn] = values; self._save_profiles(profiles)
            self._log(self.get_translated("dialog_update_profile_success", "✓ Profil '{profile_name}' güncellendi.").format(profile_name=pn))
        else:
            self._log(self.get_translated("dialog_update_profile_not_found", "⚠ Profil '{profile_name}' bulunamadı.").format(profile_name=pn))

    def delete_profile(self):
        """Seçili profili sil"""
        pn = self.profile_combobox.currentText()
        if not pn or pn == self.get_translated("no_profile", "(Profil yok)"):
            self._log(self.get_translated("log_no_profile_to_delete", "⚠ Silinecek profil seçilmedi.")); return
        reply = QMessageBox.question(
            self.callbacks.get('window'),
            self.get_translated("dialog_delete_profile_title", "Profili Sil"),
            self.get_translated("dialog_delete_profile_prompt", "'{profile_name}' profilini silmek istediğinize emin misiniz?").format(profile_name=pn),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        profiles = self._load_profiles()
        if pn in profiles:
            del profiles[pn]; self._save_profiles(profiles); self.refresh_combobox()
            self._log(self.get_translated("log_profile_deleted", "✓ Profil silindi: '{profile_name}'").format(profile_name=pn))

    def update_labels(self):
        """Çeviri etiketlerini güncelle"""
        self.setTitle(self.get_translated("profile_group_title", "Profil Yönetimi"))
        self.save_profile_button.setText(self.get_translated("button_save_profile", "💾 Profili Kaydet"))
        self.update_profile_button.setText(self.get_translated("button_update_profile", "🔄 Profili Güncelle"))
        self.delete_profile_button.setText(self.get_translated("button_delete_profile", "🗑️ Profili Sil"))
