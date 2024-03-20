from flask import Flask

# Initialize the Flask app
app = Flask(__name__)


@app.route("/")
def index_page():
    return "<p>✅ Server is ready</p>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    print("✅ Server is ready")
