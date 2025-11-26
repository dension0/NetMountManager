#!/usr/bin/env python3
import base64
import hashlib
import json
import fcntl
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Any

from netmount.config import SECURE_FILE

ITERATIONS = 100_000
ENCODING = "utf-8"

class LockedSecureFile:
    def __init__(self, file_path: Path, mode: str):
        self.file_path = file_path
        self.mode = mode
        self.file = None

    def __enter__(self):
        # Ensure parent exists before opening
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.file_path, self.mode)
        fcntl.flock(self.file.fileno(), fcntl.LOCK_EX)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            try:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self.file.close()
            except Exception:
                pass

def derive_key(password: str) -> bytes:
    salt = hashlib.md5(password.encode(ENCODING)).digest()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode(ENCODING)))

def encrypt(password: str, data: Any, file_path: Path = SECURE_FILE) -> None:
    key = derive_key(password)
    fernet = Fernet(key)
    json_data = json.dumps(data).encode(ENCODING)
    encrypted = fernet.encrypt(json_data)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with LockedSecureFile(file_path, "wb") as f:
        f.write(encrypted)

def decrypt(password: str, file_path: Path = SECURE_FILE) -> Any:
    if not file_path.exists():
        encrypt(password, [], file_path)
        return []

    try:
        if file_path.stat().st_size == 0:
            encrypt(password, [], file_path)
            return []
    except Exception:
        pass

    key = derive_key(password)
    fernet = Fernet(key)
    with LockedSecureFile(file_path, "rb") as f:
        ciphertext = f.read()

    if not ciphertext:
        encrypt(password, [], file_path)
        return []

    decrypted_data = fernet.decrypt(ciphertext)
    return json.loads(decrypted_data.decode(ENCODING))
