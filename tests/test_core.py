"""Юнит-тесты agy-unlocker (stdlib unittest, без внешних зависимостей)."""

import os
import tempfile
import unittest
from pathlib import Path

from agy_unlocker import detect, proxyenv
from agy_unlocker.envcfg import _parse_dotenv
from agy_unlocker.patchers import base, cli_bin, langserver


class BytePatternTests(unittest.TestCase):
    def test_wildcard_matches_any_byte_including_newline(self):
        pattern = base.BytePattern("80 78 08 00 74 ??")
        data = b"\x00\x80\x78\x08\x00\x74\x0a\xff"
        self.assertEqual(pattern.find(data), 1)
        self.assertEqual(pattern.find_all(data), [1])

    def test_no_false_match(self):
        pattern = base.BytePattern("80 78 08 00 74 ??")
        self.assertEqual(pattern.find(b"\x80\x78\x08\x00\x75\x00"), -1)


class GateTests(unittest.TestCase):
    SEQ_X64 = bytes.fromhex("4885c00f84aabbccdd807808000f85eeff1122")

    def _blob(self):
        return b"\x90" * 8 + self.SEQ_X64 + b"\x90" * 8

    def test_gate_applies_at_offset(self):
        layer = base.gate_layer(cli_bin.GATE_X64)
        updated, status = layer(self._blob())
        self.assertEqual(status.status, "patched")
        self.assertIn(bytes.fromhex("4885c090"), updated)
        self.assertNotIn(bytes.fromhex("80780800"), updated[8:27])

    def test_gate_idempotent(self):
        layer = base.gate_layer(cli_bin.GATE_X64)
        updated, first = layer(self._blob())
        self.assertEqual(first.status, "patched")
        again, second = layer(updated)
        self.assertIsNone(again)
        self.assertEqual(second.status, "already")

    def test_gate_foreign(self):
        layer = base.gate_layer(cli_bin.GATE_X64)
        updated, status = layer(b"\x00" * 64)
        self.assertIsNone(updated)
        self.assertEqual(status.status, "not_found")


class StringLayerTests(unittest.TestCase):
    def test_literals_same_length(self):
        self.assertEqual(len(b"ineligible"), len(b"inexigible"))

    def test_rename_all_occurrences(self):
        layer = base.string_layer("test", b"ineligible", b"inexigible")
        data = b'json:"ineligible_tiers,omitempty" name=ineligible'
        updated, status = layer(data)
        self.assertEqual(status.status, "patched")
        self.assertEqual(updated.count(b"inexigible"), 2)
        self.assertNotIn(b"ineligible", updated)

    def test_foreign_build(self):
        layer = base.string_layer("test", b"ineligible", b"inexigible")
        updated, status = layer(b"\x00" * 32)
        self.assertIsNone(updated)
        self.assertEqual(status.status, "foreign")


class BackupTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agy.exe"
            original = os.urandom(2048)
            path.write_bytes(original)
            base.ensure_backup(path)
            self.assertIn("ок", base.backup_info(path))
            patched = bytearray(original)
            patched[0] ^= 0xFF
            base.atomic_write(path, bytes(patched))
            base.restore_backup(path)
            self.assertEqual(path.read_bytes(), original)
            bak, sidecar = base.backup_paths(path)
            self.assertFalse(bak.exists())
            self.assertFalse(sidecar.exists())

    def test_tampered_backup_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agy.exe"
            path.write_bytes(os.urandom(512))
            base.ensure_backup(path)
            bak, _ = base.backup_paths(path)
            with open(bak, "r+b") as fh:
                fh.seek(0)
                fh.write(b"XXXX")
            with self.assertRaises(base.BackupError):
                base.ensure_backup(path)


class ApplyToFileTests(unittest.TestCase):
    def _langserver_blob(self):
        seq = bytes(
            [0x80, 0x78, 0x08, 0x00, 0x74, 0x55]
            + [0x48, 0x8B, 0x4C, 0x24, 0x30]
            + [0x48, 0x89, 0x7D, 0x60]
        )
        return b"\x90" * 4 + seq + b"\x90" * 4

    def test_dry_run_then_real_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "language_server.exe"
            blob = self._langserver_blob()
            path.write_bytes(blob)
            statuses = langserver.apply(path, dry_run=True)
            self.assertEqual(statuses[0].status, "would-patch")
            self.assertEqual(path.read_bytes(), blob)
            statuses = langserver.apply(path)
            self.assertEqual(statuses[0].status, "patched")
            bak, _ = base.backup_paths(path)
            self.assertTrue(bak.exists())
            # повторный патч: уже пропатчено
            statuses = langserver.apply(path)
            self.assertEqual(statuses[0].status, "already")


class DotenvTests(unittest.TestCase):
    def test_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "# comment\nAGY_CLI_PATH=C:\\x\\agy.exe\n\nFLAG='true'\n",
                encoding="utf-8",
            )
            values = _parse_dotenv(path)
            self.assertEqual(values["AGY_CLI_PATH"], r"C:\x\agy.exe")
            self.assertEqual(values["FLAG"], "true")


class DetectTests(unittest.TestCase):
    def test_find_cli_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agy.exe"
            path.write_bytes(b"MZ")
            info = detect.find_cli(str(path))
            self.assertIsNotNone(info)
            self.assertEqual(info.real_path, path)

    def test_find_cli_explicit_missing(self):
        self.assertIsNone(detect.find_cli("/nonexistent/path/agy.exe"))

    def test_candidates_return_list(self):
        self.assertIsInstance(detect.cli_candidates(), list)
        self.assertIsInstance(detect.langserver_candidates(), list)


class ProxyEnvTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(proxyenv.normalize_proxy_url("127.0.0.1:10809"), "http://127.0.0.1:10809")
        self.assertEqual(proxyenv.normalize_proxy_url("socks5://127.0.0.1:10808"), "socks5://127.0.0.1:10808")
        self.assertEqual(proxyenv.normalize_proxy_url("   "), "")

    def test_current_env_proxy(self):
        self.assertEqual(proxyenv.current_env_proxy({"HTTPS_PROXY": "http://x:1"}), "http://x:1")
        self.assertEqual(proxyenv.current_env_proxy({"http_proxy": "http://y:2"}), "http://y:2")
        self.assertIsNone(proxyenv.current_env_proxy({}))


class NormalizeShimTests(unittest.TestCase):
    def test_shim_layout_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shim = tmp_path / "agy.exe"
            real = tmp_path / "agy.exe.real"
            shim.write_bytes(b"SHIM")
            real.write_bytes(b"REAL")
            base.ensure_backup(real)

            info = detect.CliInstall(command=shim, real=real, shim=True, third_party=True)
            parked = detect.normalize_cli_shim(info)

            self.assertEqual(shim.read_bytes(), b"REAL")
            self.assertEqual(parked.read_bytes(), b"SHIM")
            self.assertFalse(real.exists())
            self.assertFalse(info.shim)
            # бэкап и метаданные переехали на agy.exe
            bak, sidecar = base.backup_paths(shim)
            self.assertTrue(bak.exists())
            self.assertTrue(sidecar.exists())
            # restore работает уже по новому имени
            shim.write_bytes(b"TAMPERED")
            base.restore_backup(shim)
            self.assertEqual(shim.read_bytes(), b"REAL")


if __name__ == "__main__":
    unittest.main()
