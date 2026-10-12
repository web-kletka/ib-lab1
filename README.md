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

### POST /auth/register

Регистрация. Принимает логин и пароль, сохраняет пароль как bcrypt-хеш.

```bash
curl -X POST http://127.0.0.1:5000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"login":"ra","password":"qwerty"}'
```

Ответ: `{"login":"ra"}`. Пустой логин или пароль: `400`. Такой логин уже есть: `409`.

### POST /auth/login

Принимает логин и пароль. При успехе возвращает JWT.

```bash
curl -X POST http://127.0.0.1:5000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"user","password":"password"}'
```

Ответ: `{"token":"<jwt>"}`. Неверный логин или пароль: `401`.

### GET /auth/me

Проверка авторизации. Возвращает логин из токена. Только с токеном.

```bash
curl http://127.0.0.1:5000/auth/me \
  -H 'Authorization: Bearer <token>'
```

Ответ: `{"login":"user"}`. Без токена или с неверным токеном: `401`.

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

Строка вида `user' OR 1=1 --` ищется как обычный логин и не меняет условие запроса. Вставка при регистрации тоже идет через `?`, а не через склейку строки.

### XSS

Пользовательские строки перед отдачей в ответе проходят через `html.escape`. Логин в `POST /auth/register`, `GET /auth/me` и `GET /api/data` экранируется: символы `<`, `>` и кавычки превращаются в HTML-сущности и не читаются как разметка.

### Аутентификация

При регистрации и при входе пароль не пишется в базу открытым текстом: в `users.password_hash` попадает только bcrypt-хеш. На входе он проверяется через `bcrypt.checkpw`. После успешного входа сервер выдает JWT (алгоритм HS256). В токене есть `sub` (логин) и `exp` (срок, 1 час). Секрет подписи берется из переменной `JWT_SECRET`.

`GET /auth/me` и `GET /api/data` закрыты middleware: из заголовка `Authorization` читается схема `Bearer`, токен проверяется `jwt.decode` с явным списком алгоритмов `HS256`. Нет заголовка, битая подпись или истекший срок дают `401`.

## CI/CD

Файл `.github/workflows/ci.yml`. Проверки запускаются на push и на pull request.

- SAST: `bandit -r .`
- SCA: OWASP Dependency-Check

## Отчёты SAST и SCA

Сюда вставляются скриншоты успешного прогона из вкладки Actions:

- SAST (bandit)
- SCA (OWASP Dependency-Check)
