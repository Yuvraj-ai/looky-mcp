"""Crypto helpers — Fernet encryption for Vision API keys, SHA-256 hashing for
MCP keys (Architecture §20; MCP-key decision from decisions.md 2026-09-10)."""

import hashlib
import secrets

from cryptography.fernet import Fernet

from app.config import settings


def encrypt_api_key(plaintext: str) -> bytes:
    return Fernet(settings.VISION_ENCRYPTION_KEY.encode()).encrypt(plaintext.encode())


def decrypt_api_key(ciphertext: bytes) -> str:
    return Fernet(settings.VISION_ENCRYPTION_KEY.encode()).decrypt(ciphertext).decode()


# --- MCP keys: mcp_ + base62 of 32 random bytes; only SHA-256 hash stored ---

_B62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def generate_mcp_key() -> str:
    raw = bytearray(secrets.token_bytes(32))
    value = int.from_bytes(raw, "big")
    chars = []
    while value:
        value, rem = divmod(value, 62)
        chars.append(_B62_ALPHABET[rem])
    key = "mcp_" + "".join(reversed(chars)).ljust(43, "0")
    return key


def hash_mcp_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
