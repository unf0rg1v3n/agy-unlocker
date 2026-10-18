"""Поиск установленных компонентов Antigravity и работа с процессами."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Set


@dataclass
class CliInstall:
    command: Path  # то, что вызывает пользователь (возможно, чужой шим)
    real: Path  # настоящий бинарник Antigravity
    shim: bool  # command != real
    third_party: bool  # распознана подмена сторонним инструментом

    @property
    def real_path(self) -> Path:
        return self.real


@dataclass
class UiInstall:
    language_server: Path


def guess_shell() -> str:
    if os.name == "posix":
        return "bash"
    return "cmd"


def cli_candidates() -> List[Path]:
    system = platform.system()
    home = Path.home()
    if system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return [
            local / "agy" / "bin" / "agy.exe",
            home / "scoop" / "apps" / "agy" / "current" / "agy.exe",
        ]
    return [
        home / ".local" / "bin" / "agy",
        home / ".gemini" / "bin" / "antigravity",
        home / ".gemini" / "bin" / "agy",
        home / "bin" / "agy",
        Path("/usr/local/bin/agy"),
        Path("/opt/homebrew/bin/agy"),
        Path("/usr/bin/agy"),
    ]


def find_cli(explicit: Optional[str] = None) -> Optional[CliInstall]:
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists() and not path.is_dir():
            return CliInstall(command=path, real=path, shim=False, third_party=False)
        return None
    for candidate in cli_candidates():
        if not candidate.exists() or candidate.is_dir():
            continue
        if os.name == "nt":
            shim_target = candidate.with_name(candidate.name + ".real")
            if shim_target.exists():
                # Google не поставляет раскладку .real — это следы стороннего
                # разблокировщика; патчим настоящий бинарник, шим не трогаем.
                return CliInstall(command=candidate, real=shim_target, shim=True, third_party=True)
        return CliInstall(command=candidate, real=candidate, shim=False, third_party=False)
    return None


def langserver_candidates() -> List[Path]:
    system = platform.system()
    home = Path.home()
    name = "language_server.exe" if system == "Windows" else "language_server"
    resources = ("resources", "bin")
    if system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        roots = [
            local / "Programs" / "Antigravity",
            local / "Programs" / "antigravity",
            local / "Programs" / "Antigravity IDE",
            program_files / "Antigravity",
            program_files_x86 / "Antigravity",
        ]
    elif system == "Darwin":
        roots = [
            Path("/Applications/Antigravity.app/Contents/Resources"),
            home / "Applications" / "Antigravity.app" / "Contents" / "Resources",
            Path("/Applications/Antigravity IDE.app/Contents/Resources"),
            home / "Applications" / "Antigravity IDE.app" / "Contents" / "Resources",
        ]
    else:
        roots = [
            home / "Applications" / "Antigravity",
            home / "Applications" / "antigravity",
            Path("/opt/antigravity"),
            Path("/opt/Antigravity"),
            Path("/usr/share/antigravity"),
            home / ".local" / "share" / "antigravity",
        ]
    return [root.joinpath(*resources, name) for root in roots]


def find_langserver(explicit: Optional[str] = None) -> Optional[UiInstall]:
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists() and not path.is_dir():
            return UiInstall(language_server=path)
        return None
    for candidate in langserver_candidates():
        if candidate.exists() and not candidate.is_dir():
            return UiInstall(language_server=candidate)
    return None


def running_processes(names: Sequence[str]) -> Set[str]:
    found: Set[str] = set()
    lowered = {n.lower() for n in names}
    if os.name == "nt":
        try:
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                timeout=20,
                text=True,
                encoding="utf-8",
                errors="replace",
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return found
        for line in out.splitlines():
            first = line.split(",", 1)[0].strip().strip('"').lower()
            if first in lowered:
                found.add(first)
    else:
        for name in lowered:
            try:
                result = subprocess.run(["pgrep", "-x", name], capture_output=True, timeout=10)
                if result.returncode == 0:
                    found.add(name)
            except (OSError, subprocess.SubprocessError):
                continue
    return found


def kill_processes(names: Sequence[str]) -> bool:
    if os.name == "nt":
        base = ["taskkill", "/F", "/IM"]
    else:
        base = ["pkill", "-9", "-x"]
    ok = True
    for name in names:
        try:
            result = subprocess.run(base + [name], capture_output=True, timeout=20)
            ok = ok and result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
    return ok


def probe_version(path: Path, timeout: int = 20) -> Optional[str]:
    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = ((result.stdout or "") + (result.stderr or "")).strip().splitlines()
    return lines[0].strip() if lines else None


def park_name_for(shim: Path) -> Path:
    candidate = shim.with_name(shim.name + ".xbox-shim.bak")
    counter = 1
    while candidate.exists():
        candidate = shim.with_name(f"{shim.name}.xbox-shim.bak.{counter}")
        counter += 1
    return candidate


def normalize_cli_shim(info: CliInstall) -> Optional[Path]:
    """Убирает сторонний посредник: шим паркуется как .xbox-shim.bak,
    настоящий бинарник (.real) встаёт на его место. Полностью обратимо.

    Заодно переносит пару «бэкап+метаданные» agy-unlocker с .real на agy.exe,
    чтобы команда restore продолжала работать после нормализации.
    Возвращает путь запаркованного шима.
    """
    if not info.shim:
        return None
    import json

    from .patchers import base  # локальный импорт, чтобы избежать циклов

    shim, real = info.command, info.real
    parked = park_name_for(shim)
    os.replace(shim, parked)
    try:
        os.replace(real, shim)
    except OSError:
        os.replace(parked, shim)  # откат парковки
        raise
    # Перенос бэкапа agy-unlocker: agy.exe.real.* -> agy.exe.*
    for suffix in (base.BACKUP_SUFFIX, base.SIDECAR_SUFFIX):
        old = real.with_name(real.name + suffix)
        new = shim.with_name(shim.name + suffix)
        if old.exists() and not new.exists():
            os.replace(old, new)
    sidecar = shim.with_name(shim.name + base.SIDECAR_SUFFIX)
    meta = base._read_sidecar(sidecar)
    if meta is not None:
        meta["original"] = str(shim)
        sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    info.command = shim
    info.real = shim
    info.shim = False
    info.third_party = False
    return parked
