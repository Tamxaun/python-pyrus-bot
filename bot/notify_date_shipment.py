import json
import hmac
import hashlib
from flask import Request
from pyrus_api_handler import PyrusAPI
from datetime import datetime
from typing import Union
import locale

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")


class NotifyDateShipment:
    def __init__(
        self,
        cache,
        pyrus_secret_key: str,
        pyrus_login: str,
        sentry_sdk,
    ):
        self.pyrus_secret_key = pyrus_secret_key
        self.pyrus_login = pyrus_login
        self.cache = cache
        self.pyrus_api = PyrusAPI(self.cache, self.pyrus_login, self.pyrus_secret_key)
        self.catalog_id = "211864"
        self.sentry_sdk = sentry_sdk

    def _validate_request(self, signature, body):
        # check if signature is set
        if signature is None:
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
        if body is None or not body:
            self.sentry_sdk.capture_message(
                "Debug message: Body is not set ❌", level="debug"
            )
            print("Body is not set ❌")
            return False

        # chech signature
        secret = str.encode(self.pyrus_secret_key)
        digest = hmac.new(secret, msg=body, digestmod=hashlib.sha1).hexdigest()
        return hmac.compare_digest(digest, signature.lower())

    def _find_fields(
        self, fields: dict, name: str, type_field: str = "text"
    ) -> Union[dict, None]:
        for field in fields:
            isNestedField = (
                "value" in field
                and "fields" in field["value"]
                and isinstance(field["value"]["fields"], dict)
            )
            if isNestedField:
                return self._find_fields(field["value"]["fields"], name, type_field)
            if (
                "type" in field
                and field["type"] == type_field
                and "name" in field
                and field["name"] == name
            ):
                return field
        return None

    def _create_message(self, author: dict, date: str, time: str = ""):
        author_link_name = f"<a href='https://pyrus.com/t#{author['id']}'>{author['first_name']} {author['last_name']}</a>"
        date_obj = datetime.strptime(str(date), "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
        formated_time = f", {time}" if time != "" else ""
        formatted_text = "{}<br>Связаться с Клиентом и подтвердить дату забора заказа на сегодня! ({}, {})<br>В случае изменение даты, обязательно изменить поле 'Дата отгрузки' в форме на актуальную дату, а также не забыть сменить даты реализации и ордера в 1С.".format(
            author_link_name, formatted_date, formated_time
        )
        return formatted_text

    def notify(self):
        print("🚚 Notify: Start checking items")
        catalog = self.pyrus_api.get_request(
            f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}"
        )
        catalog_new = {
            "apply": "true",
            "catalog_headers": ["task_id", "timestamp"],
            "items": [],
        }
        date_now = datetime.now().date()

        if catalog:
            # Check if catalog contains items
            # Loop for items
            # Find item that has today date
            # Get Task, format a message, and send this message to task
            # If task has future date, we added this task to a new catalog for new update. Everything else will be deleted
            # POST request to update catalog with new catalog
            if "items" in catalog:
                for item in catalog["items"]:
                    item_id, item_timestamp = item["values"]
                    timestamp = datetime.strptime(str(item_timestamp), "%Y-%m-%d")
                    if timestamp.date() == date_now:
                        task = self.pyrus_api.get_request(
                            f"https://api.pyrus.com/v4/tasks/{item_id}"
                        )
                        formatted_text = self._create_message(
                            author=task["task"]["author"], date=item_timestamp
                        )
                        self.pyrus_api.post_request(
                            url=f"https://api.pyrus.com/v4/tasks/{int(item_id)}/comments",
                            data={"formatted_text": formatted_text},
                        )
                        print(
                            "✅ Notify: Notification is sent. This item will be deleted"
                        )
                    if timestamp.date() > date_now:
                        print("✅ Notify: This item will be added to new catalog")
                        catalog_new["items"].append(
                            {"values": [item_id, item_timestamp]}
                        )
                    if timestamp.date() < date_now:
                        print("⚒️ Notify: This item will be deleted")
                self.pyrus_api.post_request(
                    f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}",
                    data=catalog_new,
                )
                print("✅ Notify: All items are checked")
            else:
                print("😶‍🌫️ Notify: There are no items to check")

    def _update_catalog(self, task_id: str, task_date: str, remove: bool = False):
        catalog = self.pyrus_api.get_request(
            f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}"
        )

        catalog_new = {
            "apply": "true",
            "catalog_headers": ["task_id", "timestamp"],
            "items": [],
        }

        if catalog:
            # Check if catalog contains items
            # If not - add new items
            # Loop for items
            # Find item by task_id and update timestamp
            # Or Remove item (not adding it to new catalog)
            # Or Add new item
            # POST request to update catalog with new catalog
            if "items" in catalog:
                for item in catalog["items"]:
                    item_id, item_timestamp = item["values"]
                    if item_id == task_id:
                        if not remove:
                            catalog_new["items"].append(
                                {"values": [task_id, task_date]}
                            )
                        else:
                            print("🚚 Removing the item by not adding to new catalog")
                    else:
                        catalog_new["items"].append(
                            {"values": [task_id, item_timestamp]}
                        )
            else:
                catalog_new["items"].append({"values": [task_id, task_date]})

                self.pyrus_api.post_request(
                    f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}",
                    catalog_new,
                )

        else:
            self.sentry_sdk.capture_message(
                "Debug message: ❌ Catalog is not found in _update_catalog",
                level="debug",
            )
            print("❌ Catalog is not found")

    def _prepare_response(self, task: dict):

        whole_task = self.pyrus_api.get_request(
            f"https://api.pyrus.com/v4/tasks/{task['id']}"
        )

        fields = whole_task["task"]["fields"]

        #  Find updated date in task in task
        if "comments" in task and "field_updates" in task["comments"][0]:
            fields_updated_in_task = task["comments"][0]["field_updates"]
            updated_field_date_in_task = self._find_fields(
                fields=fields_updated_in_task, name="Дата отгрузки", type_field="date"
            )
            updated_value_date: Union[str, None] = (
                str(updated_field_date_in_task["value"])
                if updated_field_date_in_task is not None
                else None
            )
            updated_date_in_task = (
                datetime.strptime(updated_value_date, "%Y-%m-%d").date()
                if updated_value_date is not None
                else None
            )
        else:
            updated_date_in_task = None

        field_date = self._find_fields(
            fields=fields, name="Дата отгрузки", type_field="date"
        )
        field_time = self._find_fields(
            fields=fields,
            name="Время отгрузки",
            type_field="date",
        )

        value_date: Union[str, None] = (
            field_date["value"] if field_date is not None else None
        )
        value_time: str = field_time["value"] if field_time is not None else ""

        if value_date is None:
            self.sentry_sdk.capture_message(
                f"Debug message: 😢 Body does not contain 'Дата отгрузки'",
                level="debug",
            )
            print("😢 Body does not contain 'Дата отгрузки'")
            return "{}", 200

        date_now = datetime.now().date()
        date_in_task = datetime.strptime(str(value_date), "%Y-%m-%d").date()
        is_today = date_now == date_in_task
        is_today_and_updated_now = (
            updated_date_in_task and date_now == updated_date_in_task
        )

        is_passed = (
            updated_date_in_task
            and date_now > updated_date_in_task
            or date_now > date_in_task
        )

        if is_today_and_updated_now:
            print(
                "Debug message: 📅 This shipment date is today, Sending a message... A notification wouldn't be created."
            )
            formatted_text = self._create_message(
                author=task["task"]["author"], date=value_date, time=value_time
            )
            return (
                '{{ "formatted_text":"{}" }}'.format(formatted_text),
                200,
            )
        elif is_today:
            print(
                "Debug message: 📅 This shipment date is today, Message should be sent previously... A notification wouldn't be created."
            )
            return {}, 200
        elif is_passed:
            print("Debug message: 📅 This shipment date is passed")
            return "{}", 200
        else:
            print(
                "Debug message: 📅 Current shipment date is not today, creating a notification..."
            )
            self._update_catalog(
                task_id=task["id"],
                task_date=value_date,
            )
            return "{}", 200

    def process_request(self, request: Request):
        signature = request.headers.get("X-Pyrus-Sig")
        body = request.data
        if not self._validate_request(signature=signature, body=body):
            self.sentry_sdk.capture_message(
                "Debug message: ❌ Signature is not correct", level="debug"
            )
            print("❌ Signature is not correct")
            return "🚫 Access Denied", 403

        print("✅ Signature_correct")

        try:
            data = json.loads(body)
            if "task" in data:
                print("😉 Body contains 'task'")
                task = data["task"]
                self.sentry_sdk.capture_message(
                    "Debug message: success Body contain 'task'", level="debug"
                )
                self.sentry_sdk.set_context("data", data)
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
