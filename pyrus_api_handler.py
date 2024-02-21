import json
import requests
from typing import Optional


class PyrusAPI:
    print("✅ All required environment variables are set")

    def __init__(self, cache, pyrus_login: str, pyrus_secret_key: str):
        self.cache = cache
        self.token = None
        self.pyrus_login = pyrus_login
        self.pyrus_secret_key = pyrus_secret_key

    def _auth(self) -> str:
        print("⌛ Starting API authentication request to Pyrus")

        try:
            r = requests.get(
                "https://api.pyrus.com/v4/auth",
                params={
                    "login": self.pyrus_login,
                    "security_key": self.pyrus_secret_key,
                },
            )
            r.raise_for_status()  # This line raises an HTTPError if the HTTP request returned an unsuccessful status code
            auth_data: str = json.loads(r.text)
        except requests.exceptions.RequestException as e:
            # Handle any request exceptions
            print(f"❌ API AUTH: Failed to get authentication token from Pyrus: {e}")
            raise Exception(e)

        token = json.loads(auth_data)["access_token"]
        print(f"✅ API AUTH: Success to get authentication token from Pyrus")

        return token

    def get_request(self, url: str) -> dict:
        print("⌛ API GET: Making a  request...")

        if self.token is None:
            print(
                "⚠️ API GET: Authentication token is not in cache, creating a new one..."
            )
            self.token = self._auth()
            print("🫙 API GET: Saving authentication token in cache...")
            self.cache.set("pyrus_auth_token", self.token)
        else:
            print("🫙 API GET: Authentication token in cache")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()  # This line raises an HTTPError if the HTTP request returned an unsuccessful status code
            r_data: dict = json.loads(r.text)
            # Process the response data
            return r_data
        except requests.exceptions.HTTPError as err:
            # Handle 401 Unauthorized error
            if r.status_code == 401:
                self.token = self._auth()
                self.cache.set("pyrus_auth_token", self.token)
                return self.get_request(url)
            else:
                # Handle other HTTP errors
                print(f"⚠️ API GET: HTTP error occurred: {err}")
                raise Exception(err)
        except requests.exceptions.RequestException as e:
            # Handle any request exceptions
            print(f"⚠️ API GET: An error occurred: {e}")
            raise Exception(e)

    def post_request(self, url, data) -> dict:
        print("⌛ API POST: Making request...")

        if self.token is None:
            print(
                "⚠️ API POST: Authentication token is not in cache, creating a new one..."
            )
            self.token = self._auth()
            print("🫙 API POST: Saving authentication token in cache...")
            self.cache.set("pyrus_auth_token", self.token)
        else:
            print("🫙 API GET: Authentication token in cache")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            r = requests.post(url=url, json=data, headers=headers)
            r.raise_for_status()  # This line raises an HTTPError if the HTTP request returned an unsuccessful status code
            r_data = r.json()
            # Process the response data
            return r_data
        except requests.exceptions.HTTPError as err:
            # Handle 401 Unauthorized error
            if r.status_code == 401:
                self.token = self._auth()
                self.cache.set("pyrus_auth_token", self.token)
                return self.post_request(url, data)
            else:
                # Handle other HTTP errors
                print(f"⚠️ API POST: HTTP error occurred: {err}")
                raise Exception(err)
        except requests.exceptions.RequestException as e:
            # Handle any request exceptions
            print(f"⚠️ API POST: An error occurred: {e}")
            raise Exception(e)
