import os
import hmac
import hashlib
import json
from flask import Flask
from flask import request

SECRET_KEY = os.getenv("SECRET_KEY")

app = Flask(__name__)
port = int(os.environ.get("PORT", 5000))


@app.route("/", methods=["GET", "POST"])
def index():
    body = request.data
    signature = request.headers["x-pyrus-sig"]
    secret = str.encode(SECRET_KEY)
    if secret is None:
        return "Access Denied (the secret key is not set)"
    if _is_signature_correct(body, secret, signature):
        print("✅ signature_correct")
        print("⌛ preparing response")
        return _prepare_response(body.decode("utf-8"))
    return "Access Denied"


def _is_signature_correct(message, secret, signature):
    digest = hmac.new(secret, msg=message, digestmod=hashlib.sha1).hexdigest()
    return hmac.compare_digest(digest, signature.lower())


def _prepare_response(body):
    task = json.loads(body)["task"]
    comment = task["comments"][-1]
    comment_author = comment["author"]
    author_name = comment_author["first_name"] + " " + comment_author["last_name"]
    comment_text = "Hello, {}! You said: {}".format(author_name, comment["text"])
    print("✅ response is ready")
    return '{{ "text":"{}", "reassign_to":{{ "id":{} }} }}'.format(
        comment_text, comment_author["id"]
    )


if __name__ == "__main__":
    print("✅ server is ready")
    app.run(host="0.0.0.0", port=port)
