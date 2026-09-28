# Защищенный REST API

Учебный REST API на Python/Flask. Данные хранятся в SQLite. Доступ к данным только по JWT.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET='long-random-secret-at-least-32-bytes'
export SEED_LOGIN=user
export SEED_PASSWORD=password
python app.py
```

Сервер слушает `http://127.0.0.1:5000`. Пользователь из `SEED_LOGIN` / `SEED_PASSWORD` создается при первом запуске, если таблица пользователей пустая. Пароль в базе лежит только как bcrypt-хеш.

## API

### POST /auth/login

Принимает логин и пароль. При успехе возвращает JWT.

```bash
curl -X POST http://127.0.0.1:5000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"user","password":"password"}'
```

Ответ: `{"token":"<jwt>"}`. Неверный логин или пароль: `401`.

### GET /api/data

Список пользователей. Только с токеном.

```bash
curl http://127.0.0.1:5000/api/data \
  -H 'Authorization: Bearer <token>'
```

Ответ: `{"users":[{"id":1,"login":"user"}]}`. Без токена или с неверным токеном: `401`.

### GET /dice

Подброс кубика. Возвращает число от 1 до 6.

```bash
curl http://127.0.0.1:5000/dice
```

Ответ: `{"result":4}`.

## Меры защиты

### SQL-инъекции

Запросы к SQLite собираются только с плейсхолдерами `?`. Значение логина передается отдельно от текста запроса и не подставляется в строку. Пример: вход ищет пользователя так:

```sql
SELECT login, password_hash FROM users WHERE login = ?
```

Строка вида `user' OR 1=1 --` ищется как обычный логин и не меняет условие запроса.

### XSS

Пользовательские строки перед отдачей в ответе проходят через `html.escape`. Логин из базы в `GET /api/data` экранируется: символы `<`, `>` и кавычки превращаются в HTML-сущности и не читаются как разметка.

### Аутентификация

Пароль проверяется через `bcrypt.checkpw` и в открытом виде не хранится. После успешного входа сервер выдает JWT (алгоритм HS256). В токене есть `sub` (логин) и `exp` (срок, 1 час). Секрет подписи берется из переменной `JWT_SECRET`.

`GET /api/data` закрыт middleware: из заголовка `Authorization` читается схема `Bearer`, токен проверяется `jwt.decode` с явным списком алгоритмов `HS256`. Нет заголовка, битая подпись или истекший срок дают `401`.

## CI/CD

Файл `.github/workflows/ci.yml`. Проверки запускаются на push и на pull request.

- SAST: `bandit -r .`
- SCA: OWASP Dependency-Check

## Отчёты SAST и SCA

Сюда вставляются скриншоты успешного прогона из вкладки Actions:

- SAST (bandit)
- SCA (OWASP Dependency-Check)
