from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
from utils.logger import get_logger

logger = get_logger(__name__)

class MessageEncryption:
    """AES-256 message encryption matching mobile app"""
    
    def __init__(self):
        # Must match the mobile app's key EXACTLY
        # Mobile uses: Key.fromUtf8('nexremote_encryption_key_32chars')
        # This is 33 characters, but the encrypt package truncates to 32 bytes for AES256
        key_str = 'nexremote_encryption_key_32chars'
        self.key = key_str.encode('utf-8')[:32]  # Take exactly first 32 bytes
        
        # IV must match mobile app exactly
        # Mobile uses: IV.fromLength(16) which creates 16 zero bytes
        self.iv = bytes(16)
        
        self.backend = default_backend()
        
        # Debug: Log key and IV info
        logger.info(f"Encryption initialized - Key length: {len(self.key)} bytes, IV length: {len(self.iv)} bytes")
        logger.info(f"Key (hex): {self.key.hex()}")
        logger.info(f"IV (hex): {self.iv.hex()}")
    
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
                # It's a base64 string - decode it first
                logger.info(f"Input is string (base64), length: {len(data)}")
                encrypted_data = base64.b64decode(data)
            elif isinstance(data, bytes):
                # It might be base64 encoded bytes or raw bytes
                try:
                    # Try to decode as UTF-8 string first (likely base64 string as bytes)
                    data_str = data.decode('utf-8').strip()
                    logger.info(f"Input is bytes, decoded to UTF-8 string, length: {len(data_str)}")
                    encrypted_data = base64.b64decode(data_str)
                except UnicodeDecodeError:
                    # It's raw encrypted bytes
                    logger.info("Input is raw encrypted bytes")
                    encrypted_data = data
            else:
                raise ValueError(f"Unexpected data type: {type(data)}")
            
            logger.info(f"Encrypted data length after base64 decode: {len(encrypted_data)} bytes")
            logger.info(f"Encrypted data (hex, first 32 bytes): {encrypted_data[:32].hex()}")
            
            # Decrypt
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(self.iv),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
            
            logger.info(f"Decrypted padded data length: {len(decrypted_padded)} bytes")
            logger.info(f"Last 16 bytes (padding, hex): {decrypted_padded[-16:].hex()}")
            
            # Unpad
            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            
            # Decode to string
            result = decrypted.decode('utf-8')
            logger.info(f"Successfully decrypted message, length: {len(result)} chars")
            logger.debug(f"Decrypted content: {result[:200]}")
            return result
            
        except Exception as e:
            logger.error(f"Decryption failed at step: {type(e).__name__}: {e}", exc_info=True)
            raise