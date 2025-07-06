#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QLocale

fallback_texts = {
    "en": {
        "title": "NetMountManager Installer",
        "log_label": "Installation log:",
        "finished": "Installation finished.",
        "close": "Close",
        "install_pip_start": "📦 Installing required Python packages...",
        "install_pip_done": "✅ Python packages installed.",
        "install_desktop_start": "📁 Creating desktop entry...",
        "install_desktop_done": "✅ Desktop entry created at:\n{}",
        "desktop_entry_name": "NetMount Manager",
        "desktop_entry_comment": "Manage network mounts (SMB, FTP, SFTP)",
        "install_error": "❌ Error: {}"
    },
    "hu": {
        "title": "NetMountManager Telepítő",
        "log_label": "Telepítési napló:",
        "finished": "Telepítés befejezve.",
        "close": "Bezárás",
        "install_pip_start": "📦 Python csomagok telepítése...",
        "install_pip_done": "✅ Python csomagok telepítve.",
        "install_desktop_start": "📁 Asztali parancsikon létrehozása...",
        "install_desktop_done": "✅ Parancsikon létrehozva itt:\n{}",
        "desktop_entry_name": "NetMount Kezelő",
        "desktop_entry_comment": "Hálózati csatolások kezelése (SMB, FTP, SFTP)",
        "install_error": "❌ Hiba történt: {}"
    }
}

LANG = QLocale.system().name().split("_")[0]
T = fallback_texts.get(LANG, fallback_texts["en"])

class InstallerWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.T = T
        self.setWindowTitle(T["title"])
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        self.text_area = QTextEdit(readOnly=True)
        self.text_area.append(T["log_label"])
        layout.addWidget(self.text_area)

        self.close_button = QPushButton("❌ " + T["close"])
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_button)
        layout.addLayout(btn_layout)

        self.run_installation()

    def log(self, msg):
        self.text_area.append(msg)
        QApplication.processEvents()

    def run_installation(self):
        try:
            self.log(self.T["install_pip_start"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pyqt6", "cryptography"])
            self.log(self.T["install_pip_done"])

            self.log(self.T["install_desktop_start"])
            desktop_path = Path.home() / ".local/share/applications/netmountmanager.desktop"
            desktop_path.parent.mkdir(parents=True, exist_ok=True)

            exec_path = Path.home() / "NetMountManager" / "netmount" / "main.py"
            icon_path = Path.home() / "NetMountManager" / "icons" / "netmount_icon.png"

            desktop_entry = f"""[Desktop Entry]
Name={self.T['desktop_entry_name']}
Comment={self.T['desktop_entry_comment']}
Exec=python3 {exec_path}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Network;Utility;
StartupNotify=true

"""

            with open(desktop_path, "w") as f:
                f.write(desktop_entry)

            self.log(self.T["install_desktop_done"].format(desktop_path))
            self.log(f"🟢 {T['finished']}")
        except Exception as e:
            self.log(self.T["install_error"].format(e))
        finally:
            self.close_button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
