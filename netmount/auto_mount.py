#!/usr/bin/env python3
import os, sys, time, json, socket, subprocess, urllib.parse
from pathlib import Path

# 📦 Projektgyökér hozzáadása a sys.path-hoz
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMessageBox, QInputDialog, QLineEdit, QDialog,
    QTextEdit, QVBoxLayout, QLabel
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QLocale

from netmount.config import (
    SECURE_FILE, XBEL_FILE, BOOKMARK_NS, icon_path, lang_file_am
)
from netmount.utils.xml_utils import prettify
from netmount.bookmarks import add_place, clean_mount_bookmarks
from netmount.password_prompt import ask_admin_password
from netmount.decryptor import decrypt, encrypt

app = QApplication(sys.argv)
app.setWindowIcon(QIcon(str(icon_path)))
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
    with open(lang_file_am, "r", encoding="utf-8") as f:
        LANGS = json.load(f)
except Exception as e:
    err = fallback_error_msgs.get(LANG, fallback_error_msgs["en"])
    QMessageBox.critical(
        None, err["title"],
        err["text"].format(path=lang_file_am, error=e)
    )
    sys.exit(1)

T = LANGS.get(LANG, LANGS["en"])

class ProgressDialog(QDialog):
    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.text_area = QTextEdit(readOnly=True)
        layout.addWidget(QLabel(T.get("log_label", "Progress log:")))
        layout.addWidget(self.text_area)

    def log(self, message):
        self.text_area.append(message)
        QApplication.processEvents()

progress_dialog = ProgressDialog(T["title"])
progress_dialog.show()

def log(msg):
    print(msg)
    progress_dialog.log(msg)

def mount_with_password(mount_point, path, options, password):
    try:
        proc = subprocess.run(
            ["sudo", "-S", "mount", "-t", "cifs", mount_point, path, "-o", options],
            input=password + '\n',
            text=True, capture_output=True
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)
        add_place(os.path.basename(path), path, icon="network-server", category="mounts")
        log(f"[OK] {T['smb_mount_ok']} {path}")
        return True
    except Exception as e:
        log(f"[ERROR] {T['smb_mount_fail']} {e}")
        return False

def is_ip_reachable(ip, port=445, timeout=2):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def auto_mount():
    time.sleep(5)

    uid = os.getuid()
    gid = os.getgid()
    prev_was_con = False
    admin_password = ask_admin_password(T)

    if not os.path.exists(SECURE_FILE):
        log(T["no_config_file"])
        return

    try:
        mounts = decrypt(admin_password)
    except Exception as e:
        log(T["decryption_failed"].format(error=e))
        return

    for m in mounts:
        if not m.get('automount'):
            continue

        path = m['path']
        url = m['url']
        user = m.get('user', '')
        stored_password = m.get('password', '')
        smb_version = m.get('smb_version', '').strip()

        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            log(T["create_path_failed"].format(path=path, error=e))
            continue

        try:
            if url.startswith("sftp://"):
                if prev_was_con: time.sleep(1)

                remote = url[7:]
                host_part = remote.split('/', 1)[0]
                remote_path = '/' + remote.split('/', 1)[1] if '/' in remote else ''
                host, port = host_part.split(':') if ':' in host_part else (host_part, '22')

                key_path = os.path.expanduser(f"~/.ssh/netmount_keys/id_rsa_{host}_{port}")
                if not os.path.exists(key_path):
                    log(f"[SKIP] {T['no_key']} {key_path}")
                    continue

                try:
                    subprocess.run([
                        "sshfs", f"{user}@{host}:{remote_path}", path,
                        "-p", port,
                        "-o", f"IdentityFile={key_path},uid={uid},gid={gid},StrictHostKeyChecking=no"
                    ], check=True)
                    add_place(os.path.basename(path), path, icon="network-server", category="mounts")
                    log(f"[OK] {T['sftp_mount_ok']} {path}")
                except Exception as e:
                    log(f"[ERROR] {T['sftp_mount_fail']} {e}")
                prev_was_con = True

            elif url.startswith("ftp://"):
                if prev_was_con: time.sleep(1)
                remote = url[7:]
                host_part = remote.split('/', 1)[0]
                remote_path = '/' + remote.split('/', 1)[1] if '/' in remote else ''
                host, port = host_part.split(':') if ':' in host_part else (host_part, '21')

                try:
                    subprocess.run([
                        "curlftpfs", host, path, "-o",
                        f"user={user}:{stored_password},uid={uid},gid={gid},ftp_port={port}"
                    ], check=True)
                    add_place(os.path.basename(path), path, icon="network-server", category="mounts")
                    log(f"[OK] {T['ftp_mount_ok']} {path}")
                except Exception as e:
                    log(f"[ERROR] {T['ftp_mount_fail']} {e}")
                prev_was_con = False

            elif url.startswith("smb://"):
                if prev_was_con: time.sleep(1)
                if not os.path.exists(path):
                    log(f"[SKIP] {T['no_dir']} {path}")
                    continue

                options = f"username={user},password={stored_password},uid={uid},gid={gid}"
                if smb_version:
                    options += f",vers={smb_version}"

                mount_point = url[6:]
                if not mount_point.startswith("//"):
                    mount_point = f"//{mount_point}"

                smb_host = mount_point.split('/')[2]
                if not is_ip_reachable(smb_host):
                    log(f"[SKIP] {T['smb_unreachable']} {smb_host}")
                    continue

                if mount_with_password(mount_point, path, options, admin_password):
                    prev_was_con = True
                else:
                    log(T["password_invalid_final"])
                    return

        except subprocess.CalledProcessError as e:
            log(T["generic_mount_fail"].format(url=url, path=path, error=e))

    clean_mount_bookmarks()
    time.sleep(8)
    progress_dialog.close()

def main():
    auto_mount()

if __name__ == "__main__":
    main()
