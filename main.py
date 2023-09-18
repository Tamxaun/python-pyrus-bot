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
    print("🔗 Enter to index route")

    body = request.data

    if "X-Pyrus-Sig" in request.headers:
        signature = request.headers["X-Pyrus-Sig"]
        print("✅ The request has the X-Pyrus-Sig.")
    else:
        print("⛔ The request does not have the X-Pyrus-Sig.")
        print(request.headers)
        return "🚫 Access Denied"

    secret = str.encode(SECRET_KEY)

    if secret is None or len(secret) == 0 or body is None or len(body) == 0:
        print(f"Body is {'set ✅' if body != None else 'not set ❌'}")
        print(f"Secret is {'set ✅' if secret != None else 'not set ❌'}")
        return format("🚫 Access Denied")
    if _is_signature_correct(body, secret, signature):
        print("✅ Signature_correct")
        return _prepare_response(body.decode("utf-8"))
    else:
        return "🚫 Access Denied"


def _is_signature_correct(message, secret, signature):
    print("⌛ Checking signature")
    digest = hmac.new(secret, msg=message, digestmod=hashlib.sha1).hexdigest()
    return hmac.compare_digest(digest, signature.lower())


def _prepare_response(body):
    print("⌛ Preparing response")
    task = json.loads(body)["task"]
    print("✅ Task is ready", task)
    comment = task["comments"][-1]

    if "text" not in comment:
        print("❌ There is no text in comment")
        return "{}"

    comment_author = comment["author"]
    author_name = comment_author["first_name"] + " " + comment_author["last_name"]
    comment_text = "Hello, {}! You said: {}".format(author_name, comment["text"])
    print("✅ Response is ready")
    return '{{ "text":"{}", "reassign_to":{{ "id":{} }} }}'.format(
        comment_text, comment_author["id"]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    print("✅ Server is ready")
