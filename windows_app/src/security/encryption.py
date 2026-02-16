from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
from utils.logger import get_logger

logger = get_logger(__name__)

class MessageEncryption:
    """AES-256-CBC message encryption matching mobile app"""
    
    def __init__(self):
        # Must match the mobile app's key EXACTLY
        # The string is 31 ASCII chars — pad with \0 to 32 bytes to match Flutter's Key.fromUtf8
        key_str = 'nexremote_encryption_key_32chars'
        self.key = key_str.encode('utf-8').ljust(32, b'\x00')
        
        # IV: 16 zero bytes (matches mobile app)
        self.iv = bytes(16)
        
        self.backend = default_backend()
        logger.info("Encryption initialized")
    
    def encrypt(self, data: str) -> bytes:
        """Encrypt string data to base64 bytes"""
        # Pad data to block size
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data.encode('utf-8')) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(self.iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return as base64 encoded bytes
        return base64.b64encode(encrypted)
    
    def decrypt(self, data) -> str:
        """Decrypt base64 string/bytes to string"""
        try:
            # Handle different input types from websocket
            if isinstance(data, str):
                encrypted_data = base64.b64decode(data)
            elif isinstance(data, bytes):
                try:
                    data_str = data.decode('utf-8').strip()
                    encrypted_data = base64.b64decode(data_str)
                except UnicodeDecodeError:
                    encrypted_data = data
            else:
                raise ValueError(f"Unexpected data type: {type(data)}")
            
            # Decrypt
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(self.iv),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Unpad
            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {type(e).__name__}: {e}")
            raise