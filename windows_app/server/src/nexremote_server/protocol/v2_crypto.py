"""Protocol v2 session encryption (negotiated, additive).

Handshake:
  client `auth` adds        {"protocol_version": 2, "client_ephemeral_key": <b64 SPKI P-256>}
  host `auth_success` adds  {"protocol_version": 2, "server_ephemeral_key": <b64 SPKI P-256>,
                             "session_crypto": "aes-256-gcm"}

Key schedule (both sides):
  shared  = ECDH(P-256)
  salt    = SHA-256(client_ephemeral_spki || server_ephemeral_spki)
  k_c2s   = HKDF-SHA256(shared, salt, info=b"nexremote/v2/c2s", 32)
  k_s2c   = HKDF-SHA256(shared, salt, info=b"nexremote/v2/s2c", 32)

Each direction keeps a 64-bit message counter that starts at 0. The nonce is 4 zero bytes
followed by the counter as 8 big-endian bytes. Wire text is Base64(ciphertext || 16-byte tag),
with no associated data. Plaintext `ping`/`pong` frames sit outside the counter sequence.

This file and client/.../core/network/SessionCrypto.kt must behave identically.
"""

from __future__ import annotations

import base64
import hashlib
import threading

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

SESSION_CRYPTO = "aes-256-gcm"
INFO_C2S = b"nexremote/v2/c2s"
INFO_S2C = b"nexremote/v2/s2c"


def _spki(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def generate_ephemeral() -> tuple[ec.EllipticCurvePrivateKey, str]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, base64.b64encode(_spki(private_key)).decode("ascii")


def derive_keys(
    private_key: ec.EllipticCurvePrivateKey, client_spki_b64: str, server_spki_b64: str
) -> tuple[bytes, bytes]:
    """Return (k_c2s, k_s2c). Works from either side; `private_key` is the caller's own."""
    client_spki = base64.b64decode(client_spki_b64)
    server_spki = base64.b64decode(server_spki_b64)
    peer_spki = client_spki if _spki(private_key) == server_spki else server_spki
    peer = serialization.load_der_public_key(peer_spki)
    if not isinstance(peer, ec.EllipticCurvePublicKey) or not isinstance(peer.curve, ec.SECP256R1):
        raise ValueError("peer ephemeral key must be P-256")
    shared = private_key.exchange(ec.ECDH(), peer)
    salt = hashlib.sha256(client_spki + server_spki).digest()

    def expand(info: bytes) -> bytes:
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info).derive(shared)

    return expand(INFO_C2S), expand(INFO_S2C)


def _nonce(counter: int) -> bytes:
    return bytes(4) + counter.to_bytes(8, "big")


class SessionCipher:
    """Directional AES-GCM cipher: `send_key` encrypts outbound, `recv_key` decrypts inbound."""

    name = "v2"

    def __init__(self, send_key: bytes, recv_key: bytes) -> None:
        self._send = AESGCM(send_key)
        self._recv = AESGCM(recv_key)
        self._send_counter = 0
        self._recv_counter = 0
        self._lock = threading.Lock()

    @classmethod
    def for_server(cls, k_c2s: bytes, k_s2c: bytes) -> SessionCipher:
        return cls(send_key=k_s2c, recv_key=k_c2s)

    @classmethod
    def for_client(cls, k_c2s: bytes, k_s2c: bytes) -> SessionCipher:
        return cls(send_key=k_c2s, recv_key=k_s2c)

    def encrypt(self, plaintext: str) -> str:
        # Encrypt under the lock so the nonce order matches the order frames are produced.
        with self._lock:
            nonce = _nonce(self._send_counter)
            self._send_counter += 1
            sealed = self._send.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(sealed).decode("ascii")

    def decrypt(self, payload: str) -> str:
        raw = base64.b64decode(payload.strip(), validate=True)
        with self._lock:
            plaintext = self._recv.decrypt(_nonce(self._recv_counter), raw, None)
            self._recv_counter += 1
        return plaintext.decode("utf-8")
