import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morse_app.license_admin_gui import create_activation, load_owner_private_key
from morse_app.licensing import verify_activation


def test_admin_requires_external_private_key(tmp_path):
    with pytest.raises(ValueError, match="私钥文件"):
        load_owner_private_key(tmp_path / "owner-private-key.txt")


def test_admin_rejects_invalid_private_key(tmp_path):
    path = tmp_path / "owner-private-key.txt"
    path.write_text("无效内容", encoding="utf-8")
    with pytest.raises(ValueError, match="私钥文件"):
        load_owner_private_key(path)


def test_admin_creates_machine_bound_activation(tmp_path):
    private = Ed25519PrivateKey.generate()
    private_bytes = private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    path = tmp_path / "owner-private-key.txt"
    path.write_text(base64.b64encode(private_bytes).decode("ascii"), encoding="ascii")

    code = create_activation("aaaa-bbbb", path)

    assert verify_activation(code, "AAAA-BBBB", public_bytes)


def test_admin_rejects_empty_machine_code(tmp_path):
    path = tmp_path / "owner-private-key.txt"
    path.write_text(base64.b64encode(bytes(32)).decode("ascii"), encoding="ascii")
    with pytest.raises(ValueError, match="机器码"):
        create_activation("  ", path)
