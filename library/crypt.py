import json
from cryptography.fernet import Fernet
import logging

HARDCODED_KEY = b'sb-B6Yp8iWp2LigLomglLtoB9pe5JnVgdWTaVqoGF10='

def get_encryption_key() -> bytes:
    """
    Returns:
        bytes: the encryption key for cookies.
    """
    return HARDCODED_KEY

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