from pathlib import Path
import os
import xml.etree.ElementTree as ET

# 📁 Alapkönyvtár
BASE_DIR = Path.home() / "NetMountManager"

# 📂 Adat- és konfigurációs könyvtárak
DATA_DIR = BASE_DIR / "data"
LANG_DIR = BASE_DIR / "lang"
ICON_DIR = BASE_DIR / "icons"
BIN_DIR = BASE_DIR / "bin"
SHARE_DIR = BASE_DIR / "share/applications"

# 📄 Ikon és nyelvi fájlok
icon_path = ICON_DIR / "netmount_icon.png"
lang_file = LANG_DIR / "main.json"
lang_file_am = LANG_DIR / "auto_mount.json"
lang_file_un = LANG_DIR / "net_unmounter.json"

# 🗂️ Konfigurációs fájl
SECURE_FILE = DATA_DIR / ".net_mounts.secure"

# 📄 XBEL könyvjelzők (KDE)
XBEL_FILE = Path.home() / ".local/share/user-places.xbel"
BOOKMARK_NS = "http://www.freedesktop.org/standards/desktop-bookmarks"
ET.register_namespace("bookmark", BOOKMARK_NS)

# 🚀 Automatikus indulási fájlok
AUTOMOUNT_SCRIPT = Path.home() / ".config/autostart/net-automounts.desktop"
AUTOMOUNT_EXEC = BASE_DIR / "netmount/auto_mount.py"
SMBUNMOUNT_SCRIPT = Path.home() / ".config/systemd/user/smb-unmount.service"
SMBUNMOUNT_EXEC = BASE_DIR / "netmount/net_unmounter.py"

# 💡 Egyéb
home_dir = str(Path.home())
