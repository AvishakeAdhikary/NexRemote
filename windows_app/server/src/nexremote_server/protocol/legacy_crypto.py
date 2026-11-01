"""Protocol v1 message encryption.

AES-256-CBC with PKCS7 padding, a fixed key and an all-zero IV, carried as Base64 text.
The original release defined it this way, and it is weak. It is kept byte-for-byte so
clients already in the field keep working. Newer clients negotiate v2 (see v2_crypto.py).
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_KEY = b"nexremote_encryption_key_32chars".ljust(32, b"\0")[:32]
_IV = bytes(16)


def encrypt_to_base64(plaintext: str) -> str:
    padder = padding.PKCS7(128).padder()
    data = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(_KEY), modes.CBC(_IV)).encryptor()
    return base64.b64encode(encryptor.update(data) + encryptor.finalize()).decode("ascii")


def decrypt_from_base64(payload: str) -> str:
    raw = base64.b64decode(payload.strip(), validate=True)
    decryptor = Cipher(algorithms.AES(_KEY), modes.CBC(_IV)).decryptor()
    padded = decryptor.update(raw) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")


class LegacyCipher:
    name = "legacy"

    def encrypt(self, plaintext: str) -> str:
        return encrypt_to_base64(plaintext)

    def decrypt(self, payload: str) -> str:
        return decrypt_from_base64(payload)
