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
        return "🚫 Access Denied", 403

    secret = str.encode(SECRET_KEY)

    if secret is None or len(secret) == 0 or body is None or len(body) == 0:
        print(f"Body is {'set ✅' if body != None else 'not set ❌'}")
        print(f"Secret is {'set ✅' if secret != None else 'not set ❌'}")
        return "🚫 Access Denied", 403

    if _is_signature_correct(body, secret, signature):
        print("✅ Signature_correct")
        return _prepare_response(body.decode("utf-8"))
    else:
        return "🚫 Access Denied", 403


def _is_signature_correct(message, secret, signature):
    print("⌛ Checking signature")
    digest = hmac.new(secret, msg=message, digestmod=hashlib.sha1).hexdigest()
    return hmac.compare_digest(digest, signature.lower())


def _prepare_response(body):
    print("⌛ Preparing response")

    task = json.loads(body)["task"]
    current_step = int(task["current_step"])
    step = task["steps"][current_step - 1]
    approvals = task["approvals"][current_step - 1]
    comment = task["comments"][-1]
    print("✅ Task is ready", task)
    print("✅ current_step is ready", current_step)
    print("✅ step is ready", step)
    print("✅ approvals is ready", approvals)

    approval_choice = None
    approvals_added = None
    approvals_rerequested = None
    approvals_removed = None

    if "approval_choice" in comment:
        approval_choice = comment["approval_choice"]
    if "approvals_added" in comment:
        approvals_added = comment["approvals_added"]
        approved_step = int(approvals_added[-1][-1]["step"])

        if approved_step != current_step:
            print("⚠️ No response")
            return "{}", 200
    if "approvals_rerequested" in comment:
        approvals_rerequested = comment["approvals_rerequested"]
    if "approvals_removed" in comment:
        approvals_removed = comment["approvals_removed"]

    if (
        approval_choice is not None
        or approvals_added is not None
        or approvals_rerequested is not None
        or approvals_removed is not None
    ):
        approvalNames = [
            "@"
            + " ".join(
                [approval["person"]["first_name"], approval["person"]["last_name"]]
            )
            for approval in approvals
        ]
        comment_text = (
            "{}<br>Приступить к исполнению следующего этапа <b>{}</b>!".format(
                ", ".join(approvalNames), step["name"]
            )
        )
        print("✅ Response is ready")
        return ('{{ "formatted_text":"{}" }}'.format(comment_text), 200)

    print("⚠️ No response")
    return "{}", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    print("✅ Server is ready")
