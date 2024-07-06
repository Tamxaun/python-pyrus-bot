import json
import hmac
import hashlib
from flask import Request
from pyrus import client
from pyrus_api_handler import PyrusAPI
from datetime import datetime
from typing import Union
import locale
import uuid


locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")


class CreateReminderComment:
    def __init__(
        self,
        catalog_id: str,
        cache,
        pyrus_secret_key: str,
        pyrus_login: str,
        sentry_sdk,
        traked_fields: Union[dict, None],
    ):
        self.pyrus_secret_key = pyrus_secret_key
        self.pyrus_login = pyrus_login
        self.cache = cache
        self.pyrus_client = client.PyrusAPI(self.pyrus_login, self.pyrus_secret_key)
        self.pyrus_api = PyrusAPI(self.cache, self.pyrus_login, self.pyrus_secret_key)
        self.catalog_id = int(catalog_id)
        self.sentry_sdk = sentry_sdk
        self.tracked_fields = traked_fields

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
        self, fields: dict, field_name: str, field_type: str = "text"
    ) -> Union[dict, None]:
        for field in fields:
            isNestedField = (
                "value" in field
                and isinstance(field["value"], dict)
                and "fields" in field["value"]
                and isinstance(field["value"]["fields"], list)
            )
            if isNestedField:
                return self._find_fields(
                    field["value"]["fields"], field_name, field_type
                )
            if (
                "type" in field
                and field["type"] == field_type
                and "name" in field
                and field["name"] == field_name
            ):
                return field

    def _create_shipment_date_formatted_text(self, author, date: str, time: str = ""):
        id = author["id"]
        first_name = author["first_name"]
        last_name = author["last_name"]
        author_link_name = (
            f"<a href='https://pyrus.com/t#{id}'>{first_name} {last_name}</a>"
        )
        date_obj = datetime.strptime(str(date), "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %d %B, %Y")
        formated_time = f", {time}" if time != "" else ""
        formatted_text = "{}<br>Связаться с Клиентом и подтвердить дату забора заказа на сегодня! ({}{})<br>В случае изменение даты, обязательно изменить поле 'Дата отгрузки' в форме на актуальную дату, а также не забыть сменить даты реализации и ордера в 1С.".format(
            author_link_name, formatted_date, formated_time
        )
        return {"formatted_text": formatted_text}

    def _create_payment_date_formatted_text(self, author):
        id = author["id"]
        first_name = author["first_name"]
        last_name = author["last_name"]
        author_link_name = (
            f"<a href='https://pyrus.com/t#{id}'>{first_name} {last_name}</a>"
        )
        formatted_text = f"{author_link_name}<br>❗Планируемый срок оплаты назначен на сегодня🗓️. Связаться с клиентом и согласовать оплату💵. В случае задержки обязательно указать новую дату оплаты."
        return {"formatted_text": formatted_text}

    def _create_payment_type_comment_data(self):
        person = f"<a href='https://pyrus.com/t#pp486746'>Татьяна Ивановна</a>"
        text = f"Для данного заказа требуется оформить:<ul><li>Приходный кассовый ордер</li><li>Оформить подотчет на Бусырев А.А.</li></ul><br>После чего назначить статус '✅Нал (чек принят в 1С)' в поле 'Тип оплаты / Статус'"
        formatted_text = f"<mark data-color='yellow'>{person}</mark><br>{text}<br>"
        subscribers_added = [
            {
                "id": 486746,
            }
        ]
        return {
            "formatted_text": formatted_text,
            "subscribers_added": subscribers_added,
        }

    def _delete_reminder(self, task_id: str, type_message: str):
        catalog_id = self.catalog_id
        catalog_response = self.pyrus_client.get_catalog(catalog_id)

        if (
            catalog_response
            and hasattr(catalog_response, "items")
            and catalog_response.items
        ):
            items = catalog_response.items
            catalog_updated = {
                "apply": "true",
                "catalog_headers": ["id", "task_id", "timestamp", "message_type"],
                "items": [],
            }

            for item in items:
                item_id, item_task_id, item_timestamp, item_message_type = item[
                    "values"
                ]
                if str(task_id) != str(item_task_id) and str(type_message) != str(
                    item_message_type
                ):
                    catalog_updated["items"].append(item)

            return self.pyrus_api.post_request(
                f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}",
                catalog_updated,
            )

    def _save_or_update_reminder(self, task_id: str, task_date: str, type_message: str):
        catalog_id = self.catalog_id
        catalog_response = self.pyrus_client.get_catalog(catalog_id)
        reminder_exists = False

        if (
            catalog_response
            and hasattr(catalog_response, "items")
            and catalog_response.items
        ):
            items = catalog_response.items
            catalog_updated = {
                "apply": "true",
                "catalog_headers": ["id", "task_id", "timestamp", "message_type"],
                "items": [],
            }

            # Filling catalog
            for item in items:
                item_id, item_task_id, item_timestamp, item_message_type = item[
                    "values"
                ]
                # Find item with the same task_id and type_message to update it
                if str(task_id) != str(item_task_id) and str(type_message) != str(
                    item_message_type
                ):
                    reminder_exists = True
                    catalog_updated["items"].append(
                        {
                            "values": [
                                item_id,
                                item_task_id,
                                task_date,
                                item_message_type,
                            ],
                        }
                    )
                else:
                    # If item not found we adding this item to updated catalog
                    catalog_updated["items"].append(item)

            if not reminder_exists:
                id = uuid.uuid4()
                id_str = str(id)
                catalog_updated["items"].append(
                    {
                        "values": [
                            id_str,
                            task_id,
                            task_date,
                            type_message,
                        ],
                    }
                )

            return self.pyrus_api.post_request(
                f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}",
                catalog_updated,
            )

    def _update_notification(
        self, task_id: str, task_date: str, type_message: str, remove: bool = False
    ):
        catalog = self.pyrus_api.get_request(
            f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}"
        )

        catalog_new = {
            "apply": "true",
            "catalog_headers": ["id", "task_id", "timestamp", "message_type"],
            "items": [],
        }

        if catalog:
            # Check if catalog contains items[]
            # If not - add new items[] with new item
            # If exist Loop over items
            # Find item by task_id and item_message_type to update it
            # Remove item if need it (not adding it to new catalog)
            # Or leave/add item just as it is
            # If item not found we adding this new item to the list catalog_new
            # POST request to update catalog with new catalog
            if "items" in catalog:
                new_item = True
                for item in catalog["items"]:
                    item_id, item_task_id, item_timestamp, item_message_type = item[
                        "values"
                    ]
                    if str(item_task_id) == str(task_id) and str(
                        item_message_type
                    ) == str(type_message):
                        new_item = False
                        if not remove:
                            catalog_new["items"].append(
                                {
                                    "values": [
                                        item_id,
                                        item_task_id,
                                        task_date,
                                        item_message_type,
                                    ]
                                }
                            )
                        else:
                            print("🚚 Removing the item by not adding to new catalog")
                    else:
                        catalog_new["items"].append(
                            {
                                "values": [
                                    item_id,
                                    item_task_id,
                                    item_timestamp,
                                    item_message_type,
                                ]
                            }
                        )
                if new_item:
                    id = uuid.uuid4()
                    id_str = str(id)
                    catalog_new["items"].append(
                        {"values": [id_str, task_id, task_date, type_message]}
                    )
                    print("🚚 Adding the item to new catalog")
            else:
                id = uuid.uuid4()
                id_str = str(id)
                catalog_new["items"].append(
                    {"values": [id_str, task_id, task_date, type_message]}
                )

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

    def _create_notification_from_text_field(
        self,
        field_name: str,
        field_value: str,
        task: dict,
        notification_type: str,
        field_type: str = "text",
    ):
        print("🚚 Creating notification from text field...")
        task_id = task["id"]
        print(f"Task ID: {task_id}")
        time_to_send = datetime.now().date()

        updated_fields_in_task = task["comments"][0]["field_updates"]

        updated_field = self._find_fields(
            updated_fields_in_task, field_name, field_type
        )

        value_updated_field = (
            str(updated_field["value"])
            if updated_field is not None and "value" in updated_field
            else None
        )

        date_now = datetime.now().date()
        time_to_send_is_today = date_now == time_to_send
        value_is_correct = field_value == value_updated_field

        if time_to_send_is_today and value_is_correct:
            if notification_type == "payment_type":
                data = self._create_payment_type_comment_data()

            self.pyrus_api.post_request(
                url=f"https://api.pyrus.com/v4/tasks/{task_id}/comments",
                data=data,
            )

    def _create_notification_from_date_field(
        self,
        field_name: str,
        task: dict,
        notification_type: str,
        field_type: str = "date",
    ):
        print("🚚 Creating notification from field...")
        task_id = task["id"]
        print(f"Task ID: {task_id}")
        updated_value_date = None
        updated_date_in_task = None

        # We check if there any fields that was updated
        # Find field in task["comments"][0]["field_updates"] from task response
        if "comments" in task and "field_updates" in task["comments"][0]:
            print("Debug message: ✅ This task has comments and field_updates")

            updated_fields_in_task = task["comments"][0]["field_updates"]

            updated_field_date_in_task = self._find_fields(
                updated_fields_in_task, field_name, field_type
            )
            updated_value_date: Union[str, None] = (
                str(updated_field_date_in_task["value"])
                if updated_field_date_in_task is not None
                and "value" in updated_field_date_in_task
                else None
            )
            updated_date_in_task = (
                datetime.strptime(updated_value_date, "%Y-%m-%d").date()
                if updated_value_date is not None
                else None
            )

        else:
            print(
                "Debug message: ❌ This task doesn't have any comments or field_updates"
            )

        if updated_date_in_task is not None and updated_value_date is not None:
            date_now = datetime.now().date()
            field_date_is_today = date_now == updated_date_in_task
            field_date_is_passed = date_now > updated_date_in_task
            field_date_in_future = updated_date_in_task > date_now

            if field_date_is_today:
                print(
                    "Debug message: 📅 This shipment date is today, Sending a message... A notification wouldn't be created."
                )
                if notification_type == "shipment_date":
                    data = self._create_shipment_date_formatted_text(
                        author=task["author"], date=updated_value_date
                    )
                elif notification_type == "payment_date":
                    data = self._create_payment_date_formatted_text(
                        author=task["author"]
                    )

                self.pyrus_api.post_request(
                    url=f"https://api.pyrus.com/v4/tasks/{task_id}/comments",
                    data=data,
                )

                self._update_notification(
                    task_id=task["id"],
                    task_date=updated_value_date,
                    type_message=notification_type,
                    remove=True,
                )
            elif field_date_is_passed:
                print("Debug message: 📅 This shipment date is passed")
            elif field_date_in_future:
                print(
                    "Debug message: 📅 Current shipment date is not today, creating a notification..."
                )
                self._update_notification(
                    task_id=task["id"],
                    task_date=updated_value_date,
                    type_message=notification_type,
                )
        else:
            print(
                f"Debug message: ❌ The field '{field_name}' is not found in task['comments'][0]['field_updates']"
            )

    def _handle_response(self, task: dict):
        print("🚚 Hadling the response...")
        self._create_notification_from_date_field(
            "Дата отгрузки", task, "shipment_date", field_type="date"
        )
        self._create_notification_from_date_field(
            "Дата планируемой оплаты", task, "payment_date", field_type="date"
        )
        self._create_notification_from_text_field(
            "Тип оплаты / Статус", "✅Нал (чек)", task, "payment_type", "text"
        )

        return "{}", 200

    def process_request(self, request: Request):
        print("🔐 Processing request...")
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
                task = data["task"]
                return self._handle_response(task)
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
