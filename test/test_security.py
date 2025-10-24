# tests/test_security.py
from core.security import generate_salt, hash_pin, verify_pin

def test_hash_verify():
    salt = generate_salt()
    h = hash_pin("1234", salt)
    assert verify_pin("1234", salt, h)
    assert not verify_pin("0000", salt, h)
