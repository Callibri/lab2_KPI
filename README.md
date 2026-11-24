# Лабораторна робота 2. Шарова архітектура та доменна модель

![tests](https://github.com/Callibri/lab2/actions/workflows/tests.yml/badge.svg)

Рефакторинг лабораторної 1: бізнес-логіка винесена в доменну модель, проєкт розділений на чотири шари. API не змінився.

## Встановлення

Потрібен Python 3.11 або новіший.

Windows (PowerShell):

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux / macOS:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

```
uvicorn boxoffice.main:app --app-dir src --reload
```

Документація в браузері: http://127.0.0.1:8000/docs.

## Тести

```
pytest -v
```

- `tests/domain` доменні об'єкти й фабрики без бази даних і без HTTP;
- `tests/application` use case-и на in-memory реалізаціях репозиторіїв (`tests/fakes.py`);
- `tests/integration` ендпоінти разом з базою даних;
- `tests/test_architecture.py` перевіряє, що домен не імпортує ORM і веб-фреймворк.

Тести домену й use case-ів окремо: `pytest tests/domain tests/application`.

## Структура

```
src/boxoffice/
  domain/           сутності, Value Objects, фабрики, інтерфейси репозиторіїв, помилки
  application/      use case-и
  infrastructure/   ORM-моделі, мапери, репозиторії, хешування паролів, JWT
  presentation/     роутери, DTO, відповідність доменних помилок HTTP-статусам
  bootstrap.py      складання застосунку
```

Залежності: Presentation → Application → Domain ← Infrastructure.

## Документи

- `docs/ADR-001-rich-domain-model.md` вибір моделі домену;
- `docs/analysis/lab2.md` порівняльний аналіз;
