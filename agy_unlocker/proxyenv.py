"""Прокси-окружение.

Go-бинарники Antigravity (agy, language_server) игнорируют системный прокси
Windows (WinINet) и читают только переменные окружения HTTP(S)_PROXY.
Поэтому при VPN через локальный прокси (xray/v2ray и т.п.) браузер работает,
а agy ходит напрямую с реального IP и получает 400 "User location is not supported".

Модуль умеет:
- читать системный прокси Windows (WinINet);
- читать/писать прокси в переменных окружения пользователя (HKCU\\Environment,
  с broadcast WM_SETTINGCHANGE — новые процессы подхватят без перелогина);
- на POSIX только показывает готовые export/unset строки.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

ENV_PROXY_KEYS = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")


def normalize_proxy_url(server: str) -> str:
    server = (server or "").strip()
    if server and "://" not in server:
        server = "http://" + server
    return server


def current_env_proxy(env: Optional[Dict[str, str]] = None) -> Optional[str]:
    env = os.environ if env is None else env
    for key in ENV_PROXY_KEYS:
        value = (env.get(key) or "").strip()
        if value:
            return normalize_proxy_url(value)
    return None


def read_system_proxy() -> Optional[str]:
    """Системный прокси (WinINet). На POSIX системного прокси не существует."""
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except OSError:
        return None
    if not enable or not server:
        return None
    return normalize_proxy_url(server) or None


def user_env_proxy() -> Optional[str]:
    """Прокси из постоянного окружения пользователя (выживает между сессиями)."""
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            for name in ENV_PROXY_KEYS:
                try:
                    value, _ = winreg.QueryValueEx(key, name)
                except OSError:
                    continue
                value = (value or "").strip()
                if value:
                    return normalize_proxy_url(value)
    except OSError:
        pass
    return None


def install_user_proxy(proxy: str) -> None:
    proxy = normalize_proxy_url(proxy)
    if not proxy:
        raise ValueError("пустой адрес прокси")
    if os.name != "nt":
        raise NotImplementedError("на POSIX задайте переменные в shell-конфиге")
    import winreg

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
    try:
        for name in ENV_PROXY_KEYS:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, proxy)
    finally:
        key.Close()
    _broadcast_environment()


def remove_user_proxy() -> int:
    if os.name != "nt":
        raise NotImplementedError("на POSIX удалите строки из shell-конфига")
    import winreg

    deleted = 0
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
    try:
        for name in ENV_PROXY_KEYS:
            try:
                winreg.DeleteValue(key, name)
                deleted += 1
            except OSError:
                continue
    finally:
        key.Close()
    if deleted:
        _broadcast_environment()
    return deleted


def _broadcast_environment() -> None:
    """WM_SETTINGCHANGE -> Explorer обновит env-блок для новых процессов."""
    import ctypes

    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF,  # HWND_BROADCAST
        0x001A,  # WM_SETTINGCHANGE
        0,
        "Environment",
        0x0002,  # SMTO_ABORTIFHUNG
        5000,
        ctypes.byref(result),
    )
