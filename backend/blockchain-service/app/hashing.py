import hashlib


def sha256_bytes(data: bytes) -> str:
    """Return a '0x'-prefixed 64-char hex SHA-256 digest of the given bytes.

    This is the only representation of the original certificate that ever
    reaches the blockchain — the file itself never does.
    """
    return "0x" + hashlib.sha256(data).hexdigest()
