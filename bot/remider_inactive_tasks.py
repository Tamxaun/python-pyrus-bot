import json
import hmac
import hashlib
from flask import Request
from pyrus_api_handler import PyrusAPI
from apscheduler.schedulers.background import BackgroundScheduler
import datetime


class RemiderInactiveTasks:
    def __init__(
        self,
        cache,
        request: Request,
        pyrus_secret_key: str,
        pyrus_login: str,
        sentry_sdk,
    ):
        self.pyrus_secret_key = pyrus_secret_key
        self.pyrus_login = pyrus_login
        self.request = request
        self.body = self.request.data
        self.signature = self.request.headers.get("X-Pyrus-Sig")
        self.cache = cache
        self.pyrus_api = PyrusAPI(self.cache, self.pyrus_login, self.pyrus_secret_key)
        self.catalog_id = "211552"
        self.sentry_sdk = sentry_sdk

    def _validate_request(self):
        # check if signature is set
        if self.signature is None:
            self.sentry_sdk.capture_message(
                "⛔ The request does not have the X-Pyrus-Sig.", level="debug"
            )
            print("⛔ The request does not have the X-Pyrus-Sig.")
            return False
        # check if secret is set
        if self.pyrus_secret_key is None or not self.pyrus_secret_key:
            self.sentry_sdk.capture_message(
                "Debug message: Secret is not set ❌", level="debug"
            )
            print("Secret is not set ❌")
            return False
        # check if body is set
        if self.body is None or not self.body:
            self.sentry_sdk.capture_message(
                "Debug message: Body is not set ❌", level="debug"
            )
            print("Body is not set ❌")
            return False

        # chech signature
        secret = str.encode(self.pyrus_secret_key)
        digest = hmac.new(secret, msg=self.body, digestmod=hashlib.sha1).hexdigest()
        return hmac.compare_digest(digest, self.signature.lower())

    def check_for_inactive_task(self):
        now = datetime.datetime.now()
        try:
            catalog = self.pyrus_api.get_request(
                f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}"
            )
        except Exception as e:
            self.sentry_sdk.capture_message(e, level="error")
        if catalog and "items" in catalog:
            items = catalog["items"]
            for item in items:
                task_id, timestamp = item["values"]
                if (now - timestamp).days >= 10:
                    # Отправьте уведомление здесь
                    taks = self.pyrus_api.get_request(
                        f"https://api.pyrus.com/v4/tasks/{task_id}"
                    )
                    if taks:
                        author = taks["author"]
                        self.pyrus_api.post_request(
                            f"https://api.pyrus.com/v4/tasks/{task_id}/comments",
                            {
                                "formatted_text": f"<a href='https://pyrus.com/t#pp{author.get('id')}'>{author.get('name')}</a><br>Задача простаивает более 10 дней. Требуется либо её завершить либо довести до логического завершения, используем при этом функцию 'Напомнить'. Каждая задача в Pyrus должны завершаться. Незавершённые задачи не допускаются (исключением являются задачи, которые имеют системный характер).",
                            },
                        )
                        self._update_tasks(task_id)
            print("✅ Tasks checked")
            return "{}", 200
        else:
            print("❌ Didn't get catalog")
            self.sentry_sdk.capture_message(
                f"Debug message: ❌ Didn't get catalog in check_for_inactive_task, {now}, {catalog}",
                level="debug",
            )
            return "❌ Didn't get catalog", 400

    def _update_tasks(self, task_id: str, remove: bool = False):
        try:
            catalog = self.pyrus_api.get_request(
                f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}"
            )
        except Exception as e:
            self.sentry_sdk.capture_message(e, level="error")
        catalog_new = [
            {
                "apply": "true",
                "catalog_headers": ["task_id", "timestamp"],
                "items": [],
            }
        ]

        if catalog:
            # Check if catalog contains items
            # If not - add new item
            # Loop for items
            # Find item by task_id and update timestamp
            # Or Remove item (not adding it to new catalog)
            # Or Add new item
            # POST request to update catalog with new catalog
            if "items" in catalog:
                items = catalog["items"]
                for item in items:
                    if item["values"] and item["values"][0] == task_id:
                        if not remove:
                            print("🚚 Updating the task")
                            item["values"][1] = datetime.datetime.now()
                            catalog_new[0]["items"].append({item["values"]})
                        else:
                            print("🚚 Removing the task by not adding to new catalog")
                    else:
                        print("🚚 Adding the task")
                        catalog_new[0]["items"].append(
                            {"values": [task_id, datetime.datetime.now()]}
                        )
            else:
                catalog_new[0]["items"].append(
                    {"values": [task_id, datetime.datetime.now()]}
                )
            self.pyrus_api.post_request(
                f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}",
                json.dumps(catalog_new),
            )
        else:
            self.sentry_sdk.capture_message(
                "Debug message: ❌ Catalog is not found in _update_tasks",
                level="debug",
            )
            print("❌ Catalog is not found")

    def _prepare_response(self, task: dict):
        task_id = task.get("id")
        is_task_closed = (
            len(task["comments"]) > 0
            and task["comments"][0].get("action") == "finished"
        )
        if task_id:
            if is_task_closed:
                print("🚚 Task is complete. Removing it")
                self._update_tasks(task_id, remove=True)
            else:
                print("🚚 Task is not complete. Updating it or adding if isn't exist")
                self._update_tasks(task_id)
            print("✅ Signal received")
            return "{}", 200
        else:
            print("❌ Didn't get task_id")
            self.sentry_sdk.capture_message(
                "Debug message: ❌ Didn't get task_id", level="debug"
            )
            return "🚫 Access Denied", 400

    def process_request(self):
        if not self._validate_request():
            self.sentry_sdk.capture_message(
                "Debug message: ❌ Signature is not correct", level="debug"
            )
            print("❌ Signature is not correct")
            return "🚫 Access Denied", 403

        print("✅ Signature_correct")

        try:
            data = json.loads(self.body)
            if "task" in data:
                print("😉 Body contains 'task'")
                task = data["task"]
                return self._prepare_response(task)
            else:
                print("😢 Body does not contain 'task'")
                self.sentry_sdk.capture_message(
                    "Debug message: 😢 Body does not contain 'task'", level="debug"
                )
                return "🚫 Access Denied", 403
        except json.JSONDecodeError:
            self.sentry_sdk.capture_message(
                "Debug message: 😢 Body is not valid JSON", level="debug"
            )
            print("😢 Body is not valid JSON")
            return "🚫 Access Denied", 403
