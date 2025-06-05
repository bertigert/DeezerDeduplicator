import json
from pathlib import Path
from cryptography.fernet import Fernet
import logging

def get_encryption_key(key_file: str = "cookie.key") -> bytes:
    """
    Loads or generates a key for encryption.
    """
    key_path = Path(__file__).parent.parent/key_file
    if not key_path.exists():
        key = Fernet.generate_key()
        key_path.write_bytes(key)
    else:
        key = key_path.read_bytes()
    return key

def encrypt_cookies(cookies: dict, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(json.dumps(cookies).encode())

def decrypt_cookies(encrypted: bytes, key: bytes) -> dict:
    f = Fernet(key)
    try:
        data = json.loads(f.decrypt(encrypted).decode())
        return data
    except Exception as e:
        logging.debug(f"Decryption failed: {e}")
        return None 