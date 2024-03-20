import os
from flask import Flask

# Initialize the Flask app
app = Flask(__name__)

# Configure the Flask app
config = {"DEBUG": False}
app.config.from_mapping(config)
port = int(os.environ.get("PORT", 5000))


@app.route("/", methods=["GET"])
def index_page():
    return "✅ Server is ready"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    print("✅ Server is ready")
