import os
from dotenv import load_dotenv
from flask import Flask
from flask import request
from flask_caching import Cache
from flask_apscheduler import APScheduler
from pyrus_api_handler import PyrusAPI
from bot.reminder_step import ReminderStep

# from bot.reminder_payment_type import ReminderPaymentType
from bot.sync_task_data import SyncTaskData

# from bot.remider_inactive_tasks import RemiderInactiveTasks
from bot.create_reminder_comment import CreateReminderComment, TrackedFieldsType
from notify_in_pyrus_task import Notification_in_pyrus_task
import sentry_sdk


# Initialize the Flask app
app = Flask(__name__)

# Check if the app is running in debug mode
if app.debug:
    print("Flask app is running in debug mode")
    os.environ["APP_ENV"] = "development"
    load_dotenv()
else:
    os.environ["APP_ENV"] = "production"

# Set the locale
# locale.setlocale(locale.LC_TIME)

# Initialize Sentry
sentry_sdk.init(
    dsn="https://4cc58ab824b087258eac2255dbfd9e99@o1295012.ingest.sentry.io/4506705877860352",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

# Load environment variables
RS_LOGIN = os.getenv("RS_LOGIN")
RS_SECRET_KEY = os.getenv("RS_SECRET_KEY")
SYNC_LOGIN = os.getenv("SYNC_LOGIN")
SYNC_SECRET_KEY = os.getenv("SYNC_SECRET_KEY")
REMINDER_LOGIN = os.getenv("REMINDER_LOGIN")
REMINDER_SECRET_KEY = os.getenv("REMINDER_SECRET_KEY")

if (
    RS_LOGIN is None
    or RS_SECRET_KEY is None
    or REMINDER_LOGIN is None
    or REMINDER_SECRET_KEY is None
    or SYNC_SECRET_KEY is None
    or SYNC_LOGIN is None
):
    print("❌ All required environment variables must be set")
    exit(1)  # Exit the application if any required environment variable is missing
else:
    print("✅ All required environment variables are set")

# Configure the Flask app
config = {"DEBUG": False, "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300}
app.config.from_mapping(config)
port = int(os.environ.get("PORT", 8000))


# Initialize the cache
CACHE = Cache(app)

# Initialize the Pyrus API
pyrus_api = PyrusAPI(CACHE, RS_LOGIN, RS_SECRET_KEY)


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


@app.route("/step-reminder", methods=["GET", "POST"])
def reminder_step_page():
    reminder_step_page = ReminderStep(
        cache=CACHE,
        request=request,
        pyrus_secret_key=RS_SECRET_KEY if RS_SECRET_KEY is not None else "",
        pyrus_login=RS_LOGIN if RS_LOGIN is not None else "",
    )
    return reminder_step_page.process_request()


# @app.route("/reminder-payment-type", methods=["GET", "POST"])
# def reminder_peyment_type_page():
#     reminder_peyment_type = ReminderPaymentType(
#         CACHE,
#         request,
#         RPT_SECRET_KEY if RPT_SECRET_KEY is not None else "",
#         RPT_LOGIN if RPT_LOGIN is not None else "",
#     )
#     return reminder_peyment_type.process_request()


# @app.route("/remider-inactive-tasks", methods=["GET", "POST"])
# def remider_inactive_tasks_page():
#     remider_inactive_tasks = RemiderInactiveTasks(
#         cache=cache,
#         request=request,
#         pyrus_secret_key=RIT_SECRET_KEY,
#         pyrus_login=RIT_LOGIN,
#         sentry_sdk=sentry_sdk,
#     )
#     return remider_inactive_tasks.process_request()
@app.route("/webhook-sync-task-data", methods=["GET", "POST"])
def webhook_sync_task_data():
    TRACKED_FIELD = {
        "Заказ в Pyrus": ["№ ордеров из 1С", "№ ордера"],
    }
    sync_task_data = SyncTaskData(
        cache=CACHE,
        pyrus_secret_key=SYNC_SECRET_KEY if SYNC_SECRET_KEY is not None else "",
        pyrus_login=SYNC_LOGIN if SYNC_LOGIN is not None else "",
        sentry_sdk=sentry_sdk,
        traked_fields=TRACKED_FIELD,
    )
    return sync_task_data.process_request(request=request)


@app.route("/webhook-reminder", methods=["GET", "POST"])
def webhook_reminder():
    CATALOG_ID = "211552"
    TRACKED_FIELDS: TrackedFieldsType = {
        "text": {
            "Тип оплаты / Статус": "✅Нал (чек)",
        },
        "date": ["Дата отгрузки", "Дата планируемой оплаты"],
    }
    create_reminder_comment = CreateReminderComment(
        CATALOG_ID,
        CACHE,
        REMINDER_SECRET_KEY if REMINDER_SECRET_KEY is not None else "",
        REMINDER_LOGIN if REMINDER_LOGIN is not None else "",
        sentry_sdk,
        TRACKED_FIELDS,
    )
    return create_reminder_comment.process_request(request)


# initialize scheduler
scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()


@scheduler.task("cron", id="notify_job", hour=8, minute=5, timezone="Europe/Moscow")
def notify_job():
    catalog_id = "211552"
    notification = Notification_in_pyrus_task(
        catalog_id, REMINDER_LOGIN, REMINDER_SECRET_KEY, sentry_sdk, CACHE
    )
    notification.send()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, use_reloader=False)
    print("✅ Server is ready")
