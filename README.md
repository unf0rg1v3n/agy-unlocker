# agy-unlocker

Утилита для снятия региональной блокировки **Google Antigravity** — и CLI (`agy`), и IDE.
Работает на Windows, Linux и macOS, требует только Python 3.9+ (стандартная библиотека,
никаких зависимостей). Запускается из bash, cmd и PowerShell одними и теми же командами.

---

## Как это работает

Проверка «доступности региона» в Antigravity **клиентская**: сервер отвечает структурой
с полем недопустимости (`ineligible` / `has_valid_auth=false`), а клиент сам решает
блокировать запуск. Инструмент правит бинарники локально, поэтому VPN по-прежнему нужен для самого трафика до Google — но больше ни OS-регион, ни ответ сервера не ломают запуск.

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
откат — одна команда.

Проверено end-to-end (патч → реальный запрос → откат → повторный патч) на:
`agy 1.3.3` (Windows x64), IDE со сборкой `language_server` от сентября 2026 (Windows x64).

## Требования

- Python 3.9+ ([python.org/downloads](https://www.python.org/downloads/)) — на Windows
  можно не добавлять в PATH, утилита найдёт его через лаунчер `py`.
- Аккаунт Google с доступом к Antigravity и VPN/прокси со страной из поддерживаемых регионов.

## Установка

```bash
git clone https://github.com/unf0rg1v3n/agy-unlocker.git
cd agy-unlocker
```

Виртуальное окружение не обязательно (зависимостей нет), но если создать `.venv`,
обёртки используют его автоматически:

```bash
python -m venv .venv          # Windows: py -3 -m venv .venv
```

## Использование

Запускайте ту обёртку, которая соответствует вашему шеллу — она сама найдёт Python
и вызовет ядро с правильным синтаксисом:

| Shell       | Команда                                |
|-------------|----------------------------------------|
| bash / Git Bash / WSL / Linux / macOS | `./agy-unlock patch`  |
| cmd         | `agy-unlock.cmd patch`                 |
| PowerShell  | `.\agy-unlock.ps1 patch`               |

Команды (идентичны во всех шеллах):

| Команда | Назначение |
|---|---|
| `patch` | Найти и пропатчить всё установленное (CLI и/или IDE) |
| `patch --dry-run` | Репетиция без записи |
| `patch -y` | Не спрашивать подтверждения (завершение процессов и т.п.) |
| `status` | Состояние: пути, версии, слои патча, бэкапы (только чтение) |
| `restore` | Откат к оригиналам из резервных копий |
| `doctor` | Диагностика + проверка страны внешнего IP |
| `run -- <команда>` | Запустить команду с прокси-переменными: `run -- agy -p "привет"` |
| `proxy status` | Показать прокси на всех уровнях и вердикт |
| `proxy install` | Прописать прокси в окружение пользователя (постоянно) |
| `proxy remove` | Убрать прокси из окружения пользователя |
| `--component cli\|ui` | Обрабатывать только один компонент |

Утилита сама определяет, что установлено, ищет бинарники в стандартных путях
(`%LOCALAPPDATA%\agy\bin\agy.exe`, `%LOCALAPPDATA%\Programs\Antigravity\...`,
`~/.local/bin/agy`, `/opt/antigravity/...`, `/Applications/Antigravity.app/...`).
Нестандартные пути можно задать в `.env` (см. `.env.example`).

### Сторонние разблокировщики

Если раньше стоял проприетарный разблокировщик семейства xbox-dns (`agy-wrapper`),
его шим распознаётся автоматически: патч применяется к настоящему бинарнику (`.real`),
а шим аккуратно убирается (паркуется как `agy.exe.xbox-shim.bak`), чтобы команда `agy`
снова запускала рабочий оригинал. Полностью обратимо.

## Прокси: почему `agy` может отвечать 400 даже «с VPN»

`agy` и `language_server` — Go-бинарники: они **игнорируют системный прокси Windows**
(настройку WinINet, которую использует браузер) и читают только переменные окружения
`HTTP(S)_PROXY`. Если VPN работает через локальный прокси (xray/v2ray/clash на
`127.0.0.1:порт`), браузер ходит через VPN, а agy — напрямую с реального IP и получает:

```
FAILED_PRECONDITION (code 400): User location is not supported for the API use.
```

Утилита решает это на выбор:

```bash
# Вариант 1 (рекомендуется, Windows): прописать прокси в окружение пользователя —
# подхватят все новые процессы, включая IDE и её language_server:
./agy-unlock proxy install        # cmd: agy-unlock.cmd proxy install
# затем перезапустите терминал и IDE

# Вариант 2: разовый запуск с автоподстановкой системного прокси:
./agy-unlock run -- agy -p "привет"

# Вариант 3: вручную (любая ОС):
export HTTPS_PROXY=http://127.0.0.1:10809   # Windows: setx HTTPS_PROXY http://127.0.0.1:10809
```

Адрес берётся из системных настроек автоматически; если авто-детект не подошёл —
задайте `AGY_PROXY` в `.env`. `proxy status` показывает все уровни и вердикт;
`proxy remove` откатывает изменения. Проверка всей цепочки — `./agy-unlock doctor`
(покажет и прокси, и страну внешнего IP).

## Решение проблем

| Симптом | Причина | Действие |
|---|---|---|
| `400 User location is not supported for the API use` | agy игнорирует системный прокси и ходит с реального IP | `proxy install` (и перезапустить терминал/IDE) или `run -- agy ...` |
| `Eligibility check failed: ... not available in your location` | патч затёрт обновлением agy/IDE | повторить `patch` |
| `Eligibility check failed: ... Not Allowed` (после стороннего разблокировщика) | чужой шим режет трафик | прогнать `patch` — он распознает и уберёт шим |
| `proxyconnect tcp: dial tcp 127.0.0.1:XXXXX: connection refused` | VPN-клиент выключен или прокси на другом порту | включить VPN; при необходимости задать `AGY_PROXY` в `.env` |
| неясно, что сломано | — | `doctor` — покажет патчи, прокси и страну выхода |

## Обновления Antigravity

Автообновление `agy` или IDE **перезаписывает бинарники и затирает патч** — это
нормально. После обновления просто запустите `patch` ещё раз: слои применятся заново
(инструмент различает «уже пропатчено», «не пропатчено» и «незнакомая сборка»).

## Отказ от ответственности

Инструмент модифицирует файлы установленного ПО на вашем компьютере и предназначен
для восстановления доступа к оплаченной подписке. Использование может противоречить
условиям использования Google; аккаунт теоретически могут ограничить. Бэкапы создаются
автоматически, но вы действуете на свой страх и риск. Проект никак не аффилирован с Google.

## Для разработчиков

```bash
python -m unittest discover -s tests   # 16 тестов, только stdlib
```

Структура: `agy_unlocker/` — ядро (детект, паттерны, бэкапы, CLI), `agy-unlock{,.cmd,.ps1}`
— тонкие обёртки под шеллы. Добавление сигнатур новых сборок — в `patchers/cli_bin.py`
и `patchers/langserver.py`.

## English (short version)

agy-unlocker removes Google Antigravity's client-side region gate for both the `agy` CLI
and the IDE (`language_server`). It patches local binaries (eligibility branch
neutralization + consistent `ineligible`→`inexigible` literal rename for the CLI;
forced `hasValidAuth=true` for the IDE), with byte-exact SHA-256-verified backups and
one-command restore. Stdlib-only Python 3.9+, works from bash/cmd/PowerShell via the
included wrappers. Re-run `patch` after each Antigravity update.

Note: Go binaries ignore the Windows system proxy — if your VPN is a local proxy
(xray/v2ray/clash), run `proxy install` once (or use `run -- agy ...`), restart your
terminal/IDE, otherwise model calls fail with `400 User location is not supported`.
Use at your own risk; not affiliated with Google.

## License

MIT, см. [LICENSE](LICENSE).
