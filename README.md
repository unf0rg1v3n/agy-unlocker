# agy-unlocker

Снимает региональную блокировку **Google Antigravity** — и у командной строки (`agy`), и у программы Antigravity (IDE).
Работает на Windows, Linux и macOS. Нужны только Python 3.9+ и VPN.

---

## ⚡ Быстрый старт — 3 шага

**Шаг 1. Установите Python** (один раз).
Откройте [python.org/downloads](https://www.python.org/downloads/) → скачайте → запустите установщик →
**обязательно поставьте галочку «Add python.exe to PATH»** на первом экране → Install.
На Linux/macOS Python обычно уже установлен.

**Шаг 2. Скачайте agy-unlocker.**
На странице репозитория: зелёная кнопка **Code → Download ZIP** → распакуйте в любую папку.
(Либо `git clone https://github.com/unf0rg1v3n/agy-unlocker.git`)

**Шаг 3. Запустите одну команду.**
Откройте терминал в папке с программой и введите:

| Ваша система | Команда |
|---|---|
| **Windows** (cmd и PowerShell — без разницы) | `agy-unlock.cmd patch` |
| **Linux / macOS / Git Bash / WSL** | `./agy-unlock patch` |

Готово — Antigravity пропатчен. Проверка: `... status`. Полная диагностика: `... doctor`.

> ### ⚠️ Два важных нюанса
>
> 1. **VPN обязателен.** Утилита убирает проверку региона в самой программе, но трафик до Google
>    по-прежнему должен идти через VPN/прокси страны, где Antigravity доступен.
> 2. **Пользуетесь программой Antigravity (IDE)?** Перезапустите её после патча. Если агент в IDE
>    отвечает `400 User location is not supported` — см. раздел «Прокси» ниже (обычно лечится
>    командой `proxy install`; при настроенном системном прокси утилита делает это сама).

---

## ❗ Запускаю — а мне просто пишет «Python» или «Python was not found»

Значит, настоящий Python не установлен, а Windows подсовывает заглушку Microsoft Store
(так бывает «из коробки» на Windows 11). Лечение — любой из двух способов:

1. **Установите Python**: [python.org/downloads](https://www.python.org/downloads/) — с галочкой
   «Add python.exe to PATH». Затем откройте **новое** окно терминала и повторите команду.
2. Или **отключите заглушки**: Параметры → Приложения → Дополнительные параметры приложений →
   Псевдонимы выполнения приложений → выключите «python» и «py» — и установите Python (способ 1).

**Python вроде стоит, но работает только команда `py` (а `python` — нет)?**
Выполните в папке утилиты:

```
py -3 -m venv .venv
```

Обёртка сама подхватит этот `.venv`. Более того: если другого Python в системе нет,
обёртка собирает `.venv` через `py` **автоматически** при первом запуске —
вручную делать это не обязательно.

## ❗ PowerShell пишет «execution of scripts is disabled on this system»

Используйте `agy-unlock.cmd` — она одинаково работает и в cmd, и в PowerShell.
Для `agy-unlock.ps1` выполните однажды: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
— либо запускайте так: `powershell -ExecutionPolicy Bypass -File .\agy-unlock.ps1 patch`.

## ❗ После обновления Antigravity всё сломалось

Автообновление `agy` или IDE перезаписывает бинарники и затирает патч — это нормально.
Просто запустите `patch` ещё раз.

---

## Команды

Запускайте ту обёртку, которая соответствует вашему шеллу — она сама найдёт Python
(Windows: `agy-unlock.cmd …`, остальные: `./agy-unlock …`; во всех шеллах команды одинаковые):

| Команда | Назначение |
|---|---|
| `patch` | Найти и пропатчить всё установленное (CLI и/или IDE) |
| `patch --dry-run` | Репетиция без записи |
| `patch -y` | Не спрашивать подтверждения (завершение процессов и т.п.) |
| `status` | Состояние: пути, версии, слои патча, бэкапы (только чтение) |
| `restore` | Откат к оригиналам из резервных копий |
| `doctor` | Диагностика + страна вашего внешнего IP |
| `run -- <команда>` | Запустить команду с прокси-переменными: `run -- agy -p "привет"` |
| `proxy status` | Показать прокси на всех уровнях и вердикт |
| `proxy install` | Прописать прокси в окружение пользователя (постоянно) |
| `proxy remove` | Убрать прокси из окружения пользователя |

Утилита сама определяет, что установлено, ищет бинарники в стандартных путях
(`%LOCALAPPDATA%\agy\bin\agy.exe`, `%LOCALAPPDATA%\Programs\Antigravity\...`,
`~/.local/bin/agy`, `/opt/antigravity/...`, `/Applications/Antigravity.app/...`).
Нестандартные пути можно задать в `.env` рядом с утилитой (см. `.env.example`).

## Решение проблем

| Симптом | Причина | Действие |
|---|---|---|
| при запуске любой команды выводит «Python» / «Python was not found…» | в системе нет Python — сработала заглушка Microsoft Store | установить Python / отключить псевдонимы (инструкция выше) |
| `python` не запускается, а работает только `py` | Python установлен, но не добавлен в PATH | ничего страшного: `py -3 -m venv .venv` в папке утилиты — обёртка подхватит `.venv` (собирает его сама автоматически) |
| `400 User location is not supported for the API use` | agy игнорирует системный прокси и ходит с реального IP | `proxy install` (и перезапустить терминал/IDE) или `run -- agy ...` |
| `Eligibility check failed: ... not available in your location` | патч затёрт обновлением agy/IDE | повторить `patch` |
| `Eligibility check failed: ... Not Allowed` (после стороннего разблокировщика) | чужой шим режет трафик | прогнать `patch` — он распознает и уберёт шим |
| `proxyconnect tcp: dial tcp 127.0.0.1:XXXXX: connection refused` | VPN-клиент выключен или прокси на другом порту | включить VPN; при необходимости задать `AGY_PROXY` в `.env` |
| неясно, что сломано | — | `doctor` — покажет патчи, прокси и страну выхода |

## Прокси: почему agy отвечает 400 даже «с VPN»

`agy` и `language_server` — Go-бинарники: они **игнорируют системный прокси Windows**
(настройку WinINet, которую использует браузер) и читают только переменные окружения
`HTTP(S)_PROXY`. Если VPN работает через локальный прокси (xray/v2ray/clash на
`127.0.0.1:порт`), браузер ходит через VPN, а agy — напрямую с реального IP и получает:

```
FAILED_PRECONDITION (code 400): User location is not supported for the API use.
```

Утилита решает это сама: если при `patch` обнаружен настроенный системный прокси,
а переменные окружения не прописаны, они прописываются автоматически (с пояснением
в выводе). Ручное управление, если нужно:

```bash
# Вариант 1 (Windows): прописать прокси в окружение пользователя —
# подхватят все новые процессы, включая IDE и её language_server:
agy-unlock.cmd proxy install        # bash: ./agy-unlock proxy install
# затем перезапустите терминал и IDE

# Вариант 2: разовый запуск с автоподстановкой системного прокси:
agy-unlock.cmd run -- agy -p "привет"

# Вариант 3: вручную (любая ОС):
export HTTPS_PROXY=http://127.0.0.1:10809   # Windows: setx HTTPS_PROXY http://127.0.0.1:10809
```

Адрес берётся из системных настроек автоматически; если авто-детект не подошёл —
задайте `AGY_PROXY` в `.env`. `proxy status` показывает все уровни и вердикт;
`proxy remove` откатывает изменения. Проверка всей цепочки — `doctor`
(покажет и прокси, и страну внешнего IP). Если VPN работает в TUN-режиме
(перехватывает весь трафик), прокси не нужен вообще.

## Как это работает

Проверка «доступности региона» в Antigravity **клиентская**: сервер отвечает структурой
с полем недопустимости (`ineligible` / `has_valid_auth=false`), а клиент сам решает
блокировать запуск. Инструмент правит бинарники локально — поэтому VPN по-прежнему нужен
для самого трафика до Google, но больше ни OS-регион, ни ответ сервера не ломают запуск.

**CLI (`agy`)** — два независимых слоя (применяются оба):

1. **Машинный гейт**: нейтрализация ветки `cmp byte [rax+8], 0; jnz <блокировка>`
   после получения ответа сервера. Сигнатура с wildcard-ми, не привязана к смещениям
   конкретной сборки (x64 и arm64).
2. **Строковый литерал**: согласованное переименование `ineligible` → `inexigible`
   той же длины во всех вхождениях — protobuf-дескриптор, json-тег и серверный ключ
   перестают совпадать, поле десериализуется как пустое.

**IDE (`language_server.exe`)**: замена `cmp byte [rax+8], 0` на `mov byte [rax+8], 1`
принудительно выставляет `hasValidAuth=true` в структуре `AuthResult`, которую IDE
получает от сервера. Это снимает гейт «User location is not supported» / 403 на
этапе авторизации.

Все замены равной длины: layout бинарника, релокации и offsets не меняются.
Перед изменением создаётся побайтовая копия `<файл>.agyunlock.bak` (контроль SHA-256),
откат — одна команда (`restore`).

Проверено end-to-end (патч → реальный запрос → откат → повторный патч) на:
`agy 1.3.3` (Windows x64), IDE со сборкой `language_server` от сентября 2026 (Windows x64).

### Сторонние разблокировщики

Если раньше стоял проприетарный разблокировщик семейства xbox-dns (`agy-wrapper`),
его шим распознаётся автоматически: патч применяется к настоящему бинарнику (`.real`),
а шим аккуратно убирается (паркуется как `agy.exe.xbox-shim.bak`), чтобы команда `agy`
снова запускала рабочий оригинал. Полностью обратимо.

## Отказ от ответственности

Инструмент модифицирует файлы установленного ПО на вашем компьютере и предназначен
для восстановления доступа к оплаченной подписке. Использование может противоречить
условиям использования Google; аккаунт теоретически могут ограничить. Бэкапы создаются
автоматически, но вы действуете на свой страх и риск. Проект никак не аффилирован с Google.

## Для разработчиков

```bash
python -m unittest discover -s tests   # только стандартная библиотека
```

Структура: `agy_unlocker/` — ядро (детект, паттерны, бэкапы, CLI), `agy-unlock{,.cmd,.ps1}`
— тонкие обёртки под шеллы: сами ищут настоящий Python 3.9+ пробным запуском (отсекая
заглушки Microsoft Store) и вызывают `python -m agy_unlocker`. Добавление сигнатур новых
сборок — в `patchers/cli_bin.py` и `patchers/langserver.py`.

## English (short version)

agy-unlocker removes Google Antigravity's client-side region gate for both the `agy` CLI
and the IDE (`language_server`). It patches local binaries (eligibility branch
neutralization + consistent `ineligible`→`inexigible` literal rename for the CLI;
forced `hasValidAuth=true` for the IDE), with byte-exact SHA-256-verified backups and
one-command restore. Stdlib-only Python 3.9+, works from bash/cmd/PowerShell via the
included wrappers. Re-run `patch` after each Antigravity update.

Quick start: install Python 3.9+ ("Add python.exe to PATH"), download this repo, run
`agy-unlock.cmd patch` on Windows or `./agy-unlock patch` elsewhere.

Note: Go binaries ignore the Windows system proxy — if your VPN is a local proxy
(xray/v2ray/clash), `patch` writes the proxy variables into your user environment
automatically (or run `proxy install` manually / use `run -- agy ...`), restart your
terminal/IDE, otherwise model calls fail with `400 User location is not supported`.
If running the tool prints just "Python" / "Python was not found", Python isn't
installed — disable the Microsoft Store aliases or install Python from python.org.
If only the `py` launcher works (no `python` in PATH), run `py -3 -m venv .venv` in the
tool folder — the wrappers pick up `.venv` automatically (and try to build it for you).
Use at your own risk; not affiliated with Google.

## License

MIT, см. [LICENSE](LICENSE).
