#!/usr/bin/env python3
"""Validate a local CarLife key, or extract the matching key from an APK.

Never print private key data. The expected public key comes from the pinned
upstream regression test, rather than trusting any RSA constant in an APK.
"""
import argparse
import base64
import hashlib
from pathlib import Path
import re
import zipfile

from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[1]


def expected_public():
    source = (ROOT / "upstream/cp2cl/src/main.rs").read_text()
    pem = re.search(r"-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----", source, re.S)
    if pem is None:
        raise ValueError("Pinned upstream public key is missing")
    return serialization.load_pem_public_key(pem.group().encode())


def public_der(key):
    return key.public_bytes(serialization.Encoding.DER,
                            serialization.PublicFormat.SubjectPublicKeyInfo)


def check(key):
    if public_der(key.public_key()) != public_der(expected_public()):
        raise ValueError("Key does not match pinned upstream CarLife public key")
    print(f"CarLife key verified: RSA {key.key_size} bits; public SHA256 "
          f"{hashlib.sha256(public_der(key.public_key())).hexdigest()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["check", "extract"])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    if args.operation == "check":
        check(serialization.load_pem_private_key(args.input.read_bytes(), None))
        return
    if args.output is None or args.output.exists():
        parser.error("extract requires a new output path (will not overwrite)")
    with zipfile.ZipFile(args.input) as archive:
        for name in archive.namelist():
            if not name.endswith(".dex"):
                continue
            for candidate in re.finditer(rb"MII[A-Za-z0-9+/=]{600,3000}", archive.read(name)):
                try:
                    key = serialization.load_der_private_key(
                        base64.b64decode(candidate.group(), validate=True), None)
                except (ValueError, TypeError):
                    continue
                if public_der(key.public_key()) != public_der(expected_public()):
                    continue
                check(key)
                # Exclusive creation and permissions apply before secret bytes are written.
                import os
                fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as output:
                    output.write(key.private_bytes(serialization.Encoding.PEM,
                                 serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption()))
                print(f"Extracted matching constant from {name}; no APK code executed")
                return
    raise SystemExit("No matching CarLife key found in APK")


if __name__ == "__main__":
    main()
