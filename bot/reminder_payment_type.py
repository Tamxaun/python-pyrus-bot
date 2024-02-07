import json
import hmac
import hashlib
from flask import Request
from pyrus_api_handler import PyrusAPI


class ReminderPaymentType:
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
        self.sentry_sdk = sentry_sdk

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
        text = "Для данного заказа требуется оформить:<br><ul><li>приходный кассовый ордер</li><li>оформить подотчет на Бусырев А.А.</li><ul>"
        comment_text = "{person}<br>{text}".format(person=person, text=text)

        hasUpdatedFields = (
            "comments" in task and "field_updates" in task["comments"][-1]
        )

        self.sentry_sdk.capture_message(
            f"Reminder_peyment_type_bot: task_str: {task['comments'][-1]}", level="info"
        )

        if hasUpdatedFields:
            task_field_updates = task["comments"][-1]["field_updates"][-1]

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
                    return ('{{ "formatted_text":"{}" }}'.format(comment_text), 200)

        return "{}", 200
        # return '{{ "formatted_text":"<code>{}</code>" }}'.format(task), 200
        # task = json.loads(self.body)
        # task_str = json.dumps(task["task"]["comments"][-1])

        # return (
        #     '{{ "text":"{}" }}'.format(task_str),
        #     200,
        # )
        # return '{{ "text":"{}" }}'.format(comment_text, comment_author["id"])

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
