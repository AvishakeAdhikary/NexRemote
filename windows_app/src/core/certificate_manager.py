"""
Certificate Manager
Handles SSL/TLS certificate generation and validation
"""
import ipaddress
import ssl
import os
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)

class CertificateManager:
    """Manage SSL certificates for secure connections"""
    
    def __init__(self, config):
        self.config = config
        self.cert_dir = Path(config.get('data_dir', '.')) / 'certs'
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
        self.cert_file = self.cert_dir / 'server.crt'
        self.key_file = self.cert_dir / 'server.key'
    
    def get_ssl_context(self) -> ssl.SSLContext:
        """Get or create SSL context"""
        # Ensure certificate exists
        if not self.cert_file.exists() or not self.key_file.exists():
            self.generate_certificate()
        
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.cert_file), str(self.key_file))
        
        # Security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # Client cert validation handled separately
        
        return context
    
    def generate_certificate(self):
        """Generate self-signed certificate"""
        try:
            logger.info("Generating new SSL certificate...")
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Build certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NeuralNexusStudios"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365 * 10)  # 10 years
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    # x509.IPAddress("127.0.0.1"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1"))
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Write certificate
            with open(self.cert_file, 'wb') as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            with open(self.key_file, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            logger.info("SSL certificate generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to generate certificate: {e}", exc_info=True)
            raise
    
    def get_certificate_fingerprint(self) -> str:
        """Get certificate SHA-256 fingerprint for verification"""
        try:
            with open(self.cert_file, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data)
            fingerprint = cert.fingerprint(hashes.SHA256())
            
            return fingerprint.hex()
            
        except Exception as e:
            logger.error(f"Failed to get certificate fingerprint: {e}")
            return ""
    
    def validate_client_certificate(self, cert_data: bytes) -> bool:
        """Validate client certificate"""
        try:
            # Load and validate client certificate
            cert = x509.load_pem_x509_certificate(cert_data)
            
            # Check expiration
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                logger.warning("Client certificate expired or not yet valid")
                return False
            
            # Additional validation can be added here
            # (e.g., check against trusted certificates, revocation list, etc.)
            
            return True
            
        except Exception as e:
            logger.error(f"Certificate validation failed: {e}")
            return False