# Аналіз лабораторної 2: шарова архітектура

## Що змінилося в структурі порівняно з лабою 1
У лабі 1 було 4 пакети за технічним принципом: `models.py`, `schemas.py`, `validators.py` і `routers/*`. Роутер (наприклад, `create_report` у `routers/reports.py`) сам шукав фільм у БД, викликав валідатор, перевіряв дубль запитом `select(...)`, будував ORM-об'єкт і робив `commit`. Тепер проєкт `src/boxoffice` складається з чотирьох шарів:
- `domain/` — сутності `Movie`, `BoxOfficeReport`, `User`, VO `Email`/`Money`/`RegionCode`, фабрики, інтерфейси репозиторіїв, доменні помилки (`DomainError` та нащадки);
- `application/` — use case-и (`AddReport`, `CreateMovie`, …) і порт `TokenService`;
- `infrastructure/` — ORM-моделі, мапери, SQLAlchemy-репозиторії, PBKDF2-хешер, JWT;
- `presentation/` — роутери, HTTP-DTO, перетворення `DomainError` → статус (400/401/404/409).
`bootstrap.py` — composition root, єдиний файл, що знає про всі шари. Логіка `create_report` розділилася на три місця: правила дати — `Movie.ensure_accepts_report_for`, унікальність — `ReportFactory`, збереження — `SqlAlchemyReportRepository`.

## Переваги
- **Інваріанти не обійти.** У лабі 1 можна було створити `BoxOfficeReport` з від'ємними зборами напряму через ORM. Тепер `Money(-1)` кидає `DomainValidationError` ще до репозиторію.
- **Швидкі тести без інфраструктури.** `tests/domain` і `tests/application` (34 тести) працюють на fake-репозиторіях з `tests/fakes.py` без БД, HTTP і FastAPI. У лабі 1 усе, окрім чистих валідаторів, можна було перевірити тільки через HTTP.
- **Контроль залежностей.** Тест `tests/test_architecture.py` автоматично перевіряє, що `domain` не імпортує `sqlalchemy`, `fastapi`, `jwt`, а `presentation` — `infrastructure`.
- **Помилки не знають про HTTP.** Доменні помилки мапляться у статуси в одному місці (`presentation/api.py`), а не `HTTPException` у кожному роутері.
- **Поведінка API збережена:** ті самі 17 інтеграційних тестів лаби 1 пройшли без змін — рефакторинг не зламав контракт.

## Недоліки та ускладнення
- **Більше коду й файлів.** Для звичайного CRUD фільму потрібно пройти `MovieRequest` → `CreateMovie` → `MovieFactory` → `Movie` → `SqlAlchemyMovieRepository` → `MovieRow` → `MovieResponse`. У лабі 1 це був один роутер.
- **Мапінг.** `mappers.py` дублює поля `Movie` ↔ `MovieRow`; додавання поля вимагає змін у 5–6 місцях (сутність, ORM, мапер, DTO, схема відповіді).
- **Складніша навігація.** Щоб зрозуміти, як додається звіт, треба відкрити `routers.py`, `use_cases.py`, `factories.py`, `entities.py`, `repositories.py`.
- **Аналітика стала повільнішою.** `GetTopMovies` для кожного фільму з топу робить окремий `movies.get(...)` (N+1), а `GetMovieSummary` завантажує всі звіти в пам'ять, щоб порахувати суму в Python (`domain/services.summarize`). У лабі 1 це була одна SQL-агрегація. Це неефективність, яку виправляє CQS у лабі 3.
- **Спрощення:** кожен метод репозиторію сам робить `commit` — немає Unit of Work, тож кілька записів в одному use case не атомарні.

## Наскільки простіше змінити БД або фреймворк
- **Інша БД** (PostgreSQL → MongoDB): достатньо написати нові реалізації трьох інтерфейсів з `domain/repositories.py` (`MongoMovieRepository` тощо) і змінити два рядки в `bootstrap.py`. Домен, use case-и, контролери та 34 unit-тести не змінюються. Для порівняння: у лабі 1 довелося б переписувати всі 4 роутери.
- **Інший фреймворк** (FastAPI → Flask): міняється лише пакет `presentation/` (роутери, DTO, обробник помилок) та `bootstrap.py`; `domain`, `application`, `infrastructure` не чіпаємо. Цю зміну обмежує те, що `infrastructure/security.py` імпортує порт з `application`, але не з веб-фреймворку.

## Чому обрано Rich Domain Model
Рішення описане в `docs/ADR-001-rich-domain-model.md`. Основна причина — інваріанти (бюджет > 0, дата звіту, формат регіону, унікальність) мають бути неможливі до порушення, а не перевірятись у кожному роутері. Anemic-модель залишила б правила в сервісах і повторила проблему лаби 1 з іншою назвою. Ціна рішення — мапери та більший обсяг коду, що наведено в розділі недоліків.
