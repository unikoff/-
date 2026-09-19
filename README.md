# Internet Speed Benchmark

CLI-программа измеряет скорость скачивания с заданного URL: выполняет 10
последовательных HTTP GET-запросов, не сохраняет тело ответа и выводит время,
объём и итоговую скорость в MB/s и Mbps.

## Установка

Требуется Python 3.12 или новее.

```powershell
cd "C:\папка куда вы скопировали репозиторий"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Запуск

Передайте прямой URL файла без redirect. В примере используется статический
файл OVH размером 10 MiB; один запуск передаст около 104.86 MB.

```powershell
python main.py "https://proof.ovh.net/files/10Mb.dat"
```

Необязательные таймауты:

```powershell
python main.py "https://proof.ovh.net/files/10Mb.dat" --connect-timeout 15 --timeout 180
```

CLI показывает панель параметров, прогресс из 10 запросов, таблицу результатов
и итоговую сводку. Если вместо URL вставить Markdown-ссылку, программа извлечёт
из неё адрес автоматически.

## Тесты

```powershell
python -m pytest
```

Тесты используют локальный HTTP-сервер: внешняя сеть не нужна.

## Архитектура

```text
main.py
  ├── benchmark/renderer.py    # терминальный интерфейс Rich
  └── benchmark/client.py      # 10 последовательных загрузок через libcurl
          ├── models.py        # результаты одного запроса и итоговая сводка
          └── statistics.py    # расчёт агрегированных метрик
```

`main.py` разбирает аргументы и связывает сетевые события с отображением.
`client.py` повторно использует один curl handle, отбрасывает тело ответа
потоково и получает время/байты из libcurl. `renderer.py` отвечает только за
панели, прогресс, таблицу и ошибки; сеть в нём отсутствует.

## Структура

```text
.
├── main.py
├── benchmark/
│   ├── client.py
│   ├── models.py
│   ├── renderer.py
│   └── statistics.py
├── tests/
│   ├── test_client.py
│   ├── test_main.py
│   ├── test_renderer.py
│   └── test_statistics.py
├── requirements.txt       # PycURL, Rich, pytest
├── pyproject.toml         # конфигурация pytest
└── README.md
```
