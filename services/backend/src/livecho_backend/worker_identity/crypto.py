"""Enrollment verifiers and RFC 8032 signature checks.

The only cryptography operations used here are
``Ed25519PublicKey.from_public_bytes`` and ``Ed25519PublicKey.verify``.
This module does not generate keys, shell out, or download bytes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from livecho_backend.auth.crypto import decode_secret

from .points import acceptable_point, group_order

_ENROLLMENT_LABEL = b"livecho-worker-enrollment-v1\x00"
_CHALLENGE_LABEL = b"livecho-worker-challenge-v1\x00"
_GATEWAY_UPGRADE_LABEL = b"livecho-worker-gateway-upgrade-v1\x00"
_UNPADDED = re.compile(r"[A-Za-z0-9_-]+\Z")


def enrollment_verifier(key: bytes, token: bytes) -> bytes:
    """HMAC-SHA-256 over the worker-enrollment label, 0x00, and the token."""
    if len(key) != 32 or len(token) != 32:
        raise ValueError("enrollment verifier inputs must be 32 bytes")
    return hmac.new(key, _ENROLLMENT_LABEL + token, hashlib.sha256).digest()


def acceptable_public_key(raw: bytes) -> bool:
    """Accept a canonical large-order key the verifier can load."""
    if not acceptable_point(raw):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(raw)
    except ValueError:
        return False
    return True


def verify_signature(public_key: bytes, signature: bytes, message: bytes) -> bool:
    """Return whether ``signature`` is a canonical Ed25519 signature."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    scalar = int.from_bytes(signature[32:], "little")
    if scalar >= group_order():
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(public_key)
        key.verify(signature, message)
    except (InvalidSignature, ValueError):
        return False
    return True


def challenge_message(device_id: str, challenge_id: str, nonce: bytes) -> bytes:
    """Build the exact challenge-signature message."""
    return (
        _CHALLENGE_LABEL
        + device_id.encode("ascii")
        + b"\x00"
        + challenge_id.encode("ascii")
        + b"\x00"
        + nonce
    )


def gateway_proof_message(
    device_id: str, challenge_id: str, nonce: bytes, handshake_key: bytes
) -> bytes:
    """Bind the challenge to the RFC 6455 key of the actual upgrade."""
    if len(nonce) != 32 or len(handshake_key) != 16:
        raise ValueError("invalid upgrade proof inputs")
    return (
        _GATEWAY_UPGRADE_LABEL
        + device_id.encode("ascii")
        + b"\x00"
        + challenge_id.encode("ascii")
        + b"\x00"
        + nonce
        + handshake_key
    )


def decode_unpadded(value: object, size: int) -> bytes | None:
    """Decode unpadded base64url of exactly ``size`` bytes, or return None."""
    if size == 32 and isinstance(value, str):
        return decode_secret(value)
    if not isinstance(value, str) or _UNPADDED.fullmatch(value) is None:
        return None
    if len(value) != (size * 8 + 5) // 6:
        return None
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError:
        return None
    if len(raw) != size:
        return None
    return raw
