import re

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morse_app.licensing import (
    load_embedded_public_key,
    is_current_machine_member,
    load_saved_activation,
    machine_code,
    save_activation,
    sign_activation,
    verify_activation,
)


@pytest.fixture
def ed25519_keys():
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
    return private_bytes, public_bytes


def test_machine_code_is_private_stable_and_grouped():
    first = machine_code("raw-windows-identifier")
    second = machine_code("raw-windows-identifier")
    assert first == second
    assert "raw" not in first.lower()
    assert re.fullmatch(r"[A-F0-9]{4}(?:-[A-F0-9]{4}){4}", first)


def test_activation_is_bound_to_machine(ed25519_keys):
    private, public = ed25519_keys
    code = sign_activation("AAAA-BBBB", private)
    assert verify_activation(code, "AAAA-BBBB", public)
    assert not verify_activation(code, "CCCC-DDDD", public)


def test_tampered_activation_is_rejected(ed25519_keys):
    private, public = ed25519_keys
    code = sign_activation("AAAA-BBBB", private)
    replacement = "A" if code[-1] != "A" else "B"
    assert not verify_activation(code[:-1] + replacement, "AAAA-BBBB", public)


def test_malformed_activation_is_rejected(ed25519_keys):
    _, public = ed25519_keys
    assert not verify_activation("不是有效激活码", "AAAA-BBBB", public)


def test_activation_file_round_trip(tmp_path):
    path = tmp_path / "永久会员授权.txt"
    save_activation("测试激活码", path)
    assert load_saved_activation(path) == "测试激活码"


def test_missing_activation_file_is_empty(tmp_path):
    assert load_saved_activation(tmp_path / "不存在.txt") == ""


def test_embedded_public_key_is_valid_raw_key():
    public_key = load_embedded_public_key()
    assert len(public_key) == 32


def test_current_machine_member_uses_saved_code(ed25519_keys, tmp_path):
    private, public = ed25519_keys
    activation_path = tmp_path / "授权.txt"
    save_activation(sign_activation(machine_code("设备一"), private), activation_path)
    assert is_current_machine_member(
        activation_path=activation_path,
        raw_machine_id="设备一",
        public_key=public,
    )
    assert not is_current_machine_member(
        activation_path=activation_path,
        raw_machine_id="设备二",
        public_key=public,
    )
