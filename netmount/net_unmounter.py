#!/usr/bin/env python3
import os, sys, json, socket, subprocess, time, signal
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QMessageBox, QLineEdit,
    QTextEdit, QDialog, QVBoxLayout, QLabel, QSystemTrayIcon, QPushButton
)
from PyQt6.QtGui import QIcon, QAction, QCursor
from PyQt6.QtCore import QTimer, QLocale
import xml.etree.ElementTree as ET

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from netmount.config import XBEL_FILE, BOOKMARK_NS, SECURE_FILE, icon_path, lang_file_un
from netmount.bookmarks import clean_mount_bookmarks
from netmount.password_prompt import ask_admin_password
from netmount.decryptor import decrypt

def create_signal_handler(T_local):
    def handler(sig, frame):
        print(T_local.get("daemon_stopped"))
        sys.exit(0)
    return handler

LANG = QLocale.system().name().split('_')[0]

fallback_error_msgs = {
    "en": {
        "title": "❌ Language File Error - Network Mount Manager",
        "text": "Failed to load language file:\n{path}\n\nError:\n{error}"
    },
    "hu": {
        "title": "❌ Nyelvi fájl hiba - Hálózati csatolókezelő",
        "text": "Nem sikerült betölteni a nyelvi fájlt:\n{path}\n\nHiba:\n{error}"
    }
}

try:
    with open(lang_file_un, "r", encoding="utf-8") as f:
        LANGS = json.load(f)
    T = LANGS.get(LANG, LANGS['en'])
except Exception as e:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))
    err = fallback_error_msgs.get(LANG, fallback_error_msgs["en"])
    QMessageBox.critical(None, err["title"], err["text"].format(path=lang_file_un, error=e))
    sys.exit(1)

signal.signal(signal.SIGINT, create_signal_handler(T))
signal.signal(signal.SIGTERM, create_signal_handler(T))

class UnmountManager:
    def __init__(self):
        self.log_window = None
        self.log_dialog = None
        self.setup_tray_icon()
        self.password = os.environ.get("NETMOUNT_PW")
        self.something_unmounted = False

    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(str(icon_path)))
        self.tray.setToolTip(T["tray_tooltip"])

        self.tray.activated.connect(self.on_tray_icon_activated)
        self.tray.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_log_window(from_tray=True)

    def log(self, message):
        print(f"[LOG] {message}")
        if self.log_window:
            self.log_window.append(message.strip())
            QApplication.processEvents()

    def is_host_reachable(self, host, port=445, timeout=2.0):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            self.log(T["host_unreachable"])
            return False

    def is_cifs_mount_zombi(self, path):
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    if path in line and "cifs" in line:
                        return True
        except Exception as e:
            self.log(f"{T['mount_read_error']} {e}")
        return False

    def unmount_with_password(self, path):
        self.log(T["unmount_attempt"].format(path=path))
        try:
            proc = subprocess.run(
                ['sudo', '-S', 'umount', path],
                input=self.password + '\n',
                text=True,
                capture_output=True
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr)
            self.log(T["unmount_success"].format(path=path))
            return True
        except Exception as e:
            QMessageBox.critical(None, T["unmount_failed_title"], T["unmount_failed_text"].format(error=e))
            return False

    def show_log_window(self, from_tray=False):
        if self.log_window and self.log_dialog:
            if not from_tray:
                self.log_dialog.close()
            else:
                return

        dialog = QDialog()

        if from_tray:
            dialog.setWindowTitle(T["log_title_log"])
        else:
            dialog.setWindowTitle(T["log_title"])

        layout = QVBoxLayout()

        if from_tray:
            layout.addWidget(QLabel(T["log_label_log"]))
        else:
            layout.addWidget(QLabel(T["log_label"]))

        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        layout.addWidget(self.log_window)

        if from_tray:
            exit_button = QPushButton(T["smb_check_exit"])
            exit_button.clicked.connect(QApplication.quit)
            layout.addWidget(exit_button)

        dialog.setLayout(layout)
        dialog.resize(500, 400)

        def on_close(event):
            self.log_window = None
            self.log_dialog = None
            event.accept()

        dialog.closeEvent = on_close

        dialog.show()
        QApplication.processEvents()
        self.log_dialog = dialog

    def main_loop(self):
        if self.password is None:
            self.password = ask_admin_password(T, log=self.log)
            if not self.password:
                self.log(T["password_invalid_final"])
                return

        self.log(T["cycle_start"])

        try:
            mounts = decrypt(self.password)
        except Exception as e:
            self.log(T["decryption_failed"].format(error=e))
            return

        for mount in mounts:
            url = mount.get("url", "")
            path = mount.get("path", "")

            if not url.startswith("smb://") or not path:
                continue

            host = url[6:].split('/')[0].split(':')[0]
            self.log(T["checking"].format(host=host, path=path))

            if self.is_cifs_mount_zombi(path) and not self.is_host_reachable(host):
                self.show_log_window()
                time.sleep(1)
                self.log(T["unmount_required"].format(host=host))

                if self.unmount_with_password(path):
                    self.something_unmounted = True
                else:
                    self.log(T["password_invalid_final"])
                    return
            else:
                self.log(T["unmount_not_required"].format(host=host))

        if self.something_unmounted and self.log_dialog:
            clean_mount_bookmarks()
            time.sleep(5)
            self.log_dialog.close()
            time.sleep(1)
            self.log_window = None
            self.log_dialog = None

            QMessageBox.information(None, T["finished_title"], T["finished_text"])
            self.something_unmounted = False

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))
    manager = UnmountManager()

    timer = QTimer()
    timer.timeout.connect(manager.main_loop)
    timer.start(5000)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
