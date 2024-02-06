import json
from flask import Request
from pyrus_api_handler import PyrusAPI


class ReminderPaymentType:
    def __init__(
        self, cache, request: Request, pyrus_secret_key: str, pyrus_login: str
    ):
        self.pyrus_secret_key = pyrus_secret_key
        self.pyrus_login = pyrus_login
        self.request = request
        self.cache = cache
        self.pyrus_api = PyrusAPI(self.cache, self.pyrus_login, self.pyrus_secret_key)

    def _validate_request(self):
        if self.request.headers.get("X-Pyrus-Sig") is None:
            print("⛔ The request does not have the X-Pyrus-Sig.")
            print(self.request.headers)
            return False
        if self.pyrus_secret_key is None or self.request.data is None:
            print(f"Body is {'set ✅' if self.request.data != None else 'not set ❌'}")
            print(
                f"Secret is {'set ✅' if self.pyrus_secret_key != None else 'not set ❌'}"
            )
            return False
        return True

    def _prepare_response(self):
        print("⌛ Preparing response")

        task = json.loads(self.request.data)
        task_field_updates = task["comments"]["task_field_updates"]

        print("👋 task", task)

        person = f"<a href='https://pyrus.com/t#pp486746'>Татьяна Ивановна</a>"
        text = "Для данного заказа требуется оформить:<br><ul><li>приходный кассовый ордер</li><li>оформить подотчет на Бусырев А.А.</li><ul>"
        comment_text = "{person}<br>{text}".format(person=person, text=text)

        for field in task_field_updates:
            isPaymenType = "name" in field and field["name"] == "Тип оплаты / Статус"
            isCorrectPaymenType = (
                "value" in field
                and isinstance(field["value"], dict)
                and "choice_names" in field["value"]
                and field["value"]["choice_names"][0] == "✅Нал (чек)"
            )

            if isPaymenType and isCorrectPaymenType:
                return ('{{ "formatted_text":"{}" }}'.format(comment_text), 200)

        return "{}", 200

    def process_request(self):
        if not self._validate_request():
            return "🚫 Access Denied", 403

        print("✅ Signature_correct")
        return self._prepare_response()
