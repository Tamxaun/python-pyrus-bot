import json
import requests


class PyrusAPI:
    print("✅ All required environment variables are set")
    # def __init__(self, cache, pyrus_login: str, pyrus_secret_key: str):
    #     self.cache = cache
    #     self.token = None
    #     self.pyrus_login = pyrus_login
    #     self.pyrus_secret_key = pyrus_secret_key

    # def _auth(self):
    #     print("⌛ Starting API authentication request to Pyrus")

    #     auth_data = requests.get(
    #         "https://api.pyrus.com/v4/auth",
    #         params={"login": self.pyrus_login, "security_key": self.pyrus_secret_key},
    #     ).text

    #     token = json.loads(auth_data)["access_token"]

    #     if token is None:
    #         print("❌ Failed to get authentication token from Pyrus")
    #         return None

    #     print("✅ Success to get authentication token from Pyrus")
    #     return token

    # def get_request(self, url: str) -> dict | None:
    #     print("⌛ API GET: Making a  request...")

    #     if self.token is None:
    #         print(
    #             "⚠️ API GET: Authentication token is not in cache, creating a new one..."
    #         )
    #         self.token = self._auth()
    #         if self.token is None:
    #             print(
    #                 "⚠️ API GET: Authentication token is not ready from _auth() method"
    #             )
    #             return None
    #         print("🫙 API GET: Saving authentication token in cache...")
    #         self.cache.set("pyrus_auth_token", self.token)
    #     else:
    #         print("🫙 API GET: Authentication token in cache")

    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json",
    #     }

    #     r = requests.get(url, headers=headers)
    #     r_data: dict = json.loads(r.text)

    #     if r.status_code == 200:
    #         print("✅ API GET: Response is ready", r.status_code)
    #         return r_data
    #     elif r.status_code == 401:
    #         print("⚠️ API GET: Authentication token is expired")
    #         self.token = self._auth()
    #         self.cache.set("pyrus_auth_token", self.token)
    #         return self.get_request(url)
    #     else:
    #         print("⚠️ API GET Response is not ready", r.status_code)
    #         return None

    # def post_request(self, url, data):
    #     print("⌛ API POST: Making request...")

    #     if self.token is None:
    #         print(
    #             "⚠️ API POST: Authentication token is not in cache, creating a new one..."
    #         )
    #         self.token = self._auth()

    #         if self.token is None:
    #             print(
    #                 "⚠️ API POST: Authentication token is not ready from .auth() method"
    #             )
    #             return None

    #         print("🫙 API POST: Saving authentication token in cache...")
    #         self.cache.set("pyrus_auth_token", self.token)

    #     else:
    #         print("🫙 API GET: Authentication token in cache")

    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json",
    #     }

    #     r = requests.post(url=url, data=data, headers=headers)
    #     r_data = r.json()

    #     if r.status_code == 200:
    #         print("✅ API POST: Response is ready", r.status_code)
    #         return r_data
    #     elif r.status_code == 401:
    #         print("⚠️ API POST: Authentication token is expired")
    #         self.token = self._auth()
    #         self.cache.set("pyrus_auth_token", self.token)
    #         return self.post_request(url, data)
    #     else:
    #         print("⚠️ API POST: Response is not ready", r.status_code)
    #         return None
