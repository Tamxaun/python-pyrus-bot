import os
from flask import Flask
from flask import request
from flask_caching import Cache

from pyrus_api_handler import PyrusAPI

# from bot.reminder_step import ReminderStep
# from bot.reminder_payment_type import ReminderPaymentType


# Initialize the Flask app
app = Flask(__name__)

# Check if the app is running in debug mode
# from dotenv import load_dotenv
# load_dotenv()

# Load environment variables
RS_LOGIN = os.getenv("RS_LOGIN")
RS_SECRET_KEY = os.getenv("RS_SECRET_KEY")
RPT_LOGIN = os.getenv("RPT_LOGIN")
RPT_SECRET_KEY = os.getenv("RPT_SECRET_KEY")

# if (
#     RS_LOGIN is None
#     or RS_SECRET_KEY is None
#     or RPT_LOGIN is None
#     or RPT_SECRET_KEY is None
# ):
#     print("❌ All required environment variables must be set")
#     exit(1)  # Exit the application if any required environment variable is missing
# else:
#     print("✅ All required environment variables are set")

# Configure the Flask app
config = {"DEBUG": False, "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300}
app.config.from_mapping(config)
port = int(os.environ.get("PORT", 5000))

# Initialize the cache
cache = Cache(app)

# Initialize the Pyrus API
# pyrus_api = PyrusAPI(cache, RS_LOGIN, RS_SECRET_KEY)


@app.route("/", methods=["GET"])
def index_page():
    # data = pyrus_api.get_request("https://api.pyrus.com/v4/tasks/201302847")
    # if data is not None:
    #     task = data["task"]
    #     task_fields = task["fields"]
    #     print("🍿task_fields", task_fields)

    # person = f"<a href='https://pyrus.com/t#pp486746'>Татьяна Ивановна</a>"
    # text = "Для данного заказа требуется оформить:<br><ul><li>приходный кассовый ордер</li><li>оформить подотчет на Бусырев А.А.</li><ul>"
    # comment_text = "{person}<br>{text}".format(person=person, text=text)

    # for field in task_fields:
    #     isPaymenType = "name" in field and field["name"] == "Тип оплаты / Статус"
    #     isCorrectPaymenType = (
    #         "value" in field
    #         and isinstance(field["value"], dict)
    #         and "choice_names" in field["value"]
    #         and field["value"]["choice_names"][0] == "✅Нал (чек)"
    #     )

    #     if isPaymenType and isCorrectPaymenType:
    #         return ('{{ "formatted_text":"{}" }}'.format(comment_text), 200)

    return "✅ Server is ready"


# @app.route("/step-reminder", methods=["GET"])
# def reminder_step_page():
#     reminder_step_page = ReminderStep(
#         cache=cache,
#         request=request,
#         pyrus_secret_key=RS_SECRET_KEY,
#         pyrus_login=RS_LOGIN,
#     )
#     return reminder_step_page.process_request()


# @app.route("/reminder-payment-type", methods=["GET"])
# def reminder_peyment_type_page():
#     reminder_peyment_type = ReminderPaymentType(
#         cache=cache,
#         request=request,
#         pyrus_secret_key=RPT_SECRET_KEY,
#         pyrus_login=RPT_LOGIN,
#     )
#     return reminder_peyment_type.process_request()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    print("✅ Server is ready")
