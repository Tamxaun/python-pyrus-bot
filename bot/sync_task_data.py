import json
import hmac
import hashlib
from flask import Request
from pyrus import client
from pyrus_api_handler import PyrusAPI
from pyrus.models.entities import FormField, Title
from typing import Union, List


class SyncTaskData:
    def __init__(
        self,
        cache,
        pyrus_secret_key: str,
        pyrus_login: str,
        sentry_sdk,
        traked_fields,
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

        if "comments" in task and "field_updates" in task["comments"][0]:
            print(f"✅ Task has comments and field_updates")
            task_fields_updated: dict = task["comments"][0]["field_updates"]

            if isinstance(self.tracked_fields, dict):
                for field_traked, fields in self.tracked_fields.items():
                    print(f"✅ Tracked fields {fields[0]}, {fields[1]}")
                    task_tracked_main_field_found = self._find_field_by_name(
                        task_fields_updated, field_traked, "form_link"
                    )
                    task_tracked_field_one_found = self._find_field_by_name(
                        task_fields_updated, fields[0], "text"
                    )
                    print(
                        f"✅task_tracked_main_field_found {task_tracked_main_field_found}"
                    )
                    print(
                        f"✅task_tracked_field_one_found {task_tracked_field_one_found}"
                    )
                    if (
                        task_tracked_main_field_found is not None
                        and task_tracked_field_one_found is not None
                        and isinstance(task_tracked_field_one_found, dict)
                        and isinstance(task_tracked_main_field_found, dict)
                    ):
                        value_field_to_update = task_tracked_field_one_found["value"]
                        id_task_to_update = task_tracked_main_field_found["value"][
                            "task_id"
                        ]
                        field_name_task_to_update: str = fields[1]
                        task_to_update = self.pyrus_client.get_task(
                            id_task_to_update
                        ).task

                        if (
                            task_to_update is not None
                            and task_to_update.fields is not None
                        ):
                            field_task_to_update = self._find_field_by_name(
                                field_name=field_name_task_to_update,
                                fields=task_to_update.fields,
                            )
                            if isinstance(field_task_to_update, FormField):
                                data_to_update_field_task = {
                                    "field_updates": [
                                        {
                                            "id": field_task_to_update.id,
                                            "value": value_field_to_update,
                                        }
                                    ]
                                }
                                self.pyrus_client.comment_task(
                                    task_id=id_task_to_update,
                                    task_comment_request=data_to_update_field_task,
                                )
                        print(
                            f"✅ Tracked task_tracked_main_field_found {task_tracked_main_field_found}"
                        )
                        print(
                            f"✅ Tracked task_tracked_field_one_found {task_tracked_field_one_found}, {fields}"
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
