import subprocess
import sys
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QLineEdit

def ask_admin_password(T, parent=None, log=None):
    if log:
        log(f"{T['information_log']} {T['displaying_password_prompt']}")

    max_tries = 3
    for attempt in range(max_tries):
        text, ok = QInputDialog.getText(
            parent,
            T['admin_password_title'],
            T['admin_password_text'],
            QLineEdit.EchoMode.Password
        )
        if not ok or not text:
            QMessageBox.critical(parent, T['error'], T['admin_password_required'])
            sys.exit(1)

        try:
            proc = subprocess.run(
                ["sudo", "-S", "whoami"],
                input=text + "\n",
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0 and "root" in proc.stdout:
                return text
            else:
                QMessageBox.warning(parent, T['invalid_password_title'], T['invalid_password_text'])
        except Exception as e:
            QMessageBox.critical(parent, T['error'], T['admin_password_error'].format(error=e))
            sys.exit(1)

    QMessageBox.critical(parent, T['error'], T['admin_password_max_tries'])
    sys.exit(1)
