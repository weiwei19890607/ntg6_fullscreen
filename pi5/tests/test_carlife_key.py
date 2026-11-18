"""Regression checks for production builds and local credential handling."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]


class KeyChecks(unittest.TestCase):
    def test_unrelated_key_is_rejected_without_printing_secret(self):
        secret = rsa.generate_private_key(public_exponent=65537, key_size=1024).private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption())
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / "key.pem"
            key.write_bytes(secret)
            result = subprocess.run(["python3", str(ROOT / "scripts/carlife-key.py"),
                                     "check", str(key)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(secret.splitlines()[1], result.stdout+result.stderr)

    def test_extract_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.pem"
            output.write_text("keep")
            result = subprocess.run(["python3", str(ROOT / "scripts/carlife-key.py"),
                                     "extract", "missing.apk", str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "keep")

    def test_production_build_refuses_missing_key_before_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, CP2CL_CARLIFE_KEY_FILE=str(Path(directory) / "missing.pem"),
                       CP2CL_ALLOW_NO_CARLIFE_KEY="0")
            result = subprocess.run(["bash", str(ROOT / "scripts/build.sh"),
                                     "aarch64-unknown-linux-musl"], env=env,
                                    capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("缺少 CarLife 密钥".encode(), result.stderr)


if __name__ == "__main__":
    unittest.main()
