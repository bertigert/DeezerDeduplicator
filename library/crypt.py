import json
import logging

from cryptography.fernet import Fernet

HARDCODED_KEY = b"sb-B6Yp8iWp2LigLomglLtoB9pe5JnVgdWTaVqoGF10="

def get_encryption_key() -> bytes:
    """
    Returns:
        bytes: the encryption key for cookies.
    """
    return HARDCODED_KEY

def encrypt_cookies(cookies: dict, key: bytes) -> bytes:
    """
    Encrypts the cookies dictionary using the provided key.
    Args:
        cookies (dict): Dictionary of cookies to encrypt in aiohttp format
        key (bytes): Encryption key
    Returns:
        bytes: Encrypted cookies as bytes
    """
    f = Fernet(key)
    return f.encrypt(json.dumps(cookies).encode())

def decrypt_cookies(encrypted: bytes, key: bytes) -> dict:
    """
    Decrypts the encrypted cookies using the provided key.
    Args:
        encrypted (bytes): Encrypted cookies as bytes
        key (bytes): Encryption key
    Returns:
        dict: Decrypted cookies as a dictionary, or None if decryption fails
    """
    f = Fernet(key)
    try:
        data = json.loads(f.decrypt(encrypted).decode())
        return data
    except Exception as e:
        logging.debug(f"Decryption failed: {e}")
        return None 