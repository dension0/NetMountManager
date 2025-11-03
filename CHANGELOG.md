# Changelog

## [v1.2.1] – 2025-11-03

### 🛠 Fejlesztések és biztonságosabb működés
- Új `_connection_details()` segédfüggvény a host, port és user kinyerésére, IPv6-címek biztonságos idézőjelezésével  
- A kulcstelepítő script generálása egységes SSH/SCP parancs idézőjelezést kapott  
- A varázsló hibakezelése javítva: hiba esetén visszalép a megfelelő lépésre  
- Új magyar és angol hibaüzenetek az érvénytelen SFTP-címek és a hiányzó felhasználónév kezeléséhez  

### 🛠 Improvements and safer operation
- Added new `_connection_details()` helper function to extract host, port, and user from URLs, with proper quoting for IPv6 addresses  
- Key installer script generation now applies consistent quoting for all SSH/SCP commands  
- Wizard error handling improved — on failure, it now correctly reverts to the appropriate step  
- Added new English and Hungarian error messages for invalid SFTP URLs and missing usernames 

## [v1.2.0] – 2025-07-07

### 🇭🇺 Funkcióbővítő kiadás – NetMountManager

- 🧩 Hozzáadva **sorrendezés lehetősége** a csatolási listához (drag & drop)
- 🗂️ Minden csatolás mostantól tartalmaz `order` mezőt, amely mentésre kerül
- 🔁 A lista és az XBEL könyvjelzők automatikusan **frissülnek a sorrend alapján**
- 🧹 Egyszerűsített logika az aktív mountokból generált KDE könyvjelzőkhöz
- 🎨 GUI finomítás: gombok átrendezve, új színek és margók
- 🔎 Listaelemeken megjelenik a csatolási sorrend száma is
- 📋 Részletesebb hibakezelés és **megerősítő ablakok törlés előtt**
- 🔄 Újratervezett **SMB háttérfigyelő**, ami automatikusan leválasztja a "ZOMBI" megosztásokat
- 🧲 Kivezetve a `systemd` használata – tálcaikonnal indul, naplóablak elérhető
- 🔁 SMB őr **GUI-ból indítható/leállítható**, élő állapotfigyeléssel

---

### 🇬🇧 Feature Release – NetMountManager

- 🧩 Added **sortable mount list** with drag & drop reordering
- 🗂️ Each mount now stores a persistent `order` field
- 🔁 List view and XBEL bookmarks auto-refresh based on defined order
- 🧹 Simplified logic for generating KDE bookmarks from active mounts
- 🎨 GUI refinements: rearranged buttons, cleaner layout and styling
- 🔎 Mount entries now show their order index explicitly
- 📋 Improved error handling and **confirmation dialogs before removal**
- 🔄 Redesigned **SMB background monitor** to auto-unmount "ZOMBIE" shares
- 🧲 Removed `systemd` dependency – tray icon launcher with log window
- 🔁 SMB watcher can be **started/stopped from GUI**, with real-time status

---

## [v1.0.1] – 2025-07-06

### 🇭🇺 Hibajavító kiadás

🔧 Javítások:

- 🐛 Kijavítva a `NameError`, amelyet a hiányzó `log()` függvény okozott a `password_prompt.py` fájlban  
- 🐛 Az `auto_mount.py` és `net_unmounter.py` mostantól explicit módon továbbadják a `log()` függvényt az `ask_admin_password()` hívásban
- 🐛 Megszüntetve az esetleges dupla betöltési ablak a GUI induláskor

---

### 🇬🇧 Bugfix Release

🔧 What’s fixed:

- 🐛 Fixed `NameError` caused by missing `log()` definition in `password_prompt.py` (used by `auto_mount.py` and `net_unmounter.py`)
- 🐛 `auto_mount.py` and `net_unmounter.py` now explicitly pass the `log()` function to `ask_admin_password()` for consistent logging
- 🐛 Prevented possible double-loading screen on GUI startup

---

### 📦 Versions
- `v1.2.1` – Improvements and safer operation release
- `v1.2.0` – Feature release
- `v1.0.1` – Bugfix release
