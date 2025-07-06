#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QTextEdit, QVBoxLayout, QLabel, QMessageBox, QPushButton, QHBoxLayout
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QLocale

DESKTOP_FILE = Path.home() / ".local/share/applications/netmountmanager.desktop"
AUTOMOUNT_FILE = Path.home() / ".config/autostart/net-automounts.desktop"
SMBUNMOUNT_SCRIPT = Path.home() / ".config/systemd/user/smb-unmount.service"
LANG = QLocale.system().name().split('_')[0]
ICON_FILE = Path.home() / "NetMountManager" / "icons" / "netmount_icon.png"

fallback_texts = {
    "en": {
        "title": "NetMountManager Uninstaller",
        "log_label": "Uninstallation log:",
        "desktop_removed": "🗑️ Desktop entry removed.",
        "desktop_not_found": "⚠️ Desktop entry not found.",
        "autostart_removed": "🗑️ Autostart entry removed.",
        "autostart_not_found": "⚠️ Autostart entry not found.",
        "systemd_disabled": "🗑️ smb-unmount.service disabled and removed.",
        "systemd_not_found": "⚠️ smb-unmount.service not found.",
        "systemd_error": "❌ Failed to disable service:\n{}",
        "done": "✅ Uninstallation complete.",
        "error": "Error",
        "close": "Close"
    },
    "hu": {
        "title": "NetMountManager Eltávolító",
        "log_label": "Eltávolítási napló:",
        "desktop_removed": "🗑️ Indítóikon törölve.",
        "desktop_not_found": "⚠️ Indítóikon nem található.",
        "autostart_removed": "🗑️ Automatikus csatoló ikon törölve.",
        "autostart_not_found": "⚠️ Automatikus csatoló ikon nem található.",
        "systemd_disabled": "🗑️ smb-unmount.service leállítva és törölve.",
        "systemd_not_found": "⚠️ smb-unmount.service nem található.",
        "systemd_error": "❌ A szolgáltatás leállítása sikertelen:\n{}",
        "done": "✅ Eltávolítás befejezve.",
        "error": "Hiba",
        "close": "Bezárás"
    }
}

T = fallback_texts.get(LANG, fallback_texts["en"])

class UninstallDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T["title"])
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(T["log_label"]))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.close_btn = QPushButton("❌ " + T["close"])
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def log(self, message):
        self.output.append(message)
        QApplication.processEvents()

    def run_uninstall(self):
        # desktop entry törlése
        if DESKTOP_FILE.exists():
            DESKTOP_FILE.unlink()
            self.log(T["desktop_removed"])
        else:
            self.log(T["desktop_not_found"])

        # autostart törlés
        if AUTOMOUNT_FILE.exists():
            AUTOMOUNT_FILE.unlink()
            self.log(T["autostart_removed"])
        else:
            self.log(T["autostart_not_found"])

        # systemd user service kikapcsolás + törlés
        if SMBUNMOUNT_SCRIPT.exists():
            try:
                subprocess.run(["systemctl", "--user", "disable", "--now", "smb-unmount.service"], check=True)
                SMBUNMOUNT_SCRIPT.unlink()
                subprocess.run(["systemctl", "--user", "daemon-reexec"], check=True)
                self.log(T["systemd_disabled"])
            except Exception as e:
                self.log(T["systemd_error"].format(str(e)))
        else:
            self.log(T["systemd_not_found"])

        self.log("")
        self.log(T["done"])
        self.close_btn.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    if ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(ICON_FILE)))

    dialog = UninstallDialog()
    dialog.show()
    dialog.run_uninstall()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
