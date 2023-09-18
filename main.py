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
    # body = request.data
    # signature = request.headers["x-pyrus-sig"]
    secret = str.encode(SECRET_KEY)
    # print(signature)
    print(secret)
    print(request)
    print(request.data)
    print(request.headers)
    # print(request.headers["x-pyrus-sig"])
    if request.headers.has_header("x-pyrus-sig"):
        print("The request has the x-pyrus-sig.")
    else:
        print("The request does not have the x-pyrus-sig.")
    # if (
    #     secret is None
    #     or len(secret) == 0
    #     or signature is None
    #     or len(signature) == 0
    #     or body is None
    #     or len(body) == 0
    # ):
    #     print(f"Body is {'set ✅' if body != None else 'not set ⛔'}")
    #     print(f"Signature is {'set ✅' if signature != None else 'not set ⛔'}")
    #     print(f"Secret is {'set ✅' if secret != None else 'not set ⛔'}")
    #     return format("Access Denied")
    # if _is_signature_correct(body, secret, signature):
    #     print("✅ Signature_correct")
    #     return _prepare_response(body.decode("utf-8"))
    # else:
    #     return "Access Denied"
    return "Access Denied"


def _is_signature_correct(message, secret, signature):
    print("⌛ Preparing response")
    digest = hmac.new(secret, msg=message, digestmod=hashlib.sha1).hexdigest()
    return hmac.compare_digest(digest, signature.lower())


def _prepare_response(body):
    task = json.loads(body)["task"]
    comment = task["comments"][-1]
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
