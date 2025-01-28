import os
from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import request
from flask_caching import Cache
from flask_apscheduler import APScheduler
import sentry_sdk

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    print("✅ Loaded environment variables from .env file")
else:
    print("⚠️ .env file not found, using server environment variables")
    print(
        "check some server environment variables, DEFAULT_PORT:",
        os.getenv("DEFAULT_PORT"),
    )


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
REMINDER_LOGIN = os.getenv("REMINDER_LOGIN")
REMINDER_SECRET_KEY = os.getenv("REMINDER_SECRET_KEY")
SYNC_LOGIN = os.getenv("SYNC_LOGIN")
SYNC_SECRET_KEY = os.getenv("SYNC_SECRET_KEY")
DEFAULT_PORT = os.getenv("DEFAULT_PORT")

required_env_vars = {
    "RS_LOGIN": RS_LOGIN,
    "RS_SECRET_KEY": RS_SECRET_KEY,
    "REMINDER_LOGIN": REMINDER_LOGIN,
    "REMINDER_SECRET_KEY": REMINDER_SECRET_KEY,
    "SYNC_LOGIN": SYNC_LOGIN,
    "SYNC_SECRET_KEY": SYNC_SECRET_KEY,
}

missing_vars = [var for var, value in required_env_vars.items() if value is None]

if missing_vars:
    print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)  # Exit the application if any required environment variable is missing
else:
    print("✅ All required environment variables are set")

app = Flask(__name__)
app.config["DEBUG"] = os.getenv("FLASK_ENV") or "development"
config = {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300}
app.config.from_mapping(config)
CACHE = Cache(app)

# initialize scheduler
scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()


@app.route("/")
def index_page():
    return "<p>✅ Server is ready</p>"


if __name__ == "__main__":
    port = int(DEFAULT_PORT) if DEFAULT_PORT is not None else 5000

    try:
        app.run(
            debug=app.config["DEBUG"],
            use_reloader=False,
            host="0.0.0.0",
            port=port,
        )
    except Exception as e:
        print(f"❌ Failed to start the server: {e}")
