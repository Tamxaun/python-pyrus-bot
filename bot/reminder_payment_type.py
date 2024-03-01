import json
import hmac
import hashlib
from flask import Request
from pyrus_api_handler import PyrusAPI

"""
Description of the class

"""


class ReminderPaymentType:
    def __init__(
        self, cache, request: Request, pyrus_secret_key: str, pyrus_login: str
    ):
        self.pyrus_secret_key = pyrus_secret_key
        self.pyrus_login = pyrus_login
        self.request = request
        self.body = self.request.data
        self.signature = self.request.headers.get("X-Pyrus-Sig")
        self.cache = cache
        self.pyrus_api = PyrusAPI(self.cache, self.pyrus_login, self.pyrus_secret_key)

    def _validate_request(self):
        # check if signature is set
        if self.signature is None:
            print("⛔ The request does not have the X-Pyrus-Sig.")
            return False
        # check if secret is set
        if self.pyrus_secret_key is None or not self.pyrus_secret_key:
            print("Secret is not set ❌")
            return False
        # check if body is set
        if self.body is None or not self.body:
            print("Body is not set ❌")
            return False

        # chech signature
        secret = str.encode(self.pyrus_secret_key)
        digest = hmac.new(secret, msg=self.body, digestmod=hashlib.sha1).hexdigest()
        return hmac.compare_digest(digest, self.signature.lower())
        # return True

    def _prepare_response(self, task: dict):
        print("⌛ Preparing response")

        person = f"<a href='https://pyrus.com/t#pp486746'>Татьяна Ивановна</a>"
        text = f"Для данного заказа требуется оформить:<ul><li>Приходный кассовый ордер</li><li>Оформить подотчет на Бусырев А.А.</li></ul><br>После чего назначить статус '✅Нал (чек принят в 1С)' в поле 'Тип оплаты / Статус'"
        comment_text = f"<mark data-color='yellow'>{person}</mark><br>{text}<br>"
        subscribers_added = [
            {
                "id": 486746,
            }
        ]

        hasUpdatedFields = (
            "comments" in task and "field_updates" in task["comments"][-1]
        )

        if hasUpdatedFields:
            task_field_updates = task["comments"][-1]["field_updates"]

            for field in task_field_updates:
                isPaymenType = (
                    "name" in field and field["name"] == "Тип оплаты / Статус"
                )
                isCorrectPaymenType = (
                    "value" in field
                    and isinstance(field["value"], dict)
                    and "choice_names" in field["value"]
                    and field["value"]["choice_names"][-1] == "✅Нал (чек)"
                )

                if isPaymenType and isCorrectPaymenType:
                    return (
                        '{{ "formatted_text":"{}", "subscribers_added": {} }}'.format(
                            comment_text, subscribers_added
                        ),
                        200,
                    )

        return "{}", 200

    def process_request(self):
        if not self._validate_request():
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
                return "🚫 Access Denied", 403
        except json.JSONDecodeError:
            print("😢 Body is not valid JSON")
            return "🚫 Access Denied", 403
