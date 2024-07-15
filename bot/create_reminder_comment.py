import json
import hmac
import hashlib
from flask import Request
from pyrus import client
from pyrus_api_handler import PyrusAPI
from datetime import datetime
from pyrus.models.entities import CatalogItem
from typing import Union, TypedDict, List, Dict, Optional
import locale
import uuid


locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")


class TrackedFieldsType(TypedDict):
    text: Dict[str, str]
    date: List[str]


class CreateReminderComment:
    def __init__(
        self,
        catalog_id: str,
        cache,
        pyrus_secret_key: str,
        pyrus_login: str,
        sentry_sdk,
        traked_fields: TrackedFieldsType,
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

    def _create_shipment_date_comment_data(self, author, date: str, time: str = ""):
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

    def _create_payment_date_comment_data(self, author):
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

        if catalog_response.items is not None:
            items: Optional[List[CatalogItem]] = catalog_response.items
            catalog_updated = {
                "apply": "true",
                "catalog_headers": ["id", "task_id", "timestamp", "message_type"],
                "items": [],
            }

            for item in items:
                if item.values is not None:
                    item_id, item_task_id, item_timestamp, item_message_type = (
                        item.values
                    )

                    if str(task_id) != str(item_task_id) and str(type_message) != str(
                        item_message_type
                    ):
                        catalog_updated["items"].append({"values": [item.values]})

            return self.pyrus_api.post_request(
                f"https://api.pyrus.com/v4/catalogs/{self.catalog_id}",
                catalog_updated,
            )

    def _save_or_update_reminder(self, task_id: str, task_date: str, type_message: str):
        catalog_id = self.catalog_id
        catalog_response = self.pyrus_client.get_catalog(catalog_id)
        reminder_exists = False

        if catalog_response.items is not None:
            items: Optional[List[CatalogItem]] = catalog_response.items
            catalog_updated = {
                "apply": "true",
                "catalog_headers": ["id", "task_id", "timestamp", "message_type"],
                "items": [],
            }

            # Filling catalog
            for item in items:
                if item.values is not None:
                    item_id, item_task_id, item_timestamp, item_message_type = (
                        item.values
                    )

                    # Find item with the same task_id and type_message to update it
                    if str(task_id) == str(item_task_id) and str(type_message) == str(
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
                        catalog_updated["items"].append(
                            {
                                "values": [
                                    item_id,
                                    item_task_id,
                                    item_timestamp,
                                    item_message_type,
                                ]
                            }
                        )

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

    def _process_text_field(
        self,
        task_id: str,
        task_field: dict,
        tracked_field_value: str,
        type_message: str,
    ):
        print("🚚 Processing text field...")

        task_field_value = (
            str(task_field["value"])
            if task_field is not None and "value" in task_field
            else None
        )

        value_is_correct = task_field_value == tracked_field_value

        if type_message == "payment_type" and value_is_correct:
            data = self._create_payment_type_comment_data()

            print(
                f"📅 Debug message _process_text_field, data: {data} Type message: {type_message}"
            )

            self.pyrus_api.post_request(
                url=f"https://api.pyrus.com/v4/tasks/{task_id}/comments",
                data=data,
            )

    def _process_data_field(
        self,
        task_id: str,
        author: dict,
        task_field: dict,
        type_message: str,
    ):
        print("🚚 Processing date field...")

        task_field_date_value: Union[str, None] = (
            str(task_field["value"])
            if task_field is not None and "value" in task_field
            else None
        )
        task_field_date = (
            datetime.strptime(task_field_date_value, "%Y-%m-%d").date()
            if task_field_date_value is not None
            else None
        )

        if task_field_date is not None and task_field_date_value is not None:
            date_now = datetime.now().date()
            is_today = date_now == task_field_date
            is_passed = date_now > task_field_date
            in_future = task_field_date > date_now

            if is_today:
                if type_message == "shipment_date":
                    data = self._create_shipment_date_comment_data(
                        author=author, date=task_field_date_value
                    )
                elif type_message == "payment_date":
                    data = self._create_payment_date_comment_data(author=author)

                print(
                    f"📅 Debug message _process_data_field: This shipment date is today, Sending a message... A notification wouldn't be created. Type message: {type_message}. Data: {data}"
                )

                self.pyrus_api.post_request(
                    url=f"https://api.pyrus.com/v4/tasks/{task_id}/comments",
                    data=data,
                )

                self._delete_reminder(
                    task_id=task_id,
                    type_message=type_message,
                )
            elif is_passed:
                print(
                    f"📅 Debug message: This shipment date is passed. Type message: {type_message}"
                )
            elif in_future:
                print(
                    f"📅 Debug message: Current shipment date is not today, creating a notification. Type message: {type_message}"
                )

                self._save_or_update_reminder(
                    task_id=task_id,
                    task_date=task_field_date_value,
                    type_message=type_message,
                )

    def _handle_response(self, task: dict):
        print("🚚 Hadling the response...")

        if "comments" in task and "field_updates" in task["comments"][0]:
            print(f"✅ Task has comments and field_updates")
            task_fields_updated = task["comments"][0]["field_updates"]

            if isinstance(self.tracked_fields, dict):
                for field_type, fields in self.tracked_fields.items():
                    if field_type == "text" and isinstance(fields, dict):
                        for field_name, field_value in fields.items():
                            task_field_found = self._find_fields(
                                task_fields_updated, field_name, field_type
                            )
                            if task_field_found is not None:
                                self._process_text_field(
                                    task_id=task["id"],
                                    task_field=task_field_found,
                                    tracked_field_value=field_value,
                                    type_message="payment_type",
                                )
                            print(
                                f"✅ Field Type: {field_type}, Field Name: {field_name}, Field Value: {field_value}, Task Field Founed: {task_field_found}"
                            )  # Field Name: Тип оплаты / Статус, Field Value: ✅Нал (чек)
                    elif field_type == "date" and isinstance(fields, list):
                        for field_name in fields:
                            task_field_found = self._find_fields(
                                task_fields_updated, field_name, field_type
                            )
                            if task_field_found is not None:
                                type_message = (
                                    "shipment_date"
                                    if field_name == "Дата отгрузки"
                                    else "payment_date"
                                )
                                self._process_data_field(
                                    task_id=task["id"],
                                    author=task["author"],
                                    task_field=task_field_found,
                                    type_message=type_message,
                                )
                            print(
                                f"✅ Field Type: {field_type}, Field Name: {field_name}, Task Field Founed: {task_field_found}"
                            )  # Field Name: Дата отгрузки, Field Name: Дата планируемой оплаты

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
