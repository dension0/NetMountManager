
```markdown
# 🌐 NetMountManager
```
[🇬🇧 English](README_EN.md) | 🇭🇺 Magyar nyelvű leírás

---

**NetMountManager** egy biztonságos, grafikus hálózati meghajtókezelő Linuxra, amely támogatja az SMB, SFTP és FTP csatolásokat, jelszavas vagy kulcsalapú hitelesítéssel. A rendszer automatikus csatolást és elérhetetlenség esetén leválasztást is biztosít.

---

## ⚙️ Főbb funkciók

- ✅ Hálózati meghajtók csatolása GUI-ból (SMB, SFTP, FTP)
- 🎛️ Teljes KDE grafikus kezelőfelület
- 🔐 Teljesen titkosított konfiguráció (Fernet + jelszó)
- 💾 Menthető és betölthető konfiguráció (importáláshoz jelszó szükséges)
- 🔑 Jelszavas hitelesítés (SMB, FTP) vagy kulcsalapú hitelesítés (SFTP)
- 💻 Automatikus csatolás rendszerinduláskor
- 🔁 Daemon figyeli és leválasztja az elérhetetlenné vált SMB mountokat *(pl. hálózatváltás esetén)*
- 🌍 Többnyelvű támogatás *(jelenleg magyar és angol)*
- 🧽 KDE könyvjelzők automatikus létrehozása, eltávolítása és karbantartása minden csatolt meghajtóhoz

> 🔧 A program **teljeskörűen tesztelve** a **Nobara KDE** disztribúción, erre optimalizálva.

---

## 📁 Projekt struktúra
```bash
NetMountManager/
├── netmount/             # 🧠 Fő Python modulcsomag
│ ├── main.py             # GUI indító
│ ├── mountmanager.py     # GUI logika
│ ├── auto_mount.py       # Automount script
│ ├── net_unmounter.py    # Unmount daemon
│ ├── decryptor.py        # Fernet titkosítás
│ ├── config.py           # Konfigurációs utak
│ ├── bookmarks.py        # KDE XBEL kezelés
│ ├── password_prompt.py  # Egységes jelszóbekérő
│ └── utils/xml_utils.py  # XBEL segédfüggvények
│
├── lang/                 # 🌍 Lokalizációk
│ ├── main.json
│ ├── auto_mount.json
│ └── net_unmounter.json
│
├── icons/
│ └── netmount_icon.png
│
├── data/
│ └── .net_mounts.secure  # 🔐 Titkosított konfiguráció
│
├── install.py            # Telepítő script
├── uninstall.py          # Eltávolító script
├── LICENSE
├── README.md
├── README_HU.md          # Magyar Olvassel
└── README_EN.md          # Angol Olvassel
```
---

## 🚀 Telepítés

Futtasd a következőket:

```bash
sudo dnf install python3-pyqt6 sshfs curlftpfs cifs-utils sshpass fuse-sshfs curlftpfs git
```

### 1 opció : GitHub Releases (ZIP)

1. Nyisd meg a [kiadások oldalát](https://github.com/dension0/NetMountManager/releases/latest)
2. Töltsd le az **Assets** szekcióban a `Source code (zip)` fájlt
3. Csomagold ki a saját mappádba (pl. `/home/janos/NetMountManager/`)
4. Run:
```bash
cd ~/NetMountManager
```
```bash
python3 install.py
```
### 2. opció: Git klónozással
```bash
git clone https://github.com/dension0/NetMountManager.git ~/NetMountManager
```
```bash
cd ~/NetMountManager
```
```bash
python3 install.py
```

Ez végrehajtja:

a szükséges csomagok telepítését (PyQt6, cryptography)

létrehozza a .desktop parancsikont a menübe

a GUI első indításakor a háttérszolgáltatások automatikusan aktiválódnak:
```bash
~/.config/autostart/net-automounts.desktop
```
```bash
~/.config/systemd/user/smb-unmount.service
```

⚠️ A program adminisztrátori jelszót kérhet a titkosítási műveletekhez és a csatolásokhoz (pl. SMB esetén mount).

---

## ❌ Eltávolítás
Futtasd a következőt:
```bash
python3 ~/NetMountManager/uninstall.py
```
Ez eltávolítja:

a parancsikont a menüből

az automatikus csatolás indítóját

a háttérdaemon systemd szolgáltatását

⚠️ A titkosított konfiguráció (.net_mounts.secure) nem kerül automatikusan törlésre.

---

## 🛠️ Kézi csomag eltávolítás (opcionális)
A NetMountManager futtatásához használt csomagok:

pip uninstall pyqt6 cryptography

Csak akkor használd, ha biztos vagy benne, hogy más nem használja őket.

---

## 📥 Csatolási fájl export / import
A beállítások exportálhatók titkosított .secure fájlba

A fájl importáláskor jelszót kér a dekódoláshoz

A meglévő bejegyzésekkel automatikusan egyesíti az újakat (kérdéses duplikációk esetén döntés kérve)

---

## 🔐 Titkosítási rendszer
Fernet titkosítás (AES 128 GCM)

A kulcs deriválása: PBKDF2HMAC (SHA256, 100000 iteráció)

A salt: az admin jelszó MD5 hash-e

A titkosított fájl: data/.net_mounts.secure

---

## 👤 Szerző
Készült: Madarász László (@dension)
Támogatás, hibabejelentés: info@pixellegion.org
Weboldal: https://pixellegion.org
Powered by: ChatGPT
Weboldal: https://chatgpt.com

---

## 📃 Licenc
Ez a projekt szabadon felhasználható, módosítható és terjeszthető a MIT licenc alapján.
