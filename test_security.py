import os
import secrets
import sqlite3
import tempfile
import unittest

os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["SEED_LOGIN"] = "user"
os.environ["SEED_PASSWORD"] = secrets.token_hex(16)

import app as application


class SecurityTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        application.DB_PATH = self.path
        application.init_db()
        self.client = application.app.test_client()
        self.login_name = os.environ["SEED_LOGIN"]
        self.password = os.environ["SEED_PASSWORD"]

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    # пустая регистрация
    def test_register_empty(self):
        response = self.client.post(
            "/auth/register",
            json={"login": "", "password": self.password},
        )
        self.assertEqual(response.status_code, 400)

    # повторная регистрация
    def test_register_exists(self):
        response = self.client.post(
            "/auth/register",
            json={"login": self.login_name, "password": self.password},
        )
        self.assertEqual(response.status_code, 409)

    # sql-инъекция
    def test_register_sqli(self):
        sqli_login = "ra' OR 1=1 --"
        response = self.client.post(
            "/auth/register",
            json={"login": sqli_login, "password": self.password},
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            "/auth/login",
            json={"login": sqli_login, "password": secrets.token_hex(16)},
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            "/auth/login",
            json={"login": sqli_login, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)

    # xss при регистрации
    def test_register_xss(self):
        response = self.client.post(
            "/auth/register",
            json={"login": "<b>y</b>", "password": self.password},
        )
        text = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 201)
        self.assertIn("&lt;b&gt;y&lt;/b&gt;", text)
        self.assertNotIn("<b>", text)

    # хеш пароля
    def test_register_hash(self):
        login_name = "hash-user"
        response = self.client.post(
            "/auth/register",
            json={"login": login_name, "password": self.password},
        )
        self.assertEqual(response.status_code, 201)

        db = sqlite3.connect(self.path)
        stored = db.execute(
            "SELECT password_hash FROM users WHERE login = ?",
            (login_name,),
        ).fetchone()[0]
        db.close()
        self.assertNotEqual(stored, self.password)
        self.assertTrue(stored.startswith("$2"))

    # без токена
    def test_me_no_token(self):
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 401)

    # плохой токен
    def test_me_bad_token(self):
        response = self.client.get("/auth/me", headers={"Authorization": "Bearer bad"})
        self.assertEqual(response.status_code, 401)

    # авторизация
    def test_me(self):
        response = self.client.post(
            "/auth/login",
            json={"login": self.login_name, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["token"]

        response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"login": self.login_name})

    # xss в авторизации
    def test_me_xss(self):
        xss_login = "<b>x</b>"
        response = self.client.post(
            "/auth/register",
            json={"login": xss_login, "password": self.password},
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            "/auth/login",
            json={"login": xss_login, "password": self.password},
        )
        token = response.get_json()["token"]
        text = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        ).get_data(as_text=True)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", text)
        self.assertNotIn("<b>", text)


if __name__ == "__main__":
    unittest.main()
