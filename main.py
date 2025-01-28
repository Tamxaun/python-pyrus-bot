import os
from flask import Flask
from dotenv import load_dotenv, find_dotenv

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

app = Flask(__name__)


@app.route("/")
def index_page():
    return "<p>✅ Server is ready</p>"


if __name__ == "__main__":
    port = 8080
    app.run(debug=False, host="0.0.0.0", port=port)
