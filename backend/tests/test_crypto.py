"""crypto helpers: Fernet round-trip, MCP key format/hash."""

from app.crypto import decrypt_api_key, encrypt_api_key, generate_mcp_key, hash_mcp_key


def test_fernet_roundtrip() -> None:
    ct = encrypt_api_key("sk-provider-key-123")
    assert isinstance(ct, bytes)
    assert b"sk-provider-key-123" not in ct
    assert decrypt_api_key(ct) == "sk-provider-key-123"


def test_mcp_key_format() -> None:
    key = generate_mcp_key()
    assert key.startswith("mcp_")
    body = key[len("mcp_") :]
    assert len(body) == 43
    allowed = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    assert set(body) <= allowed


def test_mcp_key_uniqueness() -> None:
    keys = {generate_mcp_key() for _ in range(100)}
    assert len(keys) == 100


def test_mcp_key_hash_stable_and_not_reversible() -> None:
    key = generate_mcp_key()
    h = hash_mcp_key(key)
    assert h == hash_mcp_key(key)
    assert key not in h
    assert len(h) == 64
