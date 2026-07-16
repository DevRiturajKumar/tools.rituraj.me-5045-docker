"""
TOTP (Time-based One-Time Password) implementation
Compatible with Google Authenticator, Authy, etc.
Pure Python - no external dependencies for core TOTP logic.
"""
import hmac
import hashlib
import struct
import time
import base64

BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'


def _base32_decode(s: str) -> bytes:
    """Decode base32 string to bytes (RFC 4648)."""
    s = s.upper().replace(' ', '').replace('=', '')
    output = bytearray()
    buffer = 0
    bits_left = 0
    for c in s:
        val = BASE32_ALPHABET.find(c)
        if val < 0:
            continue
        buffer = (buffer << 5) | val
        bits_left += 5
        if bits_left >= 8:
            output.append((buffer >> (bits_left - 8)) & 0xFF)
            bits_left -= 8
    return bytes(output)


def _generate_otp(secret: bytes, counter: int, digits: int = 6) -> str:
    """Generate HOTP value for given counter."""
    counter_bytes = struct.pack('>Q', counter)
    hmac_hash = hmac.new(secret, counter_bytes, hashlib.sha1).digest()
    offset = hmac_hash[19] & 0xf
    code = ((hmac_hash[offset] & 0x7f) << 24 |
            (hmac_hash[offset + 1] & 0xff) << 16 |
            (hmac_hash[offset + 2] & 0xff) << 8 |
            (hmac_hash[offset + 3] & 0xff)) % (10 ** digits)
    return str(code).zfill(digits)


class TOTP:
    """Time-based One-Time Password."""

    def __init__(self, secret: str, period: int = 30, digits: int = 6):
        self.secret = secret
        self.period = period
        self.digits = digits

    def get_code(self, timestamp: int = None) -> str:
        """Get the TOTP code for given timestamp."""
        timestamp = timestamp or int(time.time())
        counter = timestamp // self.period
        decoded = _base32_decode(self.secret)
        return _generate_otp(decoded, counter, self.digits)

    def verify(self, code: str, timestamp: int = None, window: int = 1) -> bool:
        """Verify a TOTP code with +/-window drift tolerance."""
        timestamp = timestamp or int(time.time())
        counter = timestamp // self.period
        decoded = _base32_decode(self.secret)
        for i in range(-window, window + 1):
            if hmac.compare_digest(_generate_otp(decoded, counter + i, self.digits), code):
                return True
        return False

    def get_provisioning_uri(self, label: str, issuer: str = 'SkillsPortal') -> str:
        """Generate otpauth:// URI for QR code."""
        import urllib.parse
        params = urllib.parse.urlencode({
            'secret': self.secret,
            'issuer': issuer,
            'algorithm': 'SHA1',
            'digits': self.digits,
            'period': self.period,
        })
        enc_label = urllib.parse.quote(label)
        enc_issuer = urllib.parse.quote(issuer)
        return f"otpauth://totp/{enc_issuer}:{enc_label}?{params}"
