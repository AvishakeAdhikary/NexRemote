import base64
import json

import pytest
from cryptography.exceptions import InvalidTag

from nexremote_server.protocol import legacy_crypto, v2_crypto
from nexremote_server.protocol.frames import (
    PSCR_FLAG_CONFIG,
    PSCR_FLAG_KEYFRAME,
    build_frame,
    build_phone_screen,
    parse_frame,
    parse_phone_screen,
)
from nexremote_server.protocol.jsonutil import dumps, get_int, get_str

# Produced with .NET System.Security.Cryptography.Aes, the WinUI host's implementation.
DOTNET_GOLDEN = {
    '{"type":"ping"}': "bga7c7UohXEfthnzoX4THg==",
    '{"type":"file_explorer","action":"drive_list"}': "SaRobwBGfE0CD1YoxWSfhnCpMYy1qpHGzi8zvPdpw9tgqY63URFMpu3w+1mh9VYk",
}


@pytest.mark.parametrize(("plain", "cipher"), DOTNET_GOLDEN.items())
def test_legacy_crypto_matches_dotnet_host(plain: str, cipher: str) -> None:
    assert legacy_crypto.encrypt_to_base64(plain) == cipher
    assert legacy_crypto.decrypt_from_base64(cipher) == plain


def test_legacy_crypto_round_trips_unicode() -> None:
    text = json.dumps({"type": "clipboard", "action": "set", "text": "héllo ✓ 你好"}, ensure_ascii=False)
    assert legacy_crypto.decrypt_from_base64(legacy_crypto.encrypt_to_base64(text)) == text


def _pair() -> tuple[v2_crypto.SessionCipher, v2_crypto.SessionCipher]:
    client_priv, client_pub = v2_crypto.generate_ephemeral()
    server_priv, server_pub = v2_crypto.generate_ephemeral()
    server_keys = v2_crypto.derive_keys(server_priv, client_pub, server_pub)
    client_keys = v2_crypto.derive_keys(client_priv, client_pub, server_pub)
    assert server_keys == client_keys
    return v2_crypto.SessionCipher.for_client(*client_keys), v2_crypto.SessionCipher.for_server(*server_keys)


def test_v2_round_trip_both_directions() -> None:
    client, server = _pair()
    for i in range(3):
        assert server.decrypt(client.encrypt(f"c2s {i}")) == f"c2s {i}"
        assert client.decrypt(server.encrypt(f"s2c {i}")) == f"s2c {i}"


def test_v2_rejects_replay_and_reorder() -> None:
    client, server = _pair()
    first, second = client.encrypt("one"), client.encrypt("two")
    with pytest.raises(InvalidTag):
        server.decrypt(second)  # out of order
    assert server.decrypt(first) == "one"
    assert server.decrypt(second) == "two"
    with pytest.raises(InvalidTag):
        server.decrypt(first)  # replay


def test_v2_directions_use_different_keys() -> None:
    client, _server = _pair()
    sealed = client.encrypt("hello")
    with pytest.raises(InvalidTag):
        client.decrypt(sealed)


def test_v2_known_answer_vector() -> None:
    """Fixed-key vectors (cross-checked with .NET AesGcm); the Kotlin SessionCrypto test reproduces them."""
    cipher = v2_crypto.SessionCipher(send_key=bytes(range(32)), recv_key=bytes(32))
    assert cipher.encrypt('{"type":"ping"}') == "dZ7Bp8VJoYcq2MBbfw7sx1qikhQ6HIzE88g+vhoMbA=="
    assert cipher.encrypt('{"type":"ping"}') == "bvTLhTSREiQsXjhXi4RHFKIoKnBBg/O4xhf9XmnRqg=="
    assert len(base64.b64decode("dZ7Bp8VJoYcq2MBbfw7sx1qikhQ6HIzE88g+vhoMbA==")) == 15 + 16


def test_frames() -> None:
    frame = build_frame(b"SCRN", 2, b"\xff\xd8jpeg")
    assert frame[:5] == b"SCRN\x02"
    assert parse_frame(frame) == (b"SCRN", 2, b"\xff\xd8jpeg")
    assert parse_frame(b"SCR") is None


def test_phone_screen_frames() -> None:
    data = build_phone_screen(0, PSCR_FLAG_CONFIG | PSCR_FLAG_KEYFRAME, 123_456_789, b"\x00\x00\x00\x01\x67")
    packet = parse_phone_screen(data)
    assert packet is not None
    assert packet.is_config and packet.is_keyframe
    assert packet.pts_us == 123_456_789
    assert packet.data == b"\x00\x00\x00\x01\x67"
    assert data[5:14] == bytes([3]) + (123_456_789).to_bytes(8, "big")
    assert parse_phone_screen(build_frame(b"SCRN", 0, b"x" * 20)) is None


def test_json_helpers_follow_legacy_semantics() -> None:
    assert dumps({"a": None, "b": [1, {"c": None}]}) == '{"b":[1,{}]}'
    assert get_str({"a": 5}, "a", "x") == "x"
    assert get_int({"a": True}, "a", 7) == 7
    assert get_int({"a": 2.6}, "a") == 3
