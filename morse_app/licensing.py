"""单机永久会员的离线签名与授权文件管理。"""

from __future__ import annotations

import base64
import hashlib
import os
import uuid
from pathlib import Path
from importlib.resources import files

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


_PAYLOAD_PREFIX = "永久会员|"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    if _b64encode(decoded) != value:
        raise ValueError("激活码编码不规范")
    return decoded


def _windows_machine_identifier() -> str:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
    except (ImportError, OSError) as error:
        raise ValueError("无法读取本机设备标识") from error
    if not isinstance(value, str) or not value.strip():
        raise ValueError("本机设备标识无效")
    return value.strip()


def machine_code(raw_id: str | None = None) -> str:
    source = raw_id if raw_id is not None else _windows_machine_identifier()
    digest = hashlib.sha256(f"摩斯电码生成器|{source}".encode("utf-8")).hexdigest()
    short = digest[:20].upper()
    return "-".join(short[index : index + 4] for index in range(0, 20, 4))


def load_embedded_public_key() -> bytes:
    try:
        encoded = files("morse_app").joinpath("public_key.txt").read_text(
            encoding="ascii"
        ).strip()
        public_key = base64.b64decode(encoded, validate=True)
        Ed25519PublicKey.from_public_bytes(public_key)
        return public_key
    except (OSError, ValueError) as error:
        raise ValueError("会员验证公钥不可用") from error


def sign_activation(code_for_machine: str, private_key: bytes) -> str:
    payload = f"{_PAYLOAD_PREFIX}{code_for_machine.strip().upper()}".encode("utf-8")
    signature = Ed25519PrivateKey.from_private_bytes(private_key).sign(payload)
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def verify_activation(
    code: str,
    expected_machine_code: str,
    public_key: bytes,
) -> bool:
    try:
        encoded_payload, encoded_signature = code.strip().split(".", 1)
        payload = _b64decode(encoded_payload)
        signature = _b64decode(encoded_signature)
        expected = f"{_PAYLOAD_PREFIX}{expected_machine_code.strip().upper()}".encode(
            "utf-8"
        )
        if payload != expected:
            return False
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
        return True
    except (ValueError, InvalidSignature, UnicodeError):
        return False


def default_activation_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / "摩斯电码生成器" / "永久会员授权.txt"


def load_saved_activation(path: Path | None = None) -> str:
    target = Path(path) if path is not None else default_activation_path()
    try:
        return target.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_activation(code: str, path: Path | None = None) -> None:
    target = Path(path) if path is not None else default_activation_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(code.strip() + "\n", encoding="utf-8")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def is_current_machine_member(
    *,
    activation_path: Path | None = None,
    raw_machine_id: str | None = None,
    public_key: bytes | None = None,
) -> bool:
    try:
        current_machine = machine_code(raw_machine_id)
        verification_key = public_key or load_embedded_public_key()
        saved_code = load_saved_activation(activation_path)
        return bool(saved_code) and verify_activation(
            saved_code,
            current_machine,
            verification_key,
        )
    except ValueError:
        return False
