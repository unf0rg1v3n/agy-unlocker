"""Загрузка настроек: .env рядом с инструментом/в cwd + переменные окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    cli_path: Optional[str] = None
    langserver_path: Optional[str] = None
    proxy: Optional[str] = None
    assume_yes: bool = False
    net_check: bool = True


def _parse_dotenv(path: Path) -> dict:
    values: dict = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _truthy(value: Optional[str]) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on", "y", "д", "да")


def load_settings() -> Settings:
    base = Path(__file__).resolve().parent.parent
    values: dict = {}
    for candidate in (base / ".env", Path.cwd() / ".env"):
        values.update(_parse_dotenv(candidate))

    def get(key: str) -> Optional[str]:
        return os.environ.get(key) or values.get(key)

    return Settings(
        cli_path=get("AGY_CLI_PATH"),
        langserver_path=get("AGY_LANGSERVER_PATH"),
        proxy=get("AGY_PROXY"),
        assume_yes=_truthy(get("AGY_UNLOCKER_ASSUME_YES")),
        net_check=not _truthy(get("AGY_UNLOCKER_NO_NET")),
    )
