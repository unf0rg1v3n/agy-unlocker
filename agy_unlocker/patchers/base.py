"""Базовые примитивы: байтовые сигнатуры, бэкапы, атомарная запись, слои патча."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

BACKUP_SUFFIX = ".agyunlock.bak"
SIDECAR_SUFFIX = ".agyunlock.json"


class PatchError(RuntimeError):
    """Ошибка применения патча (файл занят, нет доступа и т.п.)."""


class BackupError(PatchError):
    """Проблема с резервной копией."""


class BytePattern:
    """Байтовая сигнатура; '??' — wildcard на один байт."""

    def __init__(self, hex_pattern: str):
        tokens = hex_pattern.split()
        self.tokens: List[Optional[int]] = [
            None if tok == "??" else int(tok, 16) for tok in tokens
        ]
        body = b"".join(
            b"." if tok is None else re.escape(bytes([tok])) for tok in self.tokens
        )
        self.regex = re.compile(body, re.DOTALL)

    def find(self, data: bytes) -> int:
        match = self.regex.search(data)
        return match.start() if match else -1

    def find_all(self, data: bytes) -> List[int]:
        return [m.start() for m in self.regex.finditer(data)]


@dataclass
class Gate:
    name: str
    unpatched: BytePattern
    patched: BytePattern
    replacement: bytes
    offset: int = 0


@dataclass
class LayerStatus:
    name: str
    status: str  # patched | already | not_found | foreign | would-patch
    detail: str = ""


# Тип слоя: (data) -> (new_data | None, LayerStatus)
Layer = Callable[[bytes], Tuple[Optional[bytes], LayerStatus]]


def gate_layer(gate: Gate) -> Layer:
    def fn(data: bytes) -> Tuple[Optional[bytes], LayerStatus]:
        if gate.patched.find(data) != -1:
            return None, LayerStatus(gate.name, "already", "сигнатура патча уже присутствует")
        hits = gate.unpatched.find_all(data)
        if not hits:
            return None, LayerStatus(gate.name, "not_found", "сигнатура не найдена (незнакомая сборка)")
        buf = bytearray(data)
        for hit in hits:
            pos = hit + gate.offset
            buf[pos : pos + len(gate.replacement)] = gate.replacement
        return bytes(buf), LayerStatus(gate.name, "patched", f"{len(hits)} вхождений")

    return fn


def string_layer(name: str, find: bytes, replace: bytes) -> Layer:
    if len(find) != len(replace):
        raise ValueError("string_layer требует литералы одинаковой длины")

    def fn(data: bytes) -> Tuple[Optional[bytes], LayerStatus]:
        has_new = data.count(replace)
        if has_new and not data.count(find):
            return None, LayerStatus(name, "already", f"литерал уже переименован ({has_new} шт.)")
        count = data.count(find)
        if not count:
            return None, LayerStatus(name, "foreign", f"литерал {find!r} не найден — сборка не распознана")
        return data.replace(find, replace), LayerStatus(name, "patched", f"{count} вхождений")

    return fn


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_paths(path: Path) -> Tuple[Path, Path]:
    return (
        path.with_name(path.name + BACKUP_SUFFIX),
        path.with_name(path.name + SIDECAR_SUFFIX),
    )


def ensure_backup(path: Path) -> Path:
    """Создаёт побайтовую копию один раз; повторные вызовы проверяют целостность."""
    bak, sidecar = backup_paths(path)
    if bak.exists():
        meta = _read_sidecar(sidecar)
        if meta is None:
            raise BackupError(f"резервная копия есть, но нет метаданных: {bak}")
        if meta.get("size") != bak.stat().st_size or meta.get("sha256") != sha256_file(bak):
            raise BackupError(f"резервная копия повреждена (изменялся не через этот инструмент): {bak}")
        return bak
    try:
        shutil.copy2(path, bak)
    except OSError as exc:
        raise BackupError(f"не удалось создать копию {path}: {exc}") from exc
    meta = {
        "original": str(path),
        "size": bak.stat().st_size,
        "sha256": sha256_file(bak),
        "tool": "agy-unlocker",
        "created_at": int(time.time()),
    }
    sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return bak


def _read_sidecar(sidecar: Path) -> Optional[dict]:
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def backup_info(path: Path) -> str:
    bak, sidecar = backup_paths(path)
    if not bak.exists():
        return "бэкапа нет"
    meta = _read_sidecar(sidecar)
    if meta and meta.get("size") == bak.stat().st_size and meta.get("sha256") == sha256_file(bak):
        return f"бэкап ок ({_fmt_size(meta.get('size', 0))})"
    return "бэкап есть, но метаданные отсутствуют или повреждены"


def restore_backup(path: Path) -> None:
    bak, sidecar = backup_paths(path)
    if not bak.exists():
        raise BackupError(f"резервная копия не найдена: {bak}")
    meta = _read_sidecar(sidecar)
    if meta and (meta.get("size") != bak.stat().st_size or meta.get("sha256") != sha256_file(bak)):
        raise BackupError("резервная копия повреждена, откат отменён")
    atomic_write(path, bak.read_bytes())
    bak.unlink(missing_ok=True)
    sidecar.unlink(missing_ok=True)


def atomic_write(path: Path, data: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_name, str(path))
    except OSError as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if exc.errno in (13, 26, 32):
            raise PatchError(
                f"файл занят другим процессом или недоступен: {path}\n"
                "Закройте Antigravity IDE / agy и повторите."
            ) from exc
        raise


def run_layers(data: bytes, layers: List[Layer]) -> Tuple[bool, bytes, List[LayerStatus]]:
    statuses: List[LayerStatus] = []
    current = data
    for layer in layers:
        updated, status = layer(current)
        statuses.append(status)
        if updated is not None:
            current = updated
    return current is not data, current, statuses


def apply_to_file(path: Path, layers: List[Layer], dry_run: bool = False) -> List[LayerStatus]:
    data = path.read_bytes()
    changed, new_data, statuses = run_layers(data, layers)
    for status in statuses:
        if dry_run and status.status == "patched":
            status.status = "would-patch"
    if changed and not dry_run:
        ensure_backup(path)
        atomic_write(path, new_data)
    return statuses


def _fmt_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"
