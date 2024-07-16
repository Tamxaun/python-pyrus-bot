import json
import hmac
import hashlib
from flask import Request
from pyrus import client
from pyrus_api_handler import PyrusAPI
from pyrus.models.entities import FormField, Title
from pyrus.models.requests import TaskCommentRequest
from typing import Union, List


class SyncTaskData:
    def __init__(
        self,
        cache,
        pyrus_secret_key: str,
        pyrus_login: str,
        sentry_sdk,
        traked_fields: dict,
    ):
        self.pyrus_secret_key = pyrus_secret_key
        self.pyrus_login = pyrus_login
        self.cache = cache
        self.pyrus_client = client.PyrusAPI(self.pyrus_login, self.pyrus_secret_key)
        self.pyrus_api = PyrusAPI(self.cache, self.pyrus_login, self.pyrus_secret_key)
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

    def _find_field_by_name(
        self,
        fields: Union[dict, List[FormField]],
        field_name: str,
        field_type: str = "text",
    ) -> Union[dict, FormField, None]:
        for field in fields:
            if isinstance(field, dict):
                if (
                    "value" in field
                    and isinstance(field["value"], dict)
                    and "fields" in field["value"]
                    and isinstance(field["value"]["fields"], list)
                ):
                    nested_fields = field["value"]["fields"]
                    found_field = self._find_field_by_name(
                        nested_fields, field_name, field_type
                    )
                    if found_field is not None:
                        return found_field
                if (
                    "type" in field
                    and field["type"] == field_type
                    and "name" in field
                    and field["name"] == field_name
                ):
                    return field
            elif isinstance(field, FormField):
                if (
                    field.value is not None
                    and isinstance(field.value, Title)
                    and field.value.fields is not None
                    and isinstance(field.value.fields, List)
                ):
                    nested_fields = field.value.fields
                    found_field = self._find_field_by_name(
                        nested_fields, field_name, field_type
                    )
                    if found_field is not None:
                        return found_field
                if (
                    field.type is not None
                    and field.type == field_type
                    and field.name is not None
                    and field.name == field_name
                ):
                    return field

    def _handle_response(self, task: dict):
        print("🚚 Hadling the response...")

        if (
            "comments" in task
            and "field_updates" in task["comments"][0]
            and "fields" in task
        ):
            print(f"✅ Task has comments and field_updates")
            task_fields_updated: dict = task["comments"][0]["field_updates"]
            task_fields: dict = task["fields"]

            for field_traked, fields in self.tracked_fields.items():

                print(
                    f"🔎 Ищем в обновленных, поле, для опрделения номера задачи, где будем сихронизировать значения, в текущей задаче с полем — '{fields[0]}' и в найденой задаче с полем — '{fields[1]}'"
                )
                task_tracked_main_updated_field_found = self._find_field_by_name(
                    task_fields_updated, field_traked, "form_link"
                )
                if task_tracked_main_updated_field_found is None:
                    print(
                        f"❌ В списке обновленных полей, поле для определения задачи — '{field_traked}' не найдено"
                    )
                    print(
                        f"🔎 Ищем в списке полей, поле, для опрделения номера задачи, где будем сихронизировать значения, в текущей задаче с полем — '{fields[0]}' и в найденой задаче с полем — '{fields[1]}'"
                    )
                    task_tracked_main_updated_field_found = self._find_field_by_name(
                        task_fields, field_traked, "form_link"
                    )
                print(
                    f"➡️  Значение поля для опрделения задачи — {f'✅ Найдено, поле: {task_tracked_main_updated_field_found}' if task_tracked_main_updated_field_found else f'❌ Не найдено, список обновленных полей: {task_fields_updated}'}"
                )

                print(
                    f"🔎 Ищем в обновленных, поле '{fields[0]}', для сихронизиции значения в текущей задаче."
                )
                task_tracked_updated_field_one_found = self._find_field_by_name(
                    task_fields_updated, fields[0], "text"
                )
                print(
                    f"➡️  Значение поля '{fields[0]}' для сихронизации значения c другой задачей — {f'✅ Найдено, поле: {task_tracked_updated_field_one_found}' if task_tracked_updated_field_one_found else f'❌ Не найдено'}"
                )

                if (
                    task_tracked_main_updated_field_found is not None
                    and task_tracked_updated_field_one_found is not None
                    and isinstance(task_tracked_updated_field_one_found, dict)
                    and isinstance(task_tracked_main_updated_field_found, dict)
                ):
                    if "value" not in task_tracked_updated_field_one_found:
                        print(
                            "❌ Значение (value) в поле для сихронизации значения c другой задачей не найдено"
                        )
                        continue

                    value_field_to_update = task_tracked_updated_field_one_found[
                        "value"
                    ]
                    id_task_to_update = task_tracked_main_updated_field_found["value"][
                        "task_id"
                    ]

                    print(f"➡️  Получаем связанную задачу, id:'{id_task_to_update}'")
                    field_name_task_to_update: str = fields[1]
                    responce_task_to_update = self.pyrus_client.get_task(
                        id_task_to_update
                    )
                    task_to_update = self.pyrus_client.get_task(id_task_to_update).task

                    if task_to_update is not None and task_to_update.fields is not None:
                        print(
                            f"➡️  Задачу получили, id:'{id_task_to_update}'✅, находим в задаче поле '{field_name_task_to_update}'"
                        )
                        field_task_to_update = self._find_field_by_name(
                            field_name=field_name_task_to_update,
                            fields=task_to_update.fields,
                        )
                        if (
                            isinstance(field_task_to_update, FormField)
                            and field_task_to_update
                            and field_task_to_update.value is not None
                        ):
                            print(
                                f"➡️  Поле для обновления задаче в связанноей задачи: '✅ Найдено, поле: {field_task_to_update.value}'"
                            )
                            data_to_update_field_task: TaskCommentRequest = (
                                TaskCommentRequest(
                                    text=f"Значение поля '{field_name_task_to_update}' было сихронизированно с после '{fields[0]}' из задачи '{task['text']}'",
                                    field_updates=[
                                        {
                                            "id": field_task_to_update.id,
                                            "value": value_field_to_update,
                                        }
                                    ],
                                )
                            )
                            comment_task = self.pyrus_client.comment_task(
                                task_id=id_task_to_update,
                                task_comment_request=data_to_update_field_task,
                            )
                            if comment_task.error is None:
                                print(f"➡️  Задача '{id_task_to_update}' обновлена ✅")
                            else:
                                print(
                                    f"❌  Ошибка обновления задачи '{id_task_to_update}': error '{comment_task.error}', error_code '{comment_task.error_code}', original_response '{comment_task.original_response}', task '{comment_task.task}'"
                                )
                                self.sentry_sdk.capture_message(
                                    f"Webhook Sync Task Data Debug: Ошибка обновления задачи '{id_task_to_update}': '{comment_task.error}'",
                                    level="error",
                                )
                        else:
                            print(
                                f"➡️  Поле для обновления задаче в связанноей задачи: ❌ Не найдено"
                            )
                    else:
                        print(
                            f"❌  Не удалось получить задачу '{id_task_to_update}', error: {responce_task_to_update.error}, error_code: {responce_task_to_update.error_code}, original_response: {responce_task_to_update.original_response}, task: {responce_task_to_update.task}"
                        )
                        self.sentry_sdk.capture_message(
                            f"Webhook Sync Task Data Debug: Ошибка палучения задачи '{id_task_to_update}': '{responce_task_to_update.error}'",
                            level="error",
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
