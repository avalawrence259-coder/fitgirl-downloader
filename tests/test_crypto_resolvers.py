"""
Test Suite for Phase 4: Pure Crypto & Direct Mirror Resolvers
Tests PrivateBin AES-256-GCM + PBKDF2 decryption, Torrent magnet parsing, and Direct Host probes.
"""

import base64
import json
import zlib
from base58 import b58encode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import pytest

from ffdl.resolvers.privatebin import PrivateBinDecryptor
from ffdl.resolvers.torrent import TorrentResolver
from ffdl.resolvers.datanodes import DirectHostResolver


def test_privatebin_pure_python_decryption():
    """Create a synthetic PrivateBin v2 encrypted payload and verify pure Python decryption."""
    raw_secret_paste = "https://fuckingfast.co/part01#game.part01.rar\nhttps://fuckingfast.co/part02#game.part02.rar"
    raw_key = b"0123456789abcdef0123456789abcdef"  # 32 bytes = 256 bits
    key_b58 = b58encode(raw_key).decode("utf-8")

    salt = b"12345678"  # 8 bytes
    iv = b"123456789012"  # 12 bytes nonce
    iterations = 1000

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    derived_key = kdf.derive(raw_key)

    adata = [
        [
            base64.b64encode(iv).decode(),
            base64.b64encode(salt).decode(),
            iterations,
            256,
            128,
            "aes",
            "gcm",
            "zlib",
        ],
        "plaintext",
        0,
        0,
    ]

    payload_json = json.dumps({"paste": raw_secret_paste}).encode("utf-8")
    co = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    compressed = co.compress(payload_json) + co.flush()

    aesgcm = AESGCM(derived_key)
    associated_data = json.dumps(adata, separators=(",", ":")).encode("utf-8")
    encrypted_ct_tag = aesgcm.encrypt(iv, compressed, associated_data)

    paste_data = {
        "v": 2,
        "adata": adata,
        "ct": base64.b64encode(encrypted_ct_tag).decode(),
    }

    decrypted = PrivateBinDecryptor.decrypt_v2_payload(paste_data, key_b58)
    assert decrypted == raw_secret_paste


def test_torrent_resolver():
    magnet = "magnet:?xt=urn:btih:d3b07384d113edec49eaa6238ad5ff00&dn=Code+Vein+II+FitGirl&tr=udp://tracker.opentrackr.org:1337"
    assert TorrentResolver.is_magnet_url(magnet) is True
    assert TorrentResolver.is_magnet_url("https://fuckingfast.co/abc") is False

    info = TorrentResolver.parse_magnet_info(magnet)
    assert info["name"] == "Code Vein II FitGirl"
    assert "d3b07384d113edec49eaa6238ad5ff00" in info["hash"]

    html = f"""
    <div>
        <a href="{magnet}">Download Torrent</a>
        <a href="https://example.com">Mirror</a>
    </div>
    """
    magnets = TorrentResolver.extract_magnets_from_html(html)
    assert len(magnets) == 1
    assert magnets[0] == magnet


def test_direct_host_classifier():
    assert DirectHostResolver.is_datanodes_url("https://datanodes.to/abc123/game.rar") is True
    assert DirectHostResolver.is_datanodes_url("https://fuckingfast.co/abc123") is False
    assert DirectHostResolver.is_filekeeper_url("https://filekeeper.net/xyz/file.bin") is True
