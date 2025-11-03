#!/usr/bin/env python3
import os, sys, time, json, socket, subprocess, urllib.parse, getpass
from pathlib import Path

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
    SECURE_FILE, XBEL_FILE, BOOKMARK_NS, SMBUNMOUNT_EXEC, icon_path, lang_file_am, lang_file_pw
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
    T = LANGS.get(LANG, LANGS["en"])

    with open(lang_file_pw, "r", encoding="utf-8") as f:
        PW_LANGS = json.load(f)
    T_PW = PW_LANGS.get(LANG, PW_LANGS['en'])
except Exception as e:
    err = fallback_error_msgs.get(LANG, fallback_error_msgs["en"])
    QMessageBox.critical(
        None, err["title"],
        err["text"].format(path=lang_file_am, error=e)
    )
    sys.exit(1)

def is_local_network_up() -> bool:
    try:
        result = subprocess.run(
            'ip -o addr show up | grep -v " lo " | grep -qE "inet(6)? "',
            shell=True
        )
        return result.returncode == 0
    except Exception:
        return False

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
        log(f"{T['error_log']} {T['smb_mount_fail']} {e}")
        return False

def is_ip_reachable(ip, port=445, timeout=2):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def launch_net_unmounter(admin_password: str):
    log(f"{T['mountguard_log']} {T['start_unmounter']}")
    env = os.environ.copy()
    env["NETMOUNT_PW"] = admin_password

    subprocess.Popen(
        ["python3", os.path.join(SMBUNMOUNT_EXEC)],
        env=env,
        start_new_session=True
    )

    if is_unmounter_running():
        log(f"{T['mountguard_log']} {T['started_unmounter']}")
    else:
        log(f"{T['mountguard_log']} {T['start_unmounter_failed']}")

def is_unmounter_running():
    try:
        user = getpass.getuser()
        for _ in range(3):
            result = subprocess.run(
                ["ps", "-u", user, "-o", "pid,cmd"],
                stdout=subprocess.PIPE,
                text=True
            )
            for line in result.stdout.splitlines():
                if "net_unmounter.py" in line and "python3" in line:
                    return True
            time.sleep(1)
        return False
    except Exception:
        return False

def is_mounted(path):
    return os.path.ismount(path)

def auto_mount():
    time.sleep(5)

    if not is_local_network_up():
        return

    uid = os.getuid()
    gid = os.getgid()
    prev_was_con = False
    admin_password = ask_admin_password(T_PW, log=log)

    if not os.path.exists(SECURE_FILE):
        log(f"{T['information_log']} {T['log(T["no_config_file']}")
        return

    try:
        mounts = decrypt(admin_password)
    except Exception as e:
        log(f"{T['error_log']} {T['log(T["decryption_failed'].format(error=e)}")
        return

    for m in mounts:
        if not m.get('automount'):
            continue

        path = m['path']
        url = m['url']
        user = m.get('user', '')
        stored_password = m.get('password', '')
        smb_version = m.get('smb_version', '').strip()

        if "last_known_status" not in m:
                m["last_known_status"] = "unknown"

        if is_mounted(path):
            log(f"{T['skip_log']} {T['already_mounted']} {path}")
            continue

        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            log(f"{T['error_log']} {T['create_path_failed'].format(path=path, error=e)}")
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
                    log(f"{T['skip_log']} {T['no_key']} {key_path}")
                    continue

                try:
                    subprocess.run([
                        "sshfs", f"{user}@{host}:{remote_path}", path,
                        "-p", port,
                        "-o", f"IdentityFile={key_path},uid={uid},gid={gid},StrictHostKeyChecking=no"
                    ], check=True)
                    add_place(os.path.basename(path), path, icon="network-server", category="mounts")
                    m["last_known_status"] = "mounted"
                    log(f"{T['ok_log']} {T['sftp_mount_ok']} {path}")
                except Exception as e:
                    log(f"{T['error_log']} {T['sftp_mount_fail']}: {e}")
                prev_was_con = True

            elif url.startswith("ftp://"):
                if prev_was_con: time.sleep(1)

                remote = url[7:]
                host_part = remote.split('/', 1)[0]
                remote_path = '/' + remote.split('/', 1)[1] if '/' in remote else ''
                host, port = host_part.split(':') if ':' in host_part else (host_part, '21')

                try:
                    result = subprocess.run([
                        "curlftpfs", host, path,
                        "-o", f"user={user}:{stored_password},uid={uid},gid={gid},ftp_port={port}"
                    ], capture_output=True, check=True, text=True)

                    add_place(os.path.basename(path), path, icon="network-server", category="mounts")
                    m["last_known_status"] = "mounted"
                    log(f"{T['ok_log']} {T['ftp_mount_ok']} {path}")

                except subprocess.CalledProcessError as e:
                    stderr = e.stderr.strip() if e.stderr else str(e)
                    if "530" in stderr or "Access denied" in stderr or "Permission denied" in stderr:
                        log(f"{T['error_log']} {T['ftp_auth_error']}: {stderr}")
                    else:
                        log(f"{T['error_log']} {T['ftp_mount_fail']}: {stderr}")
                prev_was_con = False

            elif url.startswith("smb://"):
                if prev_was_con: time.sleep(1)

                if not os.path.exists(path):
                    log(f"{T['skip_log']} {T['no_dir']} {path}")
                    continue

                options = f"username={user},password={stored_password},uid={uid},gid={gid}"
                if smb_version:
                    options += f",vers={smb_version}"

                mount_point = url[6:]
                if not mount_point.startswith("//"):
                    mount_point = f"//{mount_point}"

                smb_host = mount_point.split('/')[2]
                if not is_ip_reachable(smb_host):
                    log(f"{T['skip_log']} {T['smb_unreachable']} {smb_host}")
                    continue

                if mount_with_password(mount_point, path, options, admin_password):
                    m["last_known_status"] = "mounted"
                    log(f"{T['ok_log']} {T['smb_mount_ok']} {path}")
                    prev_was_con = True
                else:
                    log(f"{T['error_log']} {T['password_invalid_final']}")
                    return

        except Exception as e:
            log(f"{T['error_log']} {T['generic_mount_fail'].format(url=url, path=path, error=e)}")


    encrypt(self.admin_password, self.mounts)
    clean_mount_bookmarks()
    launch_net_unmounter(admin_password)
    time.sleep(3)
    progress_dialog.close()

def main():
    auto_mount()

if __name__ == "__main__":
    main()
