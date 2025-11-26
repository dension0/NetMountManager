# Changelog

## [v1.2.3] – 2025-11-26

### 🛠 Stabil indítás, biztonságos secure/bookmark kezelés és többnyelvű hibakezelés
🔐 Biztonságos secure fájl kezelés
    🆕 Ha a secure fájl nem létezik vagy 0 bájt, automatikusan létrejön titkosítva egy üres lista — az alkalmazás nem lép ki induláskor.
    ⚠️ InvalidToken (rossz jelszó / törött fájl) esetén felhasználói dialógus kérdez: lehetőség az üres secure fájl létrehozására — nincs csendes kilépés.

⚙️ Indítási stabilitás és hibajelzés
    🧰 Globális excepthook: minden nem kezelt kivétel konzolra íródik és részletes `QDialogban` jelenik meg (nem készítünk logfájlokat).
    🧷 Megtartja a főablak referenciáját (`app._main_window`), így a GC nem zárja be a GUI-t.
    ⏳ `LoadingDialog non-blocking` viselkedés + `after_load()` hibakezelés javítva; `traceback dialog` megjelenik szükség esetén.

📚 Könyvjelzők (XBEL) biztonságos mentése / visszaállítása
    🔁 Bookmark generálás és tisztítás logika bővítve — regenerálás az aktív csatolások alapján.
    🧩 Könyvjelző funkciók megerősítve: `add_place`, `remove_place`, `clean_mount_bookmarks`, `regenerate_bookmarks_from_active_mounts(mounts)`.

🌐 Többnyelvű (HU/EN) hibaüzenetek és nyelvi kulcsok
    🗂️ Nyelvi fájlok betöltése és többnyelvű hibaüzenetek beépítve (pl. `secure_corrupt_*`, `console_app_started`, `fatal_error_*`).
    ✏️ Apró elírások javítva (pl. `console_app_started`).

🖱️ Kisebb UI viselkedésjavítások
    💬 `QMessageBox` használata konzisztensen a felhasználóbarát hibajelzéshez.
    🔧 Automount / unmount folyamok és `refresh_with_loading` logika finomítva.

📝 Megjegyzés / javaslat
    ♻️ Többszörös bookmark-regenerálás kódrészletek több fájlban találhatók — javasolt refaktorálás egyetlen, központi `bookmarks.py` implementációra.

### 🛠 Robust startup, secure/bookmark safety and multilingual error handling
🔐 Secure file safety
    🆕 If the secure file is missing or zero-length, an encrypted empty list is created automatically so the app doesn't exit on startup.
    ⚠️ On InvalidToken (bad password / corrupt file) a user dialog asks whether to recreate an empty secure file — no silent quit.

⚙️ Startup stability and error reporting
    🧰 Global excepthook: unhandled exceptions are printed to stderr and shown in a detailed `QDialog` (no file-based logging).
    🧷 Keep a strong reference to the main window (`app._main_window`) to avoid GC closing the UI.
    ⏳ `LoadingDialog is non-blocking`; `after_load()` shows `trace dialog` when needed.

📚 Bookmarks (XBEL) safe save/load
    🔁 Bookmark generation and cleaning logic improved — regenerate from active mounts.
    🧩 Reinforced bookmarks module functions: `add_place`, `remove_place`, `clean_mount_bookmarks`, `regenerate_bookmarks_from_active_mounts(mounts)`.

🌐 Multilingual error messages and language keys
    🗂️ Language file loading and expanded keys (e.g. `secure_corrupt_*`, `console_app_started`, `fatal_error_*`).
    ✏️ Typo fixes (e.g. `console_app_started`).

🖱️ Small UI improvements
    💬 Use `QMessageBox` consistently for user-facing errors.
    🔧 Fine-tuned automount/unmount flows and `refresh_with_loading` logic.

📝 Note / suggestion
    ♻️ Duplicate bookmark-regeneration code exists in multiple files — recommend refactor to a single implementation in `bookmarks.py`.

## [v1.2.2] – 2025-11-26

### 🛠 Új funkciók & javítások
- ✅ Automatikus hiányzó Python-függőségek telepítése indításkor — az auto_mount.py elejére beépített ellenőrző blokk megpróbálja automatikusan telepíteni a szükséges csomagokat (pyqt6, cryptography) pip --user segítségével, ha hiányoznak.
- 🌐 Automatikus nyelvdetektálás (LC_ALL/LANG) — az üzeneteket a környezet nyelvéhez igazítja (magyar vagy angol).
- 💬 Kétnyelvű (HU/EN) felhasználói kommunikáció — a dialógusok és a terminál-fallback a felismert nyelven ad visszajelzést.
- 🧾 Nincs fájl-alapú logolás — a blokk nem ír log fájlba (nem használ /tmp-ot vagy más állandó fájlt), a kimenetet QDialog-on vagy megnyitott terminálon mutatja; ezzel elkerülve a rendszerszemét létrehozását.
- 🪟 QDialog pip kimenet stream — ha PyQt6 és grafikus környezet elérhető, egy felugró ablakban láthatod a pip futását élőben; siker esetén az ablak automatikusan bezárul, hiba esetén felhasználó bevatkozásig marad.
- 🖥️ Terminál-fallback — ha nincs PyQt6 vagy más ok miatt nem lehet GUI-t nyitni, a telepítést terminálablakban indítja, amely tartja magát, amíg megnézed a kimenetet.
- 🔒 Biztonsági viselkedés autostart alatt — ha rootként fut a script, nem próbál --user pip-et futtatni; a rendszercsomag (DNF) telepítést javasolja.
- ⏱️ Időbélyeg opció (GUI) — lehetőség időbélyegek megjelenítésére a QDialog kimenetében (datetime prefixelés soronként) — beépítve.
- 🧩 A fentiek biztonságosan integrálva az auto_mount.py indítólogikájába (importok előtt futó blokk), minimalizálva az autostart-környezetben fellépő problémákat.

### 🛠 New features & fixes
- ✅ Automatic installation of missing Python dependencies at startup — the check block added to the top of auto_mount.py will attempt to automatically install required packages (pyqt6, cryptography) using pip --user when they are missing.
- 🌐 Automatic language detection (LC_ALL/LANG) — messages are adapted to the environment language (Hungarian or English).
- 💬 Bilingual (HU/EN) user communication — dialogs and the terminal fallback present feedback in the detected language.
- 🧾 No file-based logging — the block does not write log files (does not use /tmp or any persistent file); output is shown in a QDialog or an opened terminal window, avoiding creating system clutter.
- 🪟 QDialog pip output stream — if PyQt6 and a graphical session are available, pip execution is streamed live into a popup window; on success the window closes automatically, on failure it remains until user intervention.
- 🖥️ Terminal fallback — if PyQt6 is unavailable or GUI cannot be opened, the installer runs in a terminal window which remains open so you can inspect the output.
- 🔒 Safe autostart behaviour — when the script runs as root, it will not attempt pip --user; it recommends installing system packages via DNF instead.
- ⏱️ Timestamp option (GUI) — optional per-line timestamps can be shown in the QDialog output (prefixed via datetime) — implemented.
- 🧩 The above is safely integrated into the auto_mount.py startup logic (the block runs before other imports), minimising issues in autostart environments.

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
- `v1.2.3` – Robust startup, secure/bookmark safety and multilingual error handling
- `v1.2.2` – Auto-installer, bilingual UX, no-file logging
- `v1.2.1` – Improvements and safer operation release
- `v1.2.0` – Feature release
- `v1.0.1` – Bugfix release
