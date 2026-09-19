# Internet Speed Benchmark

Небольшой CLI-инструмент для измерения скорости скачивания с конкретного URL.
Программа выполняет 10 последовательных HTTP-запросов, не сохраняет файл на
диск и не загружает его целиком в оперативную память.

## Возможности

- Python 3.12+ и PycURL/libcurl;
- строго последовательные загрузки: следующий запрос начинается после полного
  завершения предыдущего;
- один переиспользуемый curl handle, поэтому libcurl может повторно использовать
  соединение;
- потоковый подсчёт фактически полученных байтов через `WRITEFUNCTION`;
- таймаут подключения и общий таймаут одной загрузки;
- проверка HTTP-статуса `2xx` и непустого тела ответа;
- итоговая скорость считается как общий объём / суммарное время, а не как
  простое среднее скоростей отдельных запросов;
- автоматические тесты с локальным HTTP-сервером, без внешней сети.

> Инструмент измеряет скорость скачивания именно с указанного URL. На результат
> влияют сервер, CDN, маршрут, TLS, размер файла и текущая нагрузка сети. Это не
> универсальный тест максимальной пропускной способности интернет-провайдера.

## Установка

Требуется Python 3.12 или новее.

```powershell
cd "C:\Project Python\-"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Если тесты запускать не нужно, достаточно установить `requirements.txt`.

## Запуск

Используйте прямую ссылку на достаточно большой файл, доступный по HTTP или
HTTPS:

```powershell
python main.py https://example.com/path/to/large-file.bin
```

Параметры таймаутов являются необязательными:

```powershell
python main.py https://example.com/large-file.bin --connect-timeout 15 --timeout 180
```

Пример формата вывода:

```text
Internet Speed Benchmark
===========================
Target:  https://example.com/large-file.bin
Requests: 10 (sequential)

  01/10 |    2.350 s |     50.00 MB |    21.28 MB/s | HTTP 200
  ...

Results
  Successful requests: 10/10
  Total downloaded:    500.00 MB
  Average time:        2.500 s
  Total transfer time: 25.000 s
  Average speed:       20.00 MB/s
  Average speed:       160.00 Mbps
```

Размеры в `MB` — десятичные (`1 MB = 1,000,000 bytes`).

## Тесты

```powershell
python -m pytest
```

Тесты проверяют расчёт агрегированной скорости, ровно 10 запросов, отсутствие
параллельных загрузок, обработку HTTP-ошибки и отказ от пустого ответа.

## Структура

```text
.
├── benchmark/
│   ├── client.py       # потоковая загрузка через PycURL
│   ├── models.py       # модели результатов
│   └── statistics.py   # чистые функции расчёта
├── tests/
├── main.py             # CLI
├── requirements.txt
├── requirements-dev.txt
└── README.md
```
