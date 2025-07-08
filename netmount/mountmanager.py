#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import re
import urllib.parse
import shutil
import pwd
import threading
import shlex
import tempfile
import time
import socket
import getpass
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QListWidget, QMessageBox,
    QFileDialog, QCheckBox, QListWidgetItem, QFrame, QToolButton,
    QDialog, QTextEdit, QInputDialog, QAbstractItemView, QSizePolicy
)
from PyQt6.QtCore import Qt, QLocale, QSize, QTimer, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from datetime import datetime
from getpass import getuser
from pathlib import Path
from netmount.decryptor import decrypt, encrypt

from netmount.config import (
    XBEL_FILE, BOOKMARK_NS, SECURE_FILE, AUTOMOUNT_SCRIPT,
    SMBUNMOUNT_SCRIPT, SMBUNMOUNT_SCRIPT_OLD, AUTOMOUNT_EXEC, SMBUNMOUNT_EXEC, icon_path
)

class LoadingDialog(QDialog):
    def __init__(self, T, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T['title'])
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)

        layout = QVBoxLayout()
        label = QLabel(T['loading_check'])
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)
        self.resize(300, 100)
        self.show()
        QApplication.processEvents()

class MountManager(QWidget):
    def __init__(self, T, admin_password):
        super().__init__()
        self.T = T
        self.admin_password = admin_password
        self.setWindowTitle(self.T['title'])
        self.resize(1100, 700)
        self.setMinimumSize(1100, 700)
        self.mounts = []
        self.load_config()

        layout = QVBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.T['url'])
        url_tip = QToolButton()
        url_tip.setText("?")
        url_tip.setToolTip(self.T['url_tip'])

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(self.T['path'])
        path_tip = QToolButton()
        path_tip.setText("?")
        path_tip.setToolTip(self.T['path_tip'])

        self.smb_version_input = QLineEdit()
        self.smb_version_input.setPlaceholderText(self.T['smb_version'])
        smb_version_tip = QToolButton()
        smb_version_tip.setText("?")
        smb_version_tip.setToolTip(self.T['smb_version_tip'])
        self.smb_version_input.setEnabled(False)
        self.smb_version_input.setStyleSheet("background-color: #2a2a2a; color: #aaa;")

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText(self.T['user'])
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText(self.T['password'])
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        add_btn = QPushButton(self.T['add'])
        add_btn.setIcon(QIcon.fromTheme("list-add"))
        add_btn.clicked.connect(self.add_mount)
        add_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        reset_btn = QPushButton(self.T['reset'])
        reset_btn.setToolTip(self.T['reset_tooltip'])
        reset_btn.setIcon(QIcon.fromTheme("view-refresh"))
        reset_btn.clicked.connect(self.reset_fields)

        self.unmounter_btn = QPushButton()
        self.unmounter_btn.setFixedWidth(250)
        self.update_unmounter_button()
        self.unmounter_btn.setToolTip(self.T['smb_unmounter_tooltip'])
        self.unmounter_btn.clicked.connect(self.toggle_unmounter)
        self.unmounter_timer = QTimer(self)
        self.unmounter_timer.timeout.connect(self.update_unmounter_button)
        self.unmounter_timer.start(2000)

        export_btn = QPushButton(self.T['export_title'])
        export_btn.setIcon(QIcon.fromTheme("document-save"))
        export_btn.setFixedWidth(250)
        export_btn.setStyleSheet("background-color: #43a047; color: #0d3a16;")
        export_btn.setToolTip(self.T['export_tooltip'])
        export_btn.clicked.connect(self.export_secure_config)

        import_btn = QPushButton(self.T['import_title'])
        import_btn.setIcon(QIcon.fromTheme("document-open"))
        import_btn.setFixedWidth(250)
        import_btn.setStyleSheet("background-color: #42a5f5; color: #0d47a1;")
        import_btn.setToolTip(self.T['import_tooltip'])
        import_btn.clicked.connect(self.import_secure_config)

        user_row = QHBoxLayout()
        user_row.addWidget(self.user_input)
        user_row.addSpacing(5)
        user_row.addWidget(export_btn)

        pass_row = QHBoxLayout()
        pass_row.addWidget(self.pass_input)
        pass_row.addSpacing(5)
        pass_row.addWidget(import_btn)

        btn_row = QHBoxLayout()
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(add_btn)
        btn_row.addSpacing(5)
        btn_row.addWidget(self.unmounter_btn)

        self.list_widget = QListWidget()

        url_h = QHBoxLayout()
        url_h.addWidget(self.url_input)
        url_h.addWidget(url_tip)

        path_h = QHBoxLayout()
        path_h.addWidget(self.path_input)
        path_h.addWidget(path_tip)

        smb_h = QHBoxLayout()
        smb_h.addWidget(self.smb_version_input)
        smb_h.addWidget(smb_version_tip)

        layout.addLayout(url_h)
        layout.addLayout(path_h)
        layout.addLayout(smb_h)
        layout.addLayout(user_row)
        layout.addLayout(pass_row)
        layout.addLayout(btn_row)
        layout.addWidget(self.list_widget)

        current_year = datetime.now().year
        footer = QLabel()
        footer.setTextFormat(Qt.TextFormat.RichText)
        footer.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        footer.setOpenExternalLinks(True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setText(
            f"<small>&copy; {current_year} Created by <b>Madarász László</b> (@dension) – "
            f"<a href='https://pixellegion.org'>pixellegion.org</a> – "
            f"<a href='mailto:info@pixellegion.org'>info@pixellegion.org</a> | Powered by "
            f"<a href='https://chatgpt.com'>ChatGPT</a></small>"
        )
        footer.setStyleSheet("""
            QLabel {
                color: palette(text);
                background-color: transparent;
                font-size: 11px;
                padding: 8px;
            }
        """)

        layout.addWidget(footer)

        self.url_input.textChanged.connect(self.on_url_changed)

        self.setLayout(layout)
        self.remove_oldsmbunmount_service()
        self.create_autostart_service()
        self.create_smbunmount_service()
        self.enable_reordering_features()

    def enable_reordering_features(self):
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.model().rowsMoved.connect(self.save_current_order)

        self.list_widget.setStyleSheet("""
QListWidget::item {
    border: 1px solid transparent;
    padding: 5px;
}

QListWidget::item:selected {
    border: 2px solid;
    background-color: transparent;
}

QListWidget::item:hover {
    border: 1px solid;
    background-color: transparent;
}
        """)

    def save_current_order(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                labels = widget.findChildren(QLabel)
                path = ""
                url = ""
                for label in labels:
                    text = label.text()
                    if text.startswith("smb://") or text.startswith("ftp://") or text.startswith("sftp://"):
                        url = text
                    elif text.startswith("/"):
                        path = text

                for mount in self.mounts:
                    if mount['path'] == path and mount['url'] == url:
                        mount['order'] = i
                        break

        self.save_config()
        self.refresh_with_loading()
        self.regenerate_bookmarks_from_active_mounts()

    def is_unmounter_running(self):
        try:
            user = getpass.getuser()
            result = subprocess.run(
                ["ps", "-u", user, "-o", "pid,cmd"],
                stdout=subprocess.PIPE,
                text=True
            )
            for line in result.stdout.splitlines():
                if "net_unmounter.py" in line and "python3" in line:
                    return True
            return False
        except Exception:
            return False

    def update_unmounter_button(self):
        if self.is_unmounter_running():
            self.unmounter_btn.setText("🟢 " + self.T["stop_unmounter"])
        else:
            self.unmounter_btn.setText("🛑 " + self.T["start_unmounter"])

    def toggle_unmounter(self):
        if self.is_unmounter_running():
            subprocess.run(["pkill", "-f", "net_unmounter.py"])
        else:
            env = os.environ.copy()
            env["NETMOUNT_PW"] = self.admin_password
            subprocess.Popen(["python3", SMBUNMOUNT_EXEC], env=env)

        QTimer.singleShot(1000, self.update_unmounter_button)

    def reset_fields(self):
        self.url_input.clear()
        self.path_input.clear()
        self.smb_version_input.clear()
        self.user_input.clear()
        self.pass_input.clear()
        self.smb_version_input.setEnabled(False)
        self.smb_version_input.setStyleSheet("background-color: #2a2a2a; color: #aaa;")

    def refresh_with_loading(self, external_dialog=None):
        if external_dialog:
            self.loading_dialog = external_dialog
        else:
            self.loading_dialog = LoadingDialog(self.T, self)
            self.loading_dialog.show()
            QApplication.processEvents()

        self.refresh_list()

        if not external_dialog:
            QTimer.singleShot(200, self.loading_dialog.close)

    def on_url_changed(self, text):
        url = text.strip().lower()

        if url.startswith("smb://"):
            self.smb_version_input.setEnabled(True)
            self.smb_version_input.setStyleSheet("")
        else:
            self.smb_version_input.setEnabled(False)
            self.smb_version_input.clear()
            self.smb_version_input.setStyleSheet("background-color: #2a2a2a; color: #aaa;")

        if url.startswith("sftp://"):
            self.pass_input.setEnabled(False)
            self.pass_input.clear()
            self.pass_input.setStyleSheet("background-color: #2a2a2a; color: #aaa;")
            self.pass_input.setPlaceholderText(self.T["key_auth_required"])
        else:
            self.pass_input.setEnabled(True)
            self.pass_input.setStyleSheet("")
            self.pass_input.setPlaceholderText(self.T['password'])


    def load_config(self):
        try:
            self.mounts = decrypt(self.admin_password)

            if not isinstance(self.mounts, list):
                raise ValueError("Konfigurációs adat nem lista típusú.")

            updated = False

            for i, mount in enumerate(self.mounts):
                if 'order' not in mount:
                    mount['order'] = i
                    updated = True

            self.mounts.sort(key=lambda x: x.get('order', 0))

            if updated:
                self.save_config()

        except ValueError:
            QMessageBox.critical(self, self.T['error'], self.T['invalid_config'])
            self.mounts = []
        except Exception as e:
            QMessageBox.critical(self, self.T['error'], self.T['config_load_failed'].format(str(e)))
            self.mounts = []


    def save_config(self):
        try:
            encrypt(self.admin_password, self.mounts)
        except Exception as e:
            QMessageBox.critical(self, self.T['error'], self.T['config_save_failed'].format(str(e)))

    def refresh_list(self):
        self.list_widget.clear()
        self.smb_check_threads = []
        self.mounts.sort(key=lambda x: x.get('order', 0))

        for i, mount in enumerate(self.mounts):
            try:
                url = mount.get('url', '')
                path = mount.get('path', '')
                order = mount.get('order', 0)
                if not url or not path:
                    continue

                label_order = QLabel(f"[{order}]")
                label_order.setFixedWidth(40)

                item = QListWidgetItem()
                widget = QWidget()
                h = QHBoxLayout()

                label_order = QLabel(f"[{order}]")
                label_order.setFixedWidth(40)

                checkbox = QCheckBox()
                checkbox.setChecked(mount.get('automount', False))
                checkbox.setToolTip(self.T['automount'])

                if not self.is_mounted(path):
                    checkbox.setEnabled(False)
                    checkbox.setToolTip(self.T['automount_disabled_not_mounted'])
                else:
                    checkbox.stateChanged.connect(lambda state, idx=i: self.toggle_automount(idx, state))

                label_url = QLabel(f"{url}")
                label_url.setStyleSheet("QLabel { padding-left: 5px; }")
                label_url.setMinimumWidth(130)

                label_arrow = QLabel(f"←")
                label_arrow.setFixedWidth(40)
                label_arrow.setStyleSheet("QLabel { padding-left: 5px; padding-right: 5px;}")

                label_path = QLabel(f"{path}")
                label_path.setMinimumWidth(130)

                mount_btn = QPushButton(self.T['mount'] if not self.is_mounted(path) else self.T['unmount'])
                mount_btn.setFixedWidth(120)
                mount_btn.clicked.connect(lambda _, idx=i, b=mount_btn: self.toggle_mount(idx, b))

                edit_btn = QPushButton(self.T['edit'])
                edit_btn.setFixedWidth(120)
                edit_btn.setIcon(QIcon.fromTheme("document-edit"))
                edit_btn.clicked.connect(lambda _, idx=i: self.edit_mount(idx))

                del_btn = QPushButton(self.T['remove'])
                del_btn.setFixedWidth(120)
                del_btn.setIcon(QIcon.fromTheme("edit-delete"))
                del_btn.clicked.connect(lambda _, idx=i: self.remove_mount(idx))

                h.addWidget(label_order)
                h.addWidget(checkbox)
                h.addWidget(label_url)
                h.addWidget(label_arrow)
                h.addWidget(label_path)
                h.addStretch()
                h.addWidget(mount_btn)
                h.addWidget(edit_btn)
                h.addWidget(del_btn)
                h.setContentsMargins(5, 5, 5, 5)

                widget.setLayout(h)
                item.setSizeHint(widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)

                mount_btn.setEnabled(True)
                mount_btn.setToolTip("")
                mount_btn.setIcon(QIcon.fromTheme("network-wired"))
                mount_btn.setStyleSheet("background-color: #e8f5e9; color: #1b5e20;")

                if self.is_mounted(mount['path']):
                    mount_btn.setIcon(QIcon.fromTheme("network-connect"))
                    mount_btn.setStyleSheet("background-color: #43a047; color: white;")

                elif url.startswith("sftp://") and not self.has_keyfile(mount):
                    mount_btn.setEnabled(False)
                    mount_btn.setIcon(QIcon.fromTheme("dialog-error"))
                    mount_btn.setToolTip(self.T['no_installed_ssh_key'])
                    mount_btn.setStyleSheet("background-color: #f8d7da; color: #721c24;")

                elif url.startswith("sftp://") and mount.get("sshkeyvalid") is False:
                    mount_btn.setEnabled(False)
                    mount_btn.setIcon(QIcon.fromTheme("dialog-error"))
                    mount_btn.setToolTip(self.T['sshkey_invalid_tooltip'])
                    mount_btn.setStyleSheet("background-color: #f8d7da; color: #721c24;")

                elif url.startswith("smb://"):
                    host = url[6:].split('/')[0].split(':')[0]
                    if not self.is_host_reachable(host):
                        mount_btn.setEnabled(False)
                        mount_btn.setIcon(QIcon.fromTheme("dialog-error"))
                        mount_btn.setToolTip(self.T['host_unreachable_smb'])
                        mount_btn.setStyleSheet("background-color: #f8d7da; color: #721c24;")

            except Exception as e:
                print(f"{self.T['warning']} {self.T['mount_item_error']} {e}")
                continue

    def export_secure_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.T['export_title'],
            str(Path.home()),
            "Secure Files (*.secure)"
        )
        if not path:
            return
        try:
            encrypt(self.admin_password, self.mounts, Path(path))
            QMessageBox.information(self, self.T['success'], self.T['export_success'].format(path))
        except Exception as e:
            QMessageBox.critical(self, self.T['error'], self.T['export_failed'].format(str(e)))


    def import_secure_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.T['import_title'],
            str(Path.home()),
            "Secure Files (*.secure)"
        )
        if not path:
            return

        text, ok = QInputDialog.getText(
            self,
            self.T['admin_password_title'],
            self.T['admin_password_text_old'],
            QLineEdit.EchoMode.Password
        )
        if not ok or not text:
            QMessageBox.warning(self, self.T['error'], self.T['admin_password_required_old'])
            return

        try:
            imported = decrypt(text, Path(path))

            if not isinstance(imported, list):
                raise ValueError("Invalid configuration format.")

            existing = {(m.get("url"), m.get("path")): i for i, m in enumerate(self.mounts)}
            added, replaced = 0, 0

            for item in imported:
                key = (item.get("url"), item.get("path"))
                if key in existing:
                    idx = existing[key]
                    existing_entry = self.mounts[idx]

                    reply = QMessageBox.question(
                        self,
                        self.T['duplicate_entry_title'],
                        self.T['duplicate_entry_text'].format(url=key[0], path=key[1], user=item.get("user")),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.mounts[idx] = item
                        replaced += 1
                else:
                    self.mounts.append(item)
                    existing[key] = len(self.mounts) - 1
                    added += 1

            if added == 0 and replaced == 0:
                QMessageBox.information(self, self.T['info'], self.T['import_no_new'])
            else:
                encrypt(self.admin_password, self.mounts)
                self.refresh_with_loading()
                QMessageBox.information(
                    self, self.T['success'],
                    self.T['import_result_summary'].format(added=added, replaced=replaced)
                )

        except Exception as e:
            QMessageBox.critical(self, self.T['error'], self.T['import_failed'].format(str(e)))

    def run_with_sudo(self, command: list[str]) -> bool:
        try:
            proc = subprocess.run(
                ["sudo", "-S"] + command,
                input=self.admin_password + "\n",
                capture_output=True,
                text=True
            )
            if proc.returncode == 0:
                return True
            else:
                QMessageBox.critical(
                    self,
                    self.T['error'],
                    self.T['admin_error'].format(proc.stderr)
                )
                return False
        except Exception as e:
            QMessageBox.critical(
                self,
                self.T['error'],
                self.T['admin_error'].format(str(e))
            )
            return False

    def is_host_reachable(self, host: str, port: int = 445, timeout: float = 2.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def toggle_automount(self, index, state):
        if state == Qt.CheckState.Checked.value:
            self.mounts[index]['automount'] = True
            self.save_config()
            QMessageBox.information(self, self.T['success'], self.T['autostart_created'])
        elif state == Qt.CheckState.Unchecked.value:
            self.mounts[index]['automount'] = False
            self.save_config()
            QMessageBox.information(self, self.T['success'], self.T['autostart_removed'])

        self.refresh_with_loading()

    def toggle_mount(self, index, button):
        mount = self.mounts[index]
        path = mount['path']
        is_smb = mount['url'].startswith("smb://")

        try:
            if self.is_mounted(path):
                reply = QMessageBox.question(
                    self,
                    self.T['confirm_unmount_title'],
                    self.T['confirm_unmount'],
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    return

                if is_smb:
                    if not self.run_with_sudo(["umount", path]):
                        self.refresh_with_loading()
                        return
                else:
                    try:
                        QTimer.singleShot(100, self.refresh_with_loading)
                        subprocess.run(["fusermount", "-u", path], check=True)
                        self.refresh_with_loading()
                    except subprocess.CalledProcessError as e:
                        QMessageBox.critical(self, self.T['error'], self.T['admin_error'].format(str(e)))
                        return

                QMessageBox.information(self, self.T['success'], self.T['unmount_success'])

                self.mounts[index]['automount'] = False
                self.save_config()

                try:
                    QTimer.singleShot(100, self.refresh_with_loading)
                    if os.path.exists(path) and not os.path.ismount(path):
                        shutil.rmtree(path)
                    self.refresh_with_loading()
                except Exception as e:
                    QMessageBox.warning(self, self.T['error'], self.T['delete_dir_failed'].format(e))
                    return

                button.setText(self.T['unmount'])
                self.refresh_with_loading()
                self.regenerate_bookmarks_from_active_mounts()

            else:
                try:
                    if not os.path.exists(path):
                        os.makedirs(path, exist_ok=True)
                    self.refresh_with_loading()
                except Exception as e:
                    QMessageBox.critical(self, self.T['error'], self.T['admin_error'].format(str(e)))
                    return

                self.mount_entry(mount)
        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['mount']}/{self.T['mount_failed']}\n\n{str(e)}")
            return

    def show_key_setup_wizard(self, entry):
        try:
            dialog = KeySetupWizard(entry, self.T, self)
            dialog.exec()

            if dialog.success:
                QMessageBox.information(self, self.T['success'], self.T['mount_success'])
                self.refresh_with_loading()
            else:
                QMessageBox.warning(self, self.T['error'], self.T['mount_failed'])
                self.refresh_with_loading()

        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['mount_failed']}\n\n{str(e)}")
            self.refresh_with_loading()


    def add_mount(self):
        raw_path = self.path_input.text().strip()
        if not re.match(r'^[a-zA-Z0-9]+$', raw_path):
            QMessageBox.critical(self, self.T['error'], self.T['invalid_path'])
            self.refresh_with_loading()
            return

        try:
            mnt_root = os.path.expanduser("~/mnt")
            os.makedirs(mnt_root, exist_ok=True)

            full_path = os.path.join(mnt_root, raw_path)
            url = self.url_input.text().strip()
            smb_version_number = self.smb_version_input.text().strip()

            for m in self.mounts:
                if m['path'] == full_path:
                    QMessageBox.warning(self, self.T['error'], self.T['duplicate_path'])
                    return
                if m['url'] == url:
                    QMessageBox.warning(self, self.T['error'], self.T['duplicate_url'])
                    return

            if not re.match(r'^(sftp|ftp|smb)://.+', url):
                QMessageBox.critical(self, self.T['error'], self.T['invalid_url'])
                self.refresh_with_loading()
                return

            max_order = max((m.get('order', 0) for m in self.mounts), default=-1)

            entry = {
                'url': url,
                'path': full_path,
                'smb_version': smb_version_number,
                'user': self.user_input.text(),
                'password': self.pass_input.text(),
                'automount': False,
                'order': max_order + 1
            }

            self.mounts.append(entry)
            self.save_config()
            self.refresh_with_loading()

            if url.startswith("sftp://"):
                self.show_key_setup_wizard(entry)

        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['add_failed']}\n\n{str(e)}")

    def edit_mount(self, index):
        try:
            mount = self.mounts[index]
            path = mount['path']
            is_smb = mount['url'].startswith("smb://")
            mnt_root = os.path.expanduser("~/mnt").rstrip("/") + "/"

            if self.is_mounted(path):
                if is_smb:
                    if not self.run_with_sudo(["umount", path]):
                        self.refresh_with_loading()
                        return
                else:
                    if not self.run_with_sudo(["fusermount", "-u", path]):
                        self.refresh_with_loading()
                        return

            if os.path.exists(path) and not os.path.ismount(path):
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    QMessageBox.warning(self, self.T['error'], self.T['delete_dir_failed'].format(str(e)))
                    self.refresh_with_loading()
                    return

            mount['automount'] = False
            del self.mounts[index]
            self.save_config()

            self.url_input.setText(mount['url'])
            self.path_input.setText(mount['path'].replace(mnt_root, ""))
            self.smb_version_input.setText(mount.get('smb_version', ''))
            self.user_input.setText(mount['user'])
            self.pass_input.setText(mount['password'])

            self.refresh_with_loading()
            self.regenerate_bookmarks_from_active_mounts()

        except IndexError:
            QMessageBox.critical(self, self.T['error'], self.T['invalid_index'])
        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['edit_failed']}\n\n{str(e)}")


    def remove_mount(self, index):
        try:
            mount = self.mounts[index]
            path = mount['path']
            url = mount.get('url', '')

            confirm = QMessageBox.question(
                self,
                self.T['remove_confirm_title'],
                self.T['remove_confirm_text'].format(path=path),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

            is_smb = mount['url'].startswith("smb://")
            is_ftp = mount['url'].startswith("ftp://")

            if self.is_mounted(path):
                if is_smb:
                    if not self.run_with_sudo(["umount", path]):
                        self.refresh_with_loading()
                        return
                else:
                    if not self.run_with_sudo(["fusermount", "-u", path]):
                        self.refresh_with_loading()
                        return

            if os.path.exists(path) and not os.path.ismount(path):
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    QMessageBox.warning(self, self.T['error'], self.T['delete_dir_failed'].format(str(e)))
                    self.refresh_with_loading()
                    return

            mount['automount'] = False
            del self.mounts[index]

            try:
                self.save_config()
            except Exception as e:
                QMessageBox.critical(self, self.T['error'], self.T['config_save_failed'].format(str(e)))
                self.refresh_with_loading()
                return

            self.reassign_orders()
            self.refresh_with_loading()
            self.regenerate_bookmarks_from_active_mounts()

        except IndexError:
            QMessageBox.critical(self, self.T['error'], self.T['invalid_index'])
        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['remove_failed']}\n\n{str(e)}")

    def reassign_orders(self):
        for idx, mount in enumerate(self.mounts):
            mount["order"] = idx
        self.save_config()

    def is_mounted(self, path):
        return os.path.ismount(path)

    def has_keyfile(self, entry):
        host_port = entry['url'][7:].split('/')[0]
        host = host_port.split(':')[0]
        port = host_port.split(':')[1] if ':' in host_port else '22'
        key_path = os.path.expanduser(f"~/.ssh/netmount_keys/id_rsa_{host}_{port}")
        return os.path.exists(key_path)

    def escape_url_for_protocol(self, url: str, proto: str) -> str:
        if proto == "ftp":
            return url.replace(' ', '%20')
        elif proto == "smb":
            return url.replace(' ', r'\040')
        return url

    def prettify(self, elem):
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        return '\n'.join([line for line in pretty.split('\n') if line.strip()])

    def regenerate_bookmarks_from_active_mounts(self):
        if not os.path.exists(XBEL_FILE):
            return

        tree = ET.parse(XBEL_FILE)
        root = tree.getroot()

        to_remove = []
        for bookmark in root.findall("bookmark"):
            title_elem = bookmark.find("title")
            if title_elem is not None and title_elem.text and title_elem.text.startswith("MNT-"):
                to_remove.append(bookmark)

        for bm in to_remove:
            root.remove(bm)

        for mount in sorted(self.mounts, key=lambda m: m.get("order", 0)):
            url = mount.get("url", "")
            path = mount.get("path", "")
            if self.is_mounted(path):
                title = path.split('/')[-1]
                full_title = "MNT-" + title
                unique_id = f"{int(time.time())}/0"

                bm = ET.Element("bookmark", href=f"file://{path}")
                ET.SubElement(bm, "title").text = full_title
                info = ET.SubElement(bm, "info")
                metadata = ET.SubElement(info, "metadata", owner="http://freedesktop.org")
                ET.SubElement(metadata, f"{{{BOOKMARK_NS}}}icon", name="folder")
                metadata_kde = ET.SubElement(info, "metadata", owner="http://www.kde.org")
                ET.SubElement(metadata_kde, "ID").text = unique_id
                ET.SubElement(metadata_kde, "isSystemItem").text = "false"
                ET.SubElement(bm, f"{{{BOOKMARK_NS}}}category").text = "mounts"
                ET.SubElement(bm, f"{{{BOOKMARK_NS}}}position").text = "0"

                root.append(bm)

        pretty_xml = self.prettify(root)
        with open(XBEL_FILE, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

    def mount_entry(self, entry):
        try:
            if not os.path.exists(entry['path']):
                if not self.run_with_sudo(["mkdir", "-p", entry['path']]):
                    self.refresh_with_loading()
                    return
        except Exception as e:
            QMessageBox.critical(self, self.T['error'], self.T['admin_error'].format(str(e)))
            self.refresh_with_loading()
            return

        uid = os.getuid()
        gid = os.getgid()

        try:
            if entry['url'].startswith("sftp://"):
                def do_sftp_mount():
                    QTimer.singleShot(100, self.refresh_with_loading)
                    remote = entry['url'][7:]
                    host_path = remote.split('/', 1)
                    host = host_path[0]
                    remote_path = '/' + host_path[1] if len(host_path) > 1 else ''

                    if ':' in host:
                        host, port = host.split(':', 1)
                    else:
                        port = '22'

                    key_path = os.path.expanduser(f"~/.ssh/netmount_keys/id_rsa_{host}_{port}")

                    try:
                        subprocess.run([
                            "sshfs", f"{entry['user']}@{host}:{remote_path}", entry['path'],
                            "-p", port,
                            "-o", f"IdentityFile={key_path},uid={uid},gid={gid},StrictHostKeyChecking=no"
                        ], check=True)
                    except Exception as e:
                        QMessageBox.critical(self, self.T['error'], f"{self.T['sftp_mount_failed']}\n\n{str(e)}")

                threading.Thread(target=do_sftp_mount, daemon=True).start()
                self.check_sftp_mount(entry['path'])
                return

            elif entry['url'].startswith("ftp://"):
                ftp_url = self.escape_url_for_protocol(entry['url'], "ftp")
                ftp_pass = entry['password']
                cmd = [
                    "curlftpfs", ftp_url, entry['path'], "-o",
                    f"user={entry['user']}:{ftp_pass},uid={uid},gid={gid}"
                ]

            elif entry['url'].startswith("smb://"):
                vers_opt = f",vers={entry['smb_version']}" if entry.get('smb_version') else ""
                unc = "//" + self.escape_url_for_protocol(entry['url'][6:], "smb")
                cmd = [
                    "mount", "-t", "cifs", unc, entry['path'], "-o",
                    f"username={entry['user']},password={entry['password']},uid={uid},gid={gid}{vers_opt}"
                ]

            else:
                QMessageBox.critical(self, self.T['error'], self.T['invalid_url'])
                return

            try:
                QTimer.singleShot(100, self.refresh_with_loading)
                if entry['url'].startswith("smb://"):
                    if not self.run_with_sudo(cmd):
                        QMessageBox.critical(self, self.T['error'], f"{self.T['admin_error']}\n{self.T['mount_failed']}")
                        return
                else:
                    subprocess.run(cmd, check=True)
            except Exception as e:
                QMessageBox.critical(self, self.T['error'], self.T['admin_error'].format(str(e)))
                return

            if self.is_mounted(entry['path']):
                QMessageBox.information(self, self.T['success'], self.T['mount_success'])
            else:
                QMessageBox.information(self, self.T['error'], self.T['unmount_success'])

            self.refresh_with_loading()
            self.regenerate_bookmarks_from_active_mounts()

        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['mount_failed']}\n\n{str(e)}")
            return


    def check_sftp_mount(self, path, attempt=0):
        try:
            if os.path.ismount(path):
                self.refresh_with_loading()
                QMessageBox.information(self, self.T['success'], self.T['add_success'])
            elif attempt < 5:
                QTimer.singleShot(600, lambda: self.check_sftp_mount(path, attempt + 1))
            else:
                self.refresh_with_loading()
                QMessageBox.critical(self, self.T['error'], self.T['add_failed'])
        except Exception as e:
            self.refresh_with_loading()
            QMessageBox.critical(self, self.T['error'], f"{self.T['add_failed']}\n\n{str(e)}")

    def create_autostart_service(self):
        try:
            expected_content = f"""[Desktop Entry]
Type=Application
Name={self.T['title']} - {self.T['automount']}
Exec=/usr/bin/python3 {AUTOMOUNT_EXEC}
Icon={icon_path}
Hidden=false
X-GNOME-Autostart-enabled=true
Comment={self.T['automount_comment']}
"""

            regenerate = True
            if os.path.exists(AUTOMOUNT_SCRIPT):
                with open(AUTOMOUNT_SCRIPT, "r", encoding="utf-8") as f:
                    existing = f.read()
                if existing.strip() == expected_content.strip():
                    regenerate = False

            if regenerate:
                os.makedirs(os.path.dirname(AUTOMOUNT_SCRIPT), exist_ok=True)
                with open(AUTOMOUNT_SCRIPT, 'w', encoding="utf-8") as f:
                    f.write(expected_content)

        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['autostart_write_failed']}\n\n{str(e)}")

    def create_smbunmount_service(self):
        try:
            expected_content = f"""[Desktop Entry]
Type=Application
Name={self.T['title']} - {self.T['autounmount']}
Exec=/usr/bin/python3 {SMBUNMOUNT_EXEC}
Icon={icon_path}
Hidden=false
X-GNOME-Autostart-enabled=true
Comment={self.T['autounmount_comment']}
"""

            regenerate = True
            if os.path.exists(SMBUNMOUNT_SCRIPT):
                with open(SMBUNMOUNT_SCRIPT, "r") as f:
                    existing = f.read()
                    if existing.strip() == expected_content.strip():
                        regenerate = False

            if regenerate:
                os.makedirs(os.path.dirname(SMBUNMOUNT_SCRIPT), exist_ok=True)
                with open(SMBUNMOUNT_SCRIPT, "w") as f:
                    f.write(expected_content)

        except Exception as e:
            QMessageBox.critical(self, self.T['error'], f"{self.T['smb_unmount_write_failed']}\n\n{str(e)}")

    def remove_oldsmbunmount_service(self):
        if os.path.exists(SMBUNMOUNT_SCRIPT_OLD):
            subprocess.run(["systemctl", "--user", "disable", "--now", "smb-unmount.service"], check=False)
            os.remove(SMBUNMOUNT_SCRIPT_OLD)
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)

class KeySetupWizard(QDialog):
    def __init__(self, entry, lang_data, parent=None):
        super().__init__(parent)
        self.manager = parent
        self.success = False
        self.setWindowTitle(lang_data['key_auth_required'])
        self.setModal(True)
        self.resize(600, 400)
        self.lang = lang_data
        self.entry = entry
        self.step = 0

        self.layout = QVBoxLayout()

        self.instructions = QTextEdit()
        self.instructions.setReadOnly(True)
        self.instructions.setStyleSheet("background-color: #1e1e1e; color: #ddd; padding: 10px;")
        self.instructions.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout.addWidget(self.instructions)

        btn_layout = QHBoxLayout()
        self.next_btn = QPushButton(self.lang['wizard_next'])
        self.next_btn.clicked.connect(self.next_step)
        self.close_btn = QPushButton(self.lang['wizard_close'])
        self.close_btn.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(self.next_btn)
        btn_layout.addWidget(self.close_btn)

        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)

        self.next_step()

    def next_step(self):
        self.step += 1
        if self.step == 1:
            self.instructions.append(self.lang['wizard_step1'])
            self.next_btn.setEnabled(False)

            ssh_dir = os.path.expanduser("~/.ssh/netmount_keys")
            os.makedirs(ssh_dir, exist_ok=True)

            host = self.entry['url'][7:].split('/')[0].split(':')[0]
            port = self.entry['url'][7:].split('/')[0].split(':')[1] if ':' in self.entry['url'] else '22'
            key_base = f"id_rsa_{host}_{port}"
            key_path = os.path.join(ssh_dir, key_base)
            pubkey_path = key_path + ".pub"

            self.key_path = key_path
            self.pubkey_path = pubkey_path

            if not Path(pubkey_path).exists():
                self.instructions.append(self.lang['wizard_generating'])
                QApplication.processEvents()()

                try:
                    subprocess.run([
                        "ssh-keygen", "-t", "rsa", "-b", "2048", "-f", key_path, "-N", ""
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.instructions.append(self.lang['wizard_generated'])
                except Exception as e:
                    self.instructions.append(f"[ERROR] {str(e)}")
                    self.next_btn.setEnabled(True)
                    return
            else:
                self.instructions.append(self.lang['wizard_already_exists'])

            self.next_btn.setEnabled(True)

        elif self.step == 2:
            self.instructions.append(self.lang['wizard_step2'])
            host = self.entry['url'][7:].split('/')[0].split(':')[0]

            host_port = self.entry['url'][7:].split('/')[0]
            host = host_port.split(':')[0]
            port = host_port.split(':')[1] if ':' in host_port else '22'

            user = self.entry["user"]
            pubkey_path = self.pubkey_path
            marker_file = os.path.expanduser("~/.netmount_result.tmp")

            if os.path.exists(marker_file):
                os.remove(marker_file)

            pw, ok = QInputDialog.getText(self, self.lang["password"], self.lang["password"], QLineEdit.EchoMode.Password)
            if not ok or not pw:
                self.instructions.append("[ABORTED] Nincs megadott jelszó.")
                return

            self.instructions.append(self.lang['wizard_copying'])
            QApplication.processEvents()

            with open(pubkey_path, 'r') as f:
                pubkey_content = f.read().strip().replace('"', r'\"')

            script_content = f"""#!/bin/bash
set -e

# 1. {self.lang['step1']}
sshpass -p {shlex.quote(pw)} ssh -p {port} -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=5 {user}@{host} "echo '{self.lang['step1_ok']}'" || exit 1

# 2. {self.lang['step2']}
sshpass -p {shlex.quote(pw)} ssh -p {port} -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no {user}@{host} "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{self.lang['step2_ok']}'" || exit 1

# 3. {self.lang['step3']}
sshpass -p {shlex.quote(pw)} scp -P {port} -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no {shlex.quote(pubkey_path)} {user}@{host}:/tmp/netmount_tmp_key.pub && echo '{self.lang['step3_ok']}' || exit 1

# 4. {self.lang['step4']}
sshpass -p {shlex.quote(pw)} ssh -p {port} -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no {user}@{host} '
    touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys &&
    grep -qxF "$(cat /tmp/netmount_tmp_key.pub)" ~/.ssh/authorized_keys || cat /tmp/netmount_tmp_key.pub >> ~/.ssh/authorized_keys;
    rm /tmp/netmount_tmp_key.pub
    echo "{self.lang['step4_ok']}"
' || exit 1

# 5. {self.lang['step5']}
echo "__OK__" > {marker_file}
"""

            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmpfile:
                    tmpfile.write(script_content)
                    tmpfile_path = tmpfile.name
                os.chmod(tmpfile_path, 0o700)
            except Exception as e:
                self.instructions.append(self.lang['wizard_tempfile_error'] + f"\n{str(e)}")
                self.next_btn.setEnabled(False)
                return

            os.chmod(tmpfile_path, 0o700)

            try:
                subprocess.Popen(["bash", tmpfile_path], stderr=subprocess.DEVNULL)
            except Exception as e:
                self.instructions.append(self.lang['wizard_script_start_error'] + f"\n{e}")
                return

            self._marker_timer_count = 0
            self._marker_timer_limit = 30
            self._marker_timer = QTimer(self)
            self._marker_timer.setInterval(1000)

            def check_marker_file():
                self._marker_timer_count += 1
                if os.path.exists(marker_file):
                    try:
                        with open(marker_file) as f:
                            if "__OK__" in f.read():
                                self.instructions.append(self.lang['wizard_success'])
                                self.success = True
                                self.entry['sshkeyvalid'] = True
                                self.manager.save_config()
                    except Exception as e:
                        self.instructions.append(self.lang['wizard_marker_read_error'] + f" {str(e)}")
                        self.success = False
                        self.entry['sshkeyvalid'] = False
                        self.manager.save_config()
                    finally:
                        self._marker_timer.stop()
                        try:
                            os.remove(marker_file)
                            os.remove(tmpfile_path)
                        except Exception:
                            pass
                    self.next_btn.setEnabled(False)
                    return

                if self._marker_timer_count >= self._marker_timer_limit:
                    self._marker_timer.stop()
                    self.instructions.append(self.lang['wizard_timeout_warn'])
                    self.success = False
                    self.entry['sshkeyvalid'] = False
                    self.manager.save_config()
                    try:
                        if os.path.exists(marker_file):
                            os.remove(marker_file)
                        os.remove(tmpfile_path)
                    except Exception:
                        pass
                    self.next_btn.setEnabled(False)

            self._marker_timer.timeout.connect(check_marker_file)
            self._marker_timer.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))
    window = MountManager()
    window.refresh_with_loading()
    window.show()
    sys.exit(app.exec())
