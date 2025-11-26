#!/usr/bin/env python3
import sys
import os
import traceback
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
    traceback.print_exc()
    sys.exit(1)

def show_fatal_trace(title: str, short_text: str, trace_text: str):
    print("=== FATAL ===", file=sys.stderr)
    print(title, file=sys.stderr)
    print(short_text, file=sys.stderr)
    print(trace_text, file=sys.stderr)

    try:
        dlg = QMessageBox()
        dlg.setIcon(QMessageBox.Critical)
        dlg.setWindowTitle(title)
        dlg.setText(short_text)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.setDetailedText(trace_text)
        dlg.exec()
    except Exception:
        traceback.print_exception(Exception, Exception(short_text), None, file=sys.stderr)

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))

    def _global_excepthook(exctype, value, tb):
        try:
            tb_text = ''.join(traceback.format_exception(exctype, value, tb))
            title = T.get('fatal_error_title_1', 'Fatal error')
            short = T.get('fatal_error_text_1', 'Unexpected error. See details.')

            msg1 = T.get('console_unhandled_exception', 'Unhandled exception (global hook):')
            print(msg1, file=sys.stderr)
            traceback.print_exception(exctype, value, tb, file=sys.stderr)

            show_fatal_trace(title, short, tb_text)
        except Exception:
            traceback.print_exception(exctype, value, tb, file=sys.stderr)

    sys.excepthook = _global_excepthook

    try:
        admin_pw = os.environ.get("NETMOUNT_PW") or ask_admin_password(T_PW)

        loading = LoadingDialog(T)
        loading.show()
        QApplication.processEvents()

        def after_load():
            try:
                window = MountManager(T, admin_pw)

                app._main_window = window

                try:
                    window.refresh_with_loading(external_dialog=loading)
                except Exception:
                    raise

                loading.close()
                window.show()

                msg2 = T.get('console_app_started', 'Application started and main window shown.')
                print(msg2, file=sys.stderr)

            except Exception:
                tb = traceback.format_exc()
                title = T.get('fatal_error_title_0', 'Fatal error during startup')
                short = T.get('fatal_error_text_0', 'An unexpected error occurred while starting the application. See details.')
                try:
                    loading.close()
                except Exception:
                    pass
                show_fatal_trace(title, short, tb)
                sys.exit(1)

        QTimer.singleShot(100, after_load)
        sys.exit(app.exec())

    except Exception:
        tb = traceback.format_exc()
        title = T.get('fatal_error_title_1', 'Fatal error')
        short = T.get('fatal_error_text_1', 'Unexpected error. See details.')
        show_fatal_trace(title, short, tb)
        sys.exit(1)

if __name__ == "__main__":
    main()
