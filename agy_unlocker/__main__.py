import sys

if sys.version_info < (3, 9):
    # До импорта пакета: на старых Python часть синтаксиса недоступна,
    # а пользователю нужен внятный совет, а не traceback.
    sys.stderr.write(
        "agy-unlock: требуется Python 3.9+, а запущен Python %s.\n"
        "Скачайте свежую версию: https://www.python.org/downloads/\n"
        % ".".join(str(part) for part in sys.version_info[:3])
    )
    raise SystemExit(1)

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
