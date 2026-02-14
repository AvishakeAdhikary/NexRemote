from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64

class MessageEncryption:
    """AES-256 message encryption matching mobile app"""
    
    def __init__(self):
        # Must match the mobile app's key exactly
        # Mobile uses: 'nexremote_encryption_key_32chars'
        key_str = 'nexremote_encryption_key_32chars'
        self.key = key_str.encode('utf-8')[:32]  # AES-256 needs 32 bytes
        
        # IV must match mobile app (16 zeros)
        self.iv = bytes(16)  # Mobile uses IV.fromLength(16) which is 16 zero bytes
        
        self.backend = default_backend()
    
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
                # If it's already a string, it's the base64 encoded data
                encrypted_data = base64.b64decode(data)
            elif isinstance(data, bytes):
                # If bytes, check if it needs base64 decoding
                try:
                    # Try to decode as UTF-8 first (websocket might send as UTF-8 bytes)
                    data_str = data.decode('utf-8').strip()
                    encrypted_data = base64.b64decode(data_str)
                except:
                    # Maybe it's already raw bytes
                    encrypted_data = base64.b64decode(data)
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
            
            # Decode to string and strip any null bytes or whitespace
            result = decrypted.decode('utf-8').strip('\x00').strip()
            return result
        except Exception as e:
            # If decryption fails, try to return as plain text
            # This handles cases where data might not be encrypted (like auth)
            try:
                if isinstance(data, bytes):
                    return data.decode('utf-8').strip()
                return str(data).strip()
            except:
                raise e