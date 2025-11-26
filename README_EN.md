```markdown
# 🌐 NetMountManager
```
🇬🇧 English Description | [🇭🇺 Magyar](README_HU.md)

---

NetMountManager is a secure graphical network mount manager for Linux that supports mounting SMB, SFTP, and FTP shares with either password-based or key-based authentication. It also offers automatic mounting and auto-unmounting for unreachable connections.

---

## ⚙️ Key Features

- ✅ Mount network shares via a GUI (SMB, SFTP, FTP)
- 🎛️ Full KDE graphical interface integration
- 🔐 Fully encrypted configuration (Fernet + password)
- 💾 Configurations can be saved/exported and imported (password required for import)
- 🔑 Password-based authentication (SMB, FTP) or key-based authentication (SFTP)
- 💻 Automatic mounting at system startup
- 🔁 Background daemon detects and unmounts unreachable SMB mounts (e.g. on network change)
- 🌍 Multilingual support (currently Hungarian and English)
- 🧽 Automatic creation, removal and maintenance of KDE bookmarks for all mounted shares
- 🔧 Fully tested on Nobara KDE – optimized for this distribution.

---

## 📁 Project Structure
```bash
NetMountManager/
├── netmount/               # 🧠 Main Python package
│   ├── main.py             # GUI entry point
│   ├── mountmanager.py     # GUI logic
│   ├── auto_mount.py       # Automount script
│   ├── net_unmounter.py    # Unmount daemon
│   ├── decryptor.py        # Fernet encryption
│   ├── config.py           # Path & config management
│   ├── bookmarks.py        # KDE XBEL bookmark handler
│   ├── password_prompt.py  # Central password prompt logic
│   └── utils/xml_utils.py  # XBEL helper functions
│
├── lang/                   # 🌍 Localization
│   ├── main.json
│   ├── auto_mount.json
│   └── net_unmounter.json
│
├── icons/
│   └── netmount_icon.png
│
├── data/
│   └── .net_mounts.secure  # 🔐 Encrypted configuration
│
├── install.py              # Installer script
├── uninstall.py            # Uninstaller script
├── LICENSE
├── README.md
├── README_HU.md            # Hungarian readme
└── README_EN.md            # English readme
```
---

## 🚀 Installation

Run the following:
```bash
sudo dnf install python3-pyqt6 sshfs curlftpfs cifs-utils sshpass fuse-sshfs curlftpfs git
```
This installs the necessary system packages (if not already present).

### Option 1: From GitHub Releases (ZIP)

1. Visit the [Releases page](https://github.com/dension0/NetMountManager/releases/latest)
2. Download the file `Source code (zip)` under **Assets**
3. Extract the ZIP to your home directory (e.g. `/home/username/NetMountManager/`)
4. Run:
```bash
cd ~/NetMountManager
```
```bash
python3 install.py
```
### Option 2: Clone via Git
```bash
git clone https://github.com/dension0/NetMountManager.git ~/NetMountManager
```
```bash
cd ~/NetMountManager
```
```bash
python3 install.py
```
This will:

Install required Python packages (PyQt6, cryptography)

Create a .desktop launcher in your application menu

Set up background services that activate automatically on first launch:
```bash
~/.config/autostart/net-automounts.desktop
```
```bash
~/.config/systemd/user/smb-unmount.service
```

⚠️ Admin password may be requested for encryption and mount operations (e.g. mounting SMB shares).

---

## ❌ Uninstallation

Run:
```bash
python3 ~/NetMountManager/uninstall.py
```
This will:

Remove the application menu entry

Remove the autostart desktop file

Disable and remove the background unmounting daemon (systemd user service)

⚠️ The encrypted config file (.net_mounts.secure) is not deleted automatically.

---

## 🛠️ Optional Python Package Removal
These packages are used by NetMountManager:

pip uninstall pyqt6 cryptography

Only use this if you're sure no other tools depend on them.

---

## 📥 Export / Import Configuration
You can export your configuration to a .secure encrypted file.

On import, you must enter the password used during encryption.

Imported entries are automatically merged with existing ones (duplicates will prompt for replacement).

---

## 🔐 Encryption System
Fernet encryption (AES 128 GCM)

Key derivation: PBKDF2HMAC (SHA256, 100,000 iterations)

Salt is derived from the MD5 hash of the admin password

Encrypted configuration stored at: data/.net_mounts.secure

---

## 👤 Author
Developed by: Madarász László (@dension)
Support / Issues: info@volthost.hu
Website: https://volthost.hu
Powered by: ChatGPT
https://chatgpt.com

---

## 📃 License
This project is licensed under the MIT License — feel free to use, modify, and distribute it.
