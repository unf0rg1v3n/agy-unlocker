"""Патч IDE: language_server — принудительный hasValidAuth=true.

IDE отдаёт всю авторизацию скомпилированному бинарнику ``language_server``
(Go, google3/jetski). Сервер возвращает ``AuthResult`` с полем
``has_valid_auth`` (bool по смещению +8 от указателя на структуру);
клиентский гейт ветвится по этому байту и при неуспехе обрывает сессию
(«User location is not supported», 403 на /auth-success и т.п.).

Замена ``cmp byte [rax+8], 0; jz ...`` на ``mov byte [rax+8], 1; nop; nop``
делает флаг всегда истинным сразу после получения ответа сервера.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from .base import BytePattern, Gate, LayerStatus, apply_to_file, gate_layer

GATE_X64 = Gate(
    name="language_server hasValidAuth=true (x64)",
    unpatched=BytePattern("80 78 08 00 74 ?? 48 8b ?? 24 ?? 48 89 ?? 60"),
    patched=BytePattern("c6 40 08 01 90 90 48 8b ?? 24 ?? 48 89 ?? 60"),
    replacement=bytes.fromhex("c64008019090"),
    offset=0,
)

GATE_ARM64 = Gate(
    name="language_server hasValidAuth=true (arm64)",
    unpatched=BytePattern("03 20 40 39 ?? ?? ?? 36 ?? ?? ?? ?? 03 10 06 a9"),
    patched=BytePattern("23 00 80 52 03 20 00 39 ?? ?? ?? ?? 03 10 06 a9"),
    replacement=bytes.fromhex("2300805203200039"),
    offset=0,
)


def layers():
    return [gate_layer(GATE_X64), gate_layer(GATE_ARM64)]


def scan(path: Path) -> List[LayerStatus]:
    return apply_to_file(path, layers(), dry_run=True)


def apply(path: Path, dry_run: bool = False) -> List[LayerStatus]:
    return apply_to_file(path, layers(), dry_run=dry_run)
