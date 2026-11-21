"""Enrollment-time Ed25519 public-key checks.

RFC 8032 decoding and the cofactor check live here so a small-order or
non-canonical key is refused before a verifier library sees it. This module
does not sign, generate keys, or call another package.
"""

from __future__ import annotations

_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_I = pow(2, (_P - 1) // 4, _P)
_IDENTITY = (0, 1)


def group_order() -> int:
    """Return the Ed25519 prime-order subgroup size ``L``."""
    return _L


def acceptable_point(raw: bytes) -> bool:
    """Return whether ``raw`` is a canonical public key of large order."""
    point = _decode(raw)
    if point is None:
        return False
    return not _order_divides_cofactor(point)


def canonical_small_order_encodings() -> tuple[bytes, ...]:
    """Return the eight canonical encodings whose order divides 8."""
    base = _order_eight_base()
    point = _IDENTITY
    found: list[bytes] = []
    for _ in range(8):
        found.append(_encode(point))
        point = _add(point, base)
    return tuple(found)


def _decode(raw: bytes) -> tuple[int, int] | None:
    """Strict RFC 8032 section 5.1.3 decode, or None when it fails."""
    if len(raw) != 32:
        return None
    word = int.from_bytes(raw, "little")
    sign = word >> 255
    y = word & ((1 << 255) - 1)
    if y >= _P:
        return None
    y2 = y * y % _P
    numerator = (y2 - 1) % _P
    denominator = (_D * y2 + 1) % _P
    if denominator == 0:
        return None
    x2 = numerator * pow(denominator, _P - 2, _P) % _P
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _I % _P
    if (x * x - x2) % _P != 0:
        return None
    if x == 0 and sign == 1:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x, y


def _encode(point: tuple[int, int]) -> bytes:
    x, y = point
    word = y | ((x & 1) << 255)
    return word.to_bytes(32, "little")


def _add(first: tuple[int, int], second: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = first
    x2, y2 = second
    product = _D * x1 * x2 * y1 * y2
    denom_x = (1 + product) % _P
    denom_y = (1 - product) % _P
    x3 = (x1 * y2 + x2 * y1) * pow(denom_x, _P - 2, _P) % _P
    y3 = (y1 * y2 + x1 * x2) * pow(denom_y, _P - 2, _P) % _P
    return x3, y3


def _double(point: tuple[int, int]) -> tuple[int, int]:
    return _add(point, point)


def _order_divides_cofactor(point: tuple[int, int]) -> bool:
    multiplied = _double(_double(_double(point)))
    return multiplied == _IDENTITY


def _sqrt(value: int) -> int | None:
    root = pow(value, (_P + 3) // 8, _P)
    if (root * root - value) % _P == 0:
        return root
    root = root * _I % _P
    if (root * root - value) % _P == 0:
        return root
    return None


def _order_eight_base() -> tuple[int, int]:
    """One point of order 8, derived from the curve equation."""
    discriminant = (1 + _D) % _P
    root = _sqrt(discriminant)
    if root is None:
        raise RuntimeError("order-8 base point was not found")
    for signed in (root, (_P - root) % _P):
        z = ((-1 + signed) * pow(_D, _P - 2, _P)) % _P
        y = _sqrt(z)
        if y is None:
            continue
        for candidate_y in (y, (_P - y) % _P):
            point = (candidate_y * _I % _P, candidate_y)
            order_at_most_four = _double(_double(point)) == _IDENTITY
            if _order_divides_cofactor(point) and not order_at_most_four:
                return point
    raise RuntimeError("order-8 base point was not found")
