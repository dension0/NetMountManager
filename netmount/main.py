#!/usr/bin/env python3
import sys
import sys
import os
import traceback
import subprocess
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

import json
from PyQt6.QtWidgets import QApplication, QMessageBox, QInputDialog, QLineEdit
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QLocale, QTimer

from netmount.config import icon_path, lang_file, lang_file_pw
from netmount.mountmanager import MountManager
from netmount.mountmanager import LoadingDialog

from netmount.password_prompt import ask_admin_password

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
    with open(lang_file, "r", encoding="utf-8") as f:
        LANGS = json.load(f)
    T = LANGS.get(LANG, LANGS['en'])

    with open(lang_file_pw, "r", encoding="utf-8") as f:
        PW_LANGS = json.load(f)
    T_PW = PW_LANGS.get(LANG, PW_LANGS['en'])
except Exception as e:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))
    err = fallback_error_msgs.get(LANG, fallback_error_msgs["en"])
    QMessageBox.critical(
        None,
        err["title"],
        err["text"].format(path=lang_file, error=e)
    )
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))

    try:
        admin_pw = os.environ.get("NETMOUNT_PW") or ask_admin_password(T_PW)

        loading = LoadingDialog(T)
        loading.show()
        QApplication.processEvents()

        def after_load():
            window = MountManager(T, admin_pw)
            window.refresh_with_loading(external_dialog=loading)
            loading.close()
            window.show()

        QTimer.singleShot(100, after_load)
        sys.exit(app.exec())

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    main()
