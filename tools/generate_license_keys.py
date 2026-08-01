"""一次性生成主程序公钥和所有者私钥。"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate(private_path: Path, public_path: Path) -> None:
    if private_path.exists() or public_path.exists():
        raise ValueError("密钥文件已经存在，为防止失效不会覆盖")
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
    private_path.write_text(base64.b64encode(private_bytes).decode("ascii") + "\n")
    public_path.write_text(base64.b64encode(public_bytes).decode("ascii") + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("private_path", type=Path)
    parser.add_argument("public_path", type=Path)
    args = parser.parse_args()
    generate(args.private_path, args.public_path)


if __name__ == "__main__":
    main()
