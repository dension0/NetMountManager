#!/usr/bin/env python3
import os, sys, json, socket, subprocess, time, signal, shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QMessageBox, QLineEdit, QHBoxLayout,
    QTextEdit, QDialog, QVBoxLayout, QLabel, QSystemTrayIcon, QPushButton
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import QTimer, QLocale
import xml.etree.ElementTree as ET
from xml.dom import minidom

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from netmount.config import XBEL_FILE, BOOKMARK_NS, SECURE_FILE, icon_path, lang_file_un, lang_file_pw
from netmount.bookmarks import clean_mount_bookmarks, regenerate_bookmarks_from_active_mounts
from netmount.password_prompt import ask_admin_password
from netmount.decryptor import decrypt, encrypt

LANG = QLocale.system().name().split('_')[0]

def create_signal_handler():
    lang = QLocale.system().name().split('_')[0]
    msg = {
        "hu": "[INFORMÁCIÓ] NetUnmounter daemon leállítva.",
        "en": "[INFO] NetUnmounter daemon stopped."
    }
    def handler(sig, frame):
        print(msg.get(lang, msg["en"]))
        sys.exit(0)
    return handler

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

    with open(lang_file_pw, "r", encoding="utf-8") as f:
        PW_LANGS = json.load(f)
    T_PW = PW_LANGS.get(LANG, PW_LANGS['en'])
except Exception as e:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))
    err = fallback_error_msgs.get(LANG, fallback_error_msgs["en"])
    QMessageBox.critical(None, err["title"], err["text"].format(path=lang_file_un, error=e))
    sys.exit(1)

signal.signal(signal.SIGINT, create_signal_handler())
signal.signal(signal.SIGTERM, create_signal_handler())

def is_local_network_up() -> bool:
    try:
        result = subprocess.run(
            'ip -o addr show up | grep -v " lo " | grep -qE "inet(6)? "',
            shell=True
        )
        return result.returncode == 0
    except Exception:
        return False

def is_mount_dir_present(path: str) -> bool:
    try:
        Path(path).lstat()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def update_mount_status(mounts: list[dict], path: str, status: str, password: str) -> None:
    for m in mounts:
        if m.get("path") == path:
            m["last_known_status"] = status
            break
    encrypt(password, mounts)

class UnmountManager:
    def __init__(self):
        self.log_window = None
        self.log_dialog = None
        self.mounts = []
        self.setup_tray_icon()
        self.admin_password = os.environ.get("NETMOUNT_PW")
        self.log_opened_by_user = False
        self.log_shown_by_script = False
        self.user_cancelled_unmount_last_time = False
        self.user_cancelled_mount_last_time = False

    def network_stable_check(self):
        if not is_local_network_up():
            if not getattr(self, "network_interrupted_daemon_restarted", False):
                self.network_interrupted_daemon_restarted = True
                self.network_interrupted_status = 1
            else:
                self.network_interrupted_status = 2
        else:
            self.network_interrupted_daemon_restarted = False
            self.network_interrupted_status = 0

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
            if T['error_log'] in message:
                color = "red"
            elif T['ok_log'] in message:
                color = "green"
            elif T['debug_log'] in message:
                color = "gray"
            elif T['information_log'] in message:
                color = "blue"
            else:
                color = "inherit"

            self.log_window.append(f'<span style="color:{color}">{message.strip()}</span>')
            self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
            QApplication.processEvents()

    def escape_url_for_protocol(self, url: str, proto: str) -> str:
        if proto == "ftp":
            return url.replace(' ', '%20')
        elif proto == "smb":
            return url.replace(' ', r'\040')
        return url

    def is_mounted(self, path: str) -> bool:
        result = os.path.ismount(path)
        self.log(f"{T['debug_log']} is_mounted({path}) = {result}")
        return result

    def is_host_reachable(self, url: str, attempts: int = 2, timeout: float = 0.5, max_total_time: float = 1.0) -> bool:
        prefix_map = {"smb://": 445, "sftp://": 22, "ftp://": 21}
        for prefix, default_port in prefix_map.items():
            if url.startswith(prefix):
                host_part = url[len(prefix):].split('/')[0]
                host, port = (host_part.split(':') + [str(default_port)])[:2]

                start_time = time.time()
                for attempt in range(attempts):
                    try:
                        socket.create_connection((host, int(port)), timeout=timeout)
                        return True
                    except Exception:
                        if time.time() - start_time > max_total_time:
                            break
                        continue

                self.log(f"{T['debug_log']} {T['host_unreachable']} ({host}:{port})")
                return False
        return False

    def run_with_sudo(self, command: list[str]) -> bool:
        try:
            proc = subprocess.run(["sudo", "-S"] + command, input=self.admin_password + "\n", capture_output=True, text=True)
            return proc.returncode == 0
        except Exception:
            return False

    def show_log_window(self, from_tray=False):
        if self.log_window and self.log_dialog:
            if from_tray:
                return
            else:
                self.log_dialog.close()
                self.log_window = None
                self.log_dialog = None

        dialog = QDialog()
        dialog.setWindowTitle(T["log_title_log"] if from_tray else T["log_title"])
        layout = QVBoxLayout()
        layout.addWidget(QLabel(T["log_label_log"] if from_tray else T["log_label"]))

        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setFont(QFont("Fira Code", 10))
        self.log_window.setStyleSheet("QTextEdit { padding: 8px; }")

        layout.addWidget(self.log_window)

        def launch_main_gui():
            env = os.environ.copy()
            if self.admin_password:
                env["NETMOUNT_PW"] = self.admin_password
            subprocess.Popen(["python3", str(project_root / "netmount/main.py")], env=env)
            if self.log_dialog:
                self.log_dialog.close()
                self.log_dialog = None
                self.log_window = None
                self.log_shown_by_script = False

        if from_tray:
            btn_layout = QHBoxLayout()
            open_btn = QPushButton(T["open_main"])
            open_btn.clicked.connect(launch_main_gui)
            btn_layout.addWidget(open_btn)
            exit_btn = QPushButton(T["mount_check_exit"])
            exit_btn.clicked.connect(QApplication.quit)
            btn_layout.addWidget(exit_btn)
            layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        dialog.resize(500, 400)

        def on_close(event):
            self.log_window = None
            self.log_dialog = None
            self.log_shown_by_script = False
            event.accept()

        dialog.closeEvent = on_close
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

        self.log_dialog = dialog
        self.log_opened_by_user = from_tray
        self.log_shown_by_script = not from_tray

    def main_loop(self):
        self.network_stable_check()
        if self.network_interrupted_status == 1:
            self.log(f"{T['error_log']} {T['network_lost_during_cycle']}")
            return

        if not self.admin_password:
            self.admin_password = ask_admin_password(T_PW, log=self.log)
            if not self.admin_password:
                self.log(f"{T['error_log']} {T['password_invalid_final']}")
                return

        self.log(f"{T['information_log']} {T['cycle_start']}")

        try:
            self.mounts = decrypt(self.admin_password)
        except Exception as e:
            self.log(f"{T['error_log']} {T['decryption_failed'].format(error=e)}")
            return

        to_unmount = []
        to_mount = []

        for mount in self.mounts:
            user = mount.get("user", "")
            password = mount.get("password", "")
            smb_version = mount.get("smb_version", "")
            url = mount.get("url", "")
            path = mount.get("path", "")
            last_known_status = mount.get("last_known_status", "unknown")
            proto = "smb" if url.startswith("smb://") else "ftp" if url.startswith("ftp://") else "sftp" if url.startswith("sftp://") else "unknown"
            host = url.split("//")[1].split('/')[0].split(':')[0]
            automount = mount.get("automount", False)
            uid, gid = os.getuid(), os.getgid()
            if "last_known_status" not in mount:
                mount["last_known_status"] = "unknown"

            if proto == "smb":
                vers_opt = f",vers={smb_version}" if smb_version else ""
                smb_host = "//" + self.escape_url_for_protocol(url[6:], "smb")

                if not path or not smb_host or not user or not password:
                    cmd_for_mount = ""
                else:
                    cmd_for_mount = [
                        "mount", "-t", "cifs", smb_host, path, "-o",
                        f"username={user},password={password},uid={uid},gid={gid}{vers_opt}"
                    ]

                if not path:
                    cmd_for_unmount = ""
                else:
                    cmd_for_unmount = ["umount", path]
            elif proto == "ftp":
                ftp_url = self.escape_url_for_protocol(url, "ftp")
                ftp_remote = ftp_url[6:]
                ftp_host_path = ftp_remote.split('/', 1)
                ftp_host = ftp_host_path[0]

                ftp_port = ftp_host.split(':')[1] if ':' in ftp_host else '21'
                ftp_host = ftp_host.split(':')[0] if ':' in ftp_host else ftp_host
                full_ftp_host = f"{ftp_host}:{ftp_port}" if ftp_port != "21" else ftp_host

                if not ftp_host or not path or not user or not password or not ftp_port:
                    cmd_for_mount = ""
                else:
                    cmd_for_mount = [
                        "curlftpfs", full_ftp_host, path,
                        "-o", f"user={user}:{password},uid={uid},gid={gid}"
                    ]

                if not path:
                    cmd_for_unmount = ""
                else:
                    cmd_for_unmount = ["fusermount", "-u", path]
            elif proto == "sftp":
                sftp_remote = url[7:]
                sftp_host_path = sftp_remote.split('/', 1)
                sftp_host = sftp_host_path[0]
                sftp_remote_path = '/' + sftp_host_path[1] if len(sftp_host_path) > 1 else ''

                sftp_port = sftp_host.split(':')[1] if ':' in sftp_host else '22'
                sftp_host = sftp_host.split(':')[0] if ':' in sftp_host else sftp_host

                sftp_key_path = os.path.expanduser(f"~/.ssh/netmount_keys/id_rsa_{sftp_host}_{sftp_port}")

                if not user or not sftp_host or not sftp_remote_path or not path or not sftp_port or not os.path.exists(sftp_key_path):
                    cmd_for_mount = ""
                else:
                    cmd_for_mount = [
                        "sshfs", f"{user}@{sftp_host}:{sftp_remote_path}", path,
                        "-p", sftp_port,
                        "-o", f"IdentityFile={sftp_key_path},uid={uid},gid={gid},StrictHostKeyChecking=no"
                    ]

                if not path:
                    cmd_for_unmount = ""
                else:
                    cmd_for_unmount = ["fusermount", "-u", path]
            else:
                cmd_for_mount = ""
                cmd_for_unmount = ""

            if self.network_interrupted_status == 0:
                mounted = self.is_mounted(path)
                reachable = self.is_host_reachable(url)
            else:
                mounted = True
                reachable = False

            status = {
                "host": host,
                "path": path,
                "proto": proto,
                "cmd_for_mount": cmd_for_mount,
                "cmd_for_unmount": cmd_for_unmount,
                "mounted": mounted,
                "reachable": reachable,
                "automount": automount
            }

            if cmd_for_unmount and not reachable and mounted and last_known_status == "mounted":
                to_unmount.append(status)
            elif cmd_for_mount and reachable and not mounted and automount and last_known_status == "unmounted":
                to_mount.append(status)

        if to_unmount:
            if self.user_cancelled_unmount_last_time:
                self.log(f"{T['debug_log']} {T['user_cancelled_unmount']} (skipping)")
                return

            if self.log_dialog:
                self.log_dialog.close()
                self.log_dialog = None
                self.log_window = None
            self.show_log_window(from_tray=False)

            mount_list_str = "\n".join([
                f"• {entry['host']} → {entry['path']}" for entry in to_unmount
            ])
            msg = f"{T['unreachable_found']}\n\n{mount_list_str}\n\n{T['unreachable_choice']}"
            dialog = QMessageBox()
            dialog.setIcon(QMessageBox.Icon.Question)
            dialog.setWindowTitle(T["unreachable_title"])
            dialog.setText(msg)
            reboot_btn = dialog.addButton(T["reboot_now"], QMessageBox.ButtonRole.YesRole)
            unmount_btn = dialog.addButton(T["unmount_now"], QMessageBox.ButtonRole.NoRole)
            cancel_btn = dialog.addButton(QMessageBox.StandardButton.Cancel)
            dialog.exec()

            clicked = dialog.clickedButton()

            if clicked == reboot_btn:
                self.log(f"{T['information_log']} {T['rebooting_system']}")
                if self.log_dialog:
                    self.log_dialog.close()
                    self.log_dialog = None
                    self.log_window = None
                subprocess.run(["reboot"])
                return
            elif clicked == unmount_btn:
                self.network_stable_check()
                self.log(f"{T['information_log']} {T['proceeding_with_unmount']}")
                any_action_taken = False

                for entry in to_unmount:
                    try:
                        if self.network_interrupted_status == 0 or self.network_interrupted_status == 2:
                            self.log(f"{T['information_log']} {T['unmounting_entry'].format(host=entry['host'], path=entry['path'])}")
                            if entry['proto'] == "smb":
                                self.run_with_sudo(entry['cmd_for_unmount'])
                                shutil.rmtree(entry['path'], ignore_errors=True)
                                update_mount_status(self.mounts, entry['path'], "unmounted", self.admin_password)
                                any_action_taken = True
                            elif entry['proto'] in ("ftp", "sftp"):
                                subprocess.run(entry['cmd_for_unmount'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                shutil.rmtree(entry['path'], ignore_errors=True)
                                update_mount_status(self.mounts, entry['path'], "unmounted", self.admin_password)
                                any_action_taken = True
                            else:
                                self.log(f"{T['ok_log']} {T['not_compatible_mount'].format(host=entry['host'])}")
                                continue
                            self.log(f"{T['ok_log']} {T['entry_unmounted'].format(host=entry['host'], path=entry['path'])}")
                        else:
                            self.log(f"{T['error_log']} {T['network_lost_during_cycle']}")

                    except Exception as e:
                        self.log(f"{T['error_log']} {T['mount_failed'].format(error=e)}")

                if any_action_taken:
                    clean_mount_bookmarks()
                    self.log(f"{T['ok_log']} {T['all_unmounted_successfully']}")
                    QTimer.singleShot(5000, lambda: self.log_dialog and self.log_dialog.close())
                    QMessageBox.information(None, T["finished_title"], T["finished_text"])
                return
            else:
                self.log(f"{T['debug_log']} {T['user_cancelled_unmount']}")
                self.user_cancelled_unmount_last_time = True
                return
        elif to_mount:
            if self.user_cancelled_mount_last_time:
                self.log(f"{T['debug_log']} {T['user_cancelled_mount']} (skipping)")
                return

            if self.log_dialog:
                self.log_dialog.close()
                self.log_dialog = None
                self.log_window = None
            self.show_log_window(from_tray=False)

            mount_list_str = "\n".join([
                f"• {entry['host']} → {entry['path']}" for entry in to_mount
            ])
            msg = f"{T['mountable_found']}\n\n{mount_list_str}\n\n{T['mountable_choice']}"
            dialog = QMessageBox()
            dialog.setIcon(QMessageBox.Icon.Question)
            dialog.setWindowTitle(T["mountable_title"])
            dialog.setText(msg)
            proceed_btn = dialog.addButton(T["mount_now"], QMessageBox.ButtonRole.YesRole)
            cancel_btn = dialog.addButton(QMessageBox.StandardButton.Cancel)
            dialog.exec()

            clicked = dialog.clickedButton()

            if clicked == proceed_btn:
                self.network_stable_check()
                self.log(f"{T['information_log']} {T['proceeding_with_mount']}")
                any_action_taken = False

                for entry in to_mount:
                    try:
                        if self.network_interrupted_status == 0:
                            result = False
                            stderr = ""

                            self.log(f"{T['information_log']} {T['mounting_entry'].format(host=entry['host'], path=entry['path'])}")

                            if not os.path.exists(entry['path']):
                                os.makedirs(entry['path'], exist_ok=True)

                            if entry['proto'] == "smb":
                                proc = subprocess.run(
                                    ["sudo", "-S"] + entry['cmd_for_mount'],
                                    input=self.admin_password + "\n",
                                    capture_output=True,
                                    text=True
                                )
                                stderr = proc.stderr
                                result = proc.returncode == 0
                                update_mount_status(self.mounts, entry['path'], "mounted", self.admin_password)
                            elif entry['proto'] in ("ftp", "sftp"):
                                proc = subprocess.run(
                                    entry['cmd_for_mount'],
                                    check=False,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE,
                                    text=True
                                )
                                stderr = proc.stderr
                                result = proc.returncode == 0
                                update_mount_status(self.mounts, entry['path'], "mounted", self.admin_password)
                            else:
                                self.log(f"{T['ok_log']} {T['not_compatible_mount'].format(host=entry['host'])}")

                            if result:
                                self.log(f"{T['ok_log']} {T['entry_mounted'].format(host=entry['host'], path=entry['path'])}")
                                any_action_taken = True
                            else:
                                if "530" in stderr or "Access denied" in stderr or "Permission denied" in stderr:
                                    self.log(f"{T['error_log']} {T['auth_failed'].format(host=entry['host'])}")
                                elif "No such file or directory" in stderr or "Connection refused" in stderr:
                                    self.log(f"{T['error_log']} {T['mount_failed'].format(error=T['connection_refused'])}")
                                else:
                                    self.log(f"{T['error_log']} {T['mount_failed'].format(error=stderr.strip() or T['unknown_error'])}")
                        else:
                            self.log(f"{T['error_log']} {T['network_lost_during_cycle']}")

                    except Exception as e:
                        self.log(f"{T['error_log']} {T['mount_failed'].format(error=e)}")

                if any_action_taken:
                    regenerate_bookmarks_from_active_mounts(self.mounts)
                    self.log(f"{T['ok_log']} {T['all_mounted_successfully']}")
                    QTimer.singleShot(5000, lambda: self.log_dialog and self.log_dialog.close())
                    QMessageBox.information(None, T["finished_title"], T["finished_text"])
                return
            else:
                self.log(f"{T['debug_log']} {T['user_cancelled_mount']}")
                self.user_cancelled_mount_last_time = True
                return
        else:
            if not to_unmount and not to_mount:
                self.log(f"{T['debug_log']} {T['action_not_required']}")
            self.log(f"{T['ok_log']} {T['end_of_check']}")

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))
    time.sleep(5)
    manager = UnmountManager()
    timer = QTimer()
    timer.timeout.connect(manager.main_loop)
    timer.start(5000)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
