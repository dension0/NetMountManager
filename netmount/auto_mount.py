#!/usr/bin/env python3
# --- BEGIN: localized auto-install missing Python deps (improved) ---
import importlib, sys, os, subprocess, shlex, shutil
from datetime import datetime

# --- automatic short lang detect (hu or en) ---
_env_lang = (os.environ.get("LC_ALL") or os.environ.get("LANG") or "en").split(".")[0]
LANG = _env_lang.split("_")[0] if "_" in _env_lang else _env_lang
if LANG not in ("hu", "en"):
    LANG = "en"
# ---------------------------------------------------------

REQ = [("PyQt6", "pyqt6"), ("cryptography", "cryptography")]

def module_ok(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False

missing = [pip for mod, pip in REQ if not module_ok(mod)]

MSG = {
    "en": {
        "missing": "Missing Python packages required by NetMountManager: {pkgs}",
        "no_display": "No graphical display detected. Please run the installer manually or use the DNF command below.",
        "dnf_reco": "sudo dnf install -y python3-cryptography python3-qt6 sshpass curlftpfs fuse-sshfs cifs-utils",
        "pip_cmd": "python3 -m pip install --user {pkgs}",
        "no_terminal": "No terminal emulator found to show the installer. Running pip in-process (output may be invisible in autostart).",
        "install_ok": "Dependencies installed successfully.",
        "install_fail": "Dependencies installation failed. Please inspect the output.",
        "dialog_title": "NetMountManager — Installer",
        "close_btn": "Close",
        "press_enter": "Press ENTER to close..."
    },
    "hu": {
        "missing": "Hiányzó Python csomagok a NetMountManager számára: {pkgs}",
        "no_display": "Nem található grafikus kijelző. Telepítsd kézzel vagy használd az alábbi DNF parancsot.",
        "dnf_reco": "sudo dnf install -y python3-cryptography python3-qt6 sshpass curlftpfs fuse-sshfs cifs-utils",
        "pip_cmd": "python3 -m pip install --user {pkgs}",
        "no_terminal": "Nem található terminálemulátor a telepítő megjelenítéséhez. A pip in-process fut (autostart alatt nem biztos, hogy látható).",
        "install_ok": "A függőségek sikeresen telepítve.",
        "install_fail": "A függőségek telepítése sikertelen. Nézd meg a kimenetet.",
        "dialog_title": "NetMountManager — Telepítő",
        "close_btn": "Bezárás",
        "press_enter": "Nyomj Entert a bezáráshoz..."
    }
}[LANG]

if not missing:
    pass
else:
    pkgs_str = " ".join(missing)

    if os.geteuid() == 0:
        sys.stderr.write(MSG["missing"].format(pkgs=pkgs_str) + "\n")
        sys.stderr.write(MSG["dnf_reco"] + "\n")
        sys.exit(1)

    # If PyQt6 is available -> show QDialog and stream pip output into it
    if module_ok("PyQt6"):
        from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
        from PyQt6.QtCore import QProcess, QTimer

        app = QApplication.instance() or QApplication([])

        dlg = QDialog()
        dlg.setWindowTitle(MSG["dialog_title"])
        dlg.resize(780, 480)
        layout = QVBoxLayout(dlg)

        header = QLabel(MSG["missing"].format(pkgs=pkgs_str))
        header.setWordWrap(True)
        layout.addWidget(header)

        out = QTextEdit(readOnly=True)
        out.setAcceptRichText(False)
        layout.addWidget(out)

        btn_close = QPushButton(MSG["close_btn"])
        btn_close.setEnabled(False)
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)

        proc = QProcess(dlg)

        def append_stdout():
            data = proc.readAllStandardOutput().data().decode(errors="replace")
            if data:
                for line in data.splitlines(True):
                    ts = datetime.now().strftime("[%H:%M:%S] ")
                    out.moveCursor(out.textCursor().End)
                    out.insertPlainText(ts + line)
                out.ensureCursorVisible()

        def append_stderr():
            data = proc.readAllStandardError().data().decode(errors="replace")
            if data:
                for line in data.splitlines(True):
                    ts = datetime.now().strftime("[%H:%M:%S] ")
                    out.moveCursor(out.textCursor().End)
                    out.insertPlainText(ts + line)
                out.ensureCursorVisible()

        proc.readyReadStandardOutput.connect(append_stdout)
        proc.readyReadStandardError.connect(append_stderr)

        def finished(code, status):
            if code == 0:
                out.append("\n=== " + MSG["install_ok"] + " ===\n")
                QTimer.singleShot(1200, dlg.accept)
            else:
                out.append("\n=== " + MSG["install_fail"] + " ===\n")
                btn_close.setEnabled(True)

        proc.finished.connect(finished)

        cmd = [sys.executable, "-m", "pip", "install", "--user"] + missing
        out.append("Running: " + shlex.join(cmd) + "\n\n")
        proc.start(cmd[0], cmd[1:])
        dlg.exec()

        still_missing = [pip for mod, pip in REQ if not module_ok(mod)]
        if still_missing:
            sys.stderr.write(MSG["missing"].format(pkgs=" ".join(still_missing)) + "\n")
            sys.stderr.write(MSG["dnf_reco"] + "\n")
            sys.exit(1)

    else:
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if not has_display:
            sys.stderr.write(MSG["missing"].format(pkgs=pkgs_str) + "\n")
            sys.stderr.write(MSG["no_display"] + "\n")
            sys.stderr.write(MSG["dnf_reco"] + "\n")
            sys.exit(1)

        terms = ["gnome-terminal","konsole","xfce4-terminal","xterm","mate-terminal","tilix","alacritty","kitty"]
        term = next((t for t in terms if shutil.which(t)), None)

        if not term:
            sys.stderr.write(MSG["no_terminal"] + "\n")
            try:
                proc = subprocess.run([sys.executable, "-m", "pip", "install", "--user"] + missing, check=False)
            except Exception as e:
                sys.stderr.write("pip failed: " + str(e) + "\n")
                sys.stderr.write(MSG["dnf_reco"] + "\n")
                sys.exit(1)
            if proc.returncode != 0:
                sys.stderr.write(MSG["install_fail"] + "\n")
                sys.stderr.write(MSG["pip_cmd"].format(pkgs=pkgs_str) + "\n")
                sys.exit(1)
        else:
            pip_cmd = shlex.join([sys.executable, "-m", "pip", "install", "--user"] + missing)
            shell_cmd = f"bash -lc 'echo \"{shlex.quote(MSG['missing'].format(pkgs=pkgs_str))}\"; {pip_cmd}; echo; echo \"{shlex.quote(MSG['press_enter'])}\"; read -r'"
            if term in ("gnome-terminal","tilix"):
                cmd = [term, "--", "bash", "-c", shell_cmd]
            elif term == "konsole":
                cmd = [term, "-e", "bash", "-c", shell_cmd]
            else:
                cmd = [term, "-e", "bash", "-c", shell_cmd]
            try:
                subprocess.run(cmd)
            except Exception as e:
                sys.stderr.write("Failed to launch terminal: " + str(e) + "\n")
                sys.stderr.write(MSG["pip_cmd"].format(pkgs=pkgs_str) + "\n")
                sys.exit(1)

            still_missing = [pip for mod, pip in REQ if not module_ok(mod)]
            if still_missing:
                sys.stderr.write(MSG["missing"].format(pkgs=" ".join(still_missing)) + "\n")
                sys.stderr.write(MSG["dnf_reco"] + "\n")
# --- END: localized auto-install missing Python deps (improved) ---

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
        log(f"{T.get('information_log','[i]')} {T.get('no_config_file','No config file')}")
        return

    try:
        mounts = decrypt(admin_password)
    except Exception as e:
        log(f"{T.get('error_log','[ERROR]')} {T.get('decryption_failed','Decryption failed').format(error=e)}")
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

    # persist changes: encrypt with correct variables
    try:
        encrypt(admin_password, mounts)
    except Exception as e:
        log(f"{T.get('error_log','[ERROR]')} {T.get('config_save_failed','Config save failed').format(str(e))}")

    clean_mount_bookmarks()
    launch_net_unmounter(admin_password)
    time.sleep(3)
    progress_dialog.close()

def main():
    auto_mount()

if __name__ == "__main__":
    main()
