from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os
from pathlib import Path

class MessageEncryption:
    """AES-256 message encryption"""
    
    def __init__(self, password: bytes = None):
        if password is None:
            password = self._get_or_create_key()
        
        self.cipher = Fernet(self._derive_key(password))
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        key_file = Path('./data/encryption.key')
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        
        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        
        return key
    
    def _derive_key(self, password: bytes) -> bytes:
        """Derive encryption key from password"""
        if len(password) == 44:  # Already a Fernet key
            return password
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'nexremote_salt',  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt(self, data: str) -> bytes:
        """Encrypt string data"""
        return self.cipher.encrypt(data.encode('utf-8'))
    
    def decrypt(self, data: bytes) -> str:
        """Decrypt data to string"""
        return self.cipher.decrypt(data).decode('utf-8')