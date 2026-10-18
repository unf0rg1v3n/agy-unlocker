"""Патч Antigravity CLI (agy).

Сервер присылает структуру с полем ``ineligible``, а клиент сам решает
блокировать запуск. Патч двухслойный:

1. Машинный гейт: нейтрализация ветки ``cmp byte [rax+8], 0; jnz <блокировка>``
   после проверки ответа сервера. Сигнатура с wildcard-ми, применяется ко
   всем вхождениям; не зависит от смещений конкретной сборки.
2. Строковый литерал ``ineligible`` -> ``inexigible`` той же длины:
   protobuf-дескриптор, json-тег и серверный ключ переименовываются
   согласованно, поле перестаёт десериализоваться — гейт видит его пустым.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from .base import BytePattern, Gate, LayerStatus, apply_to_file, gate_layer, string_layer

GATE_X64 = Gate(
    name="машинный гейт eligibility (x64)",
    unpatched=BytePattern("48 85 c0 0f 84 ?? ?? ?? ?? 80 78 08 00 0f 85 ?? ?? ?? ??"),
    patched=BytePattern("48 85 c0 0f 84 ?? ?? ?? ?? 48 85 c0 90 0f 85 ?? ?? ?? ??"),
    replacement=bytes.fromhex("4885c090"),
    offset=9,
)

GATE_ARM64 = Gate(
    name="машинный гейт eligibility (arm64)",
    unpatched=BytePattern("?? ?? ?? b5 ?? ?? ?? b4 01 20 40 39 ?? ?? ?? 37"),
    patched=BytePattern("?? ?? ?? b5 ?? ?? ?? b4 21 00 80 52 ?? ?? ?? 37"),
    replacement=bytes.fromhex("21008052"),
    offset=8,
)

STRING_PROTOBUF_FIELD = string_layer(
    "строковый литерал ineligible -> inexigible",
    b"ineligible",
    b"inexigible",
)


def layers():
    return [gate_layer(GATE_X64), gate_layer(GATE_ARM64), STRING_PROTOBUF_FIELD]


def scan(path: Path) -> List[LayerStatus]:
    return apply_to_file(path, layers(), dry_run=True)


def apply(path: Path, dry_run: bool = False) -> List[LayerStatus]:
    return apply_to_file(path, layers(), dry_run=dry_run)
