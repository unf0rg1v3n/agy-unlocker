"""Командный интерфейс agy-unlocker."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from typing import List, Optional, Tuple

from . import __version__, detect
from .envcfg import Settings, load_settings
from .patchers import base, cli_bin, langserver

CLI_PROCESS_NAMES = ("agy.exe", "agy")
UI_PROCESS_NAMES = ("language_server.exe", "language_server", "Antigravity.exe", "antigravity")

STATUS_MARK = {
    "patched": "[OK] применён",
    "would-patch": "[..] применим, ещё не пропатчен",
    "already": "[==] уже пропатчено",
    "not_found": "[??] сигнатура не найдена",
    "foreign": "[??] сборка не распознана",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agy-unlock",
        description="Снятие региональной блокировки Google Antigravity (CLI agy и IDE).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--shell",
        choices=("bash", "cmd", "powershell"),
        default=None,
        help=argparse.SUPPRESS,
    )
    sub = parser.add_subparsers(dest="command")

    def common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--component",
            choices=("all", "cli", "ui"),
            default="all",
            help="что обрабатывать (по умолчанию: всё найденное)",
        )

    patch = sub.add_parser("patch", help="пропатчить найденные компоненты (действие по умолчанию)")
    common(patch)
    patch.add_argument("--dry-run", action="store_true", help="показать изменения без записи")
    patch.add_argument("-y", "--yes", action="store_true", help="не спрашивать подтверждения")

    status = sub.add_parser("status", help="состояние компонентов и патчей (только чтение)")
    common(status)

    restore = sub.add_parser("restore", help="откатить патч из резервной копии")
    common(restore)
    restore.add_argument("-y", "--yes", action="store_true", help="не спрашивать подтверждения")

    doctor = sub.add_parser("doctor", help="диагностика: компоненты, патчи, сетевой выход")
    common(doctor)
    doctor.add_argument("--no-net", action="store_true", help="не проверять внешний IP")
    return parser


def _force_utf8_stdio() -> None:
    # Git Bash / Windows Terminal ожидают UTF-8, а Python на Windows по умолчанию
    # пишет в консоль в ANSI-кодировке — кириллица превращается в «?».
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def main(argv: Optional[List[str]] = None) -> int:
    _force_utf8_stdio()
    args = build_parser().parse_args(argv)
    settings = load_settings()
    shell = args.shell or detect.guess_shell()
    command = args.command or "patch"
    handlers = {
        "patch": cmd_patch,
        "status": cmd_status,
        "restore": cmd_restore,
        "doctor": cmd_doctor,
    }
    return handlers[command](args, settings, shell)


def resolve_targets(component: str, settings: Settings) -> List[Tuple[str, object]]:
    targets: List[Tuple[str, object]] = []
    if component in ("all", "cli"):
        targets.append(("cli", detect.find_cli(settings.cli_path)))
    if component in ("all", "ui"):
        targets.append(("ui", detect.find_langserver(settings.langserver_path)))
    return targets


def target_path(kind: str, info: object) -> object:
    return info.real_path if kind == "cli" else info.language_server


def target_title(kind: str) -> str:
    return "Antigravity CLI (agy)" if kind == "cli" else "Antigravity IDE (language_server)"


def confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(prompt)
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes", "д", "да")


def print_layers(statuses: List[base.LayerStatus]) -> None:
    for status in statuses:
        mark = STATUS_MARK.get(status.status, status.status)
        detail = f" — {status.detail}" if status.detail else ""
        print(f"    {mark}: {status.name}{detail}")


def shell_command(shell: str, arguments: str) -> str:
    if shell == "bash":
        return f"./agy-unlock {arguments}".rstrip()
    if shell == "powershell":
        return f".\\agy-unlock.ps1 {arguments}".rstrip()
    return f"agy-unlock.cmd {arguments}".rstrip()


def cmd_patch(args: argparse.Namespace, settings: Settings, shell: str) -> int:
    dry_run = bool(getattr(args, "dry_run", False))
    assume_yes = bool(getattr(args, "yes", False)) or settings.assume_yes
    found_any = False
    rc = 0
    for kind, info in resolve_targets(args.component, settings):
        if info is None:
            print(f"[--] {target_title(kind)}: установка не найдена, пропуск")
            continue
        found_any = True
        path = target_path(kind, info)
        print(f"\n=== {target_title(kind)} ===")
        print(f"    бинарник: {path}")
        if kind == "cli" and info.shim:
            print(f"    [!] обнаружен сторонний посредник: {info.command}")
            print("        патчим настоящий бинарник (.real), посредник не трогаем")
        procs = detect.running_processes(CLI_PROCESS_NAMES if kind == "cli" else UI_PROCESS_NAMES)
        if procs:
            print(f"    [!] запущены процессы: {', '.join(sorted(procs))}")
            if not assume_yes and not confirm("        завершить их? [y/N]: "):
                print("    пропускаем компонент")
                rc = 1
                continue
            if not detect.kill_processes(sorted(procs)):
                print("    [!] не удалось завершить процессы — пропускаем компонент")
                rc = 1
                continue
        patcher = cli_bin if kind == "cli" else langserver
        try:
            statuses = patcher.apply(path, dry_run=dry_run)
        except (base.PatchError, OSError) as exc:
            print(f"    [ERR] {exc}")
            rc = 1
            continue
        print_layers(statuses)
        if all(st.status in ("not_found", "foreign") for st in statuses):
            print("    [!] ни один слой не применим — пришлите вывод 'status' разработчику")
            rc = 1
        if kind == "cli" and info.shim and not dry_run:
            if assume_yes or confirm("    убрать сторонний посредник (сохраним его как .xbox-shim.bak)? [y/N]: "):
                try:
                    parked = detect.normalize_cli_shim(info)
                except OSError as exc:
                    print(f"    [ERR] не удалось убрать посредника: {exc}")
                    rc = 1
                else:
                    print(f"    [OK] посредник убран -> {parked}")
                    print("         теперь команда 'agy' запускает пропатченный бинарник напрямую")
            else:
                print("    посредник оставлен: запускайте бинарник напрямую (agy.exe.real)")
    if not found_any:
        print("\nНичего не найдено. Установите Antigravity или укажите пути в .env (см. .env.example).")
        return 2
    print()
    if dry_run:
        print("Это была репетиция (--dry-run). Для реального патча запустите:")
        print(f"    {shell_command(shell, 'patch')}")
    else:
        print("Готово. Дальше:")
        if args.component in ("all", "cli"):
            print("    • CLI:  agy --version   (при необходимости: agy login — с включённым VPN)")
        if args.component in ("all", "ui"):
            print("    • IDE:  запустите Antigravity как обычно")
        print(f"    • проверка состояния: {shell_command(shell, 'status')}")
    return rc


def cmd_status(args: argparse.Namespace, settings: Settings, shell: str) -> int:
    found_any = False
    for kind, info in resolve_targets(args.component, settings):
        if info is None:
            print(f"[--] {target_title(kind)}: установка не найдена")
            continue
        found_any = True
        path = target_path(kind, info)
        print(f"\n=== {target_title(kind)} ===")
        print(f"    бинарник: {path}")
        print(f"    бэкап:    {base.backup_info(path)}")
        if kind == "cli":
            if info.shim:
                print(f"    [!] сторонний посредник: {info.command} (патчим {info.real})")
            version = detect.probe_version(info.real_path)
            if version:
                print(f"    версия:   {version}")
        patcher = cli_bin if kind == "cli" else langserver
        try:
            statuses = patcher.scan(path)
        except OSError as exc:
            print(f"    [ERR] не удалось прочитать файл: {exc}")
            continue
        print_layers(statuses)
    if not found_any:
        print("Компоненты Antigravity не найдены.")
        print("Если установка нестандартная — задайте пути в .env (см. .env.example).")
        return 2
    print()
    print(f"Патч: {shell_command(shell, 'patch')}    Откат: {shell_command(shell, 'restore')}")
    return 0


def cmd_restore(args: argparse.Namespace, settings: Settings, shell: str) -> int:
    assume_yes = bool(getattr(args, "yes", False)) or settings.assume_yes
    found_any = False
    rc = 0
    for kind, info in resolve_targets(args.component, settings):
        if info is None:
            print(f"[--] {target_title(kind)}: установка не найдена, пропуск")
            continue
        found_any = True
        path = target_path(kind, info)
        print(f"\n=== {target_title(kind)} ===")
        print(f"    бинарник: {path}")
        if not assume_yes and not confirm("    откатить к оригиналу? [y/N]: "):
            print("    отменено")
            continue
        try:
            base.restore_backup(path)
        except (base.BackupError, base.PatchError, OSError) as exc:
            print(f"    [ERR] {exc}")
            rc = 1
            continue
        print("    [OK] восстановлено из резервной копии")
    if not found_any:
        return 2
    if args.component == "all" or True:
        pass
    print()
    print("Примечание: сторонние шимы (если были) этой командой не удаляются.")
    return rc


def cmd_doctor(args: argparse.Namespace, settings: Settings, shell: str) -> int:
    print(f"agy-unlocker {__version__}")
    rc = cmd_status(args, settings, shell)
    print("\n=== Сеть ===")
    if getattr(args, "no_net", False) or not settings.net_check:
        print("    проверка IP отключена (--no-net или AGY_UNLOCKER_NO_NET)")
    else:
        egress = _egress_info()
        if egress:
            print(f"    внешний IP: {egress}")
            print("    ожидается страна из поддерживаемых регионов (US/EU и т.п.) — иначе VPN обязателен")
        else:
            print("    [??] не удалось определить внешний IP (сеть недоступна?)")
    return rc


def _egress_info(timeout: int = 6) -> Optional[str]:
    try:
        with urllib.request.urlopen("https://ipinfo.io/json", timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
        org = data.get("org") or ""
        return f"{data.get('ip', '?')} ({data.get('country', '?')}) {org}".strip()
    except Exception:
        return None
