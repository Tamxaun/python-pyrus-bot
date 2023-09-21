import os
import hmac
import hashlib
import json
import requests
from flask import Flask
from flask import request

SECRET_KEY = os.getenv("SECRET_KEY")
LOGIN = os.getenv("LOGIN")

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
            f"<a href='https://pyrus.com/t#pp{approval['person']['id']}'>{approval['person']['first_name']} {approval['person']['last_name']}</a>"
            for approval in approvals
            if str(approval["approval_choice"]) == "waiting"
        ]

        form_fields = _make_api_request(
            f"https://api.pyrus.com/v4/forms/{int(task['form_id'])}"
        )
        comment_text = str(
            (
                "{}<br>Приступить к исполнению следующего этапа <b>{}</b>!<br><code>{}</code>".format(
                    ", ".join(approvalNames), step["name"], form_fields
                )
            )
        )

        print("✅ Response is ready", '{{ "formatted_text":"{}" }}'.format(comment_text))

        return ('{{ "formatted_text":"{}" }}'.format(comment_text), 200)

    print("⚠️ No response")
    return "{}", 200


def _make_api_request(url):
    print("⌛ Making API request")

    secret = str.encode(SECRET_KEY)
    login = str.encode(LOGIN)

    auth = requests.get(
        "https://api.pyrus.com/v4/auth", params={"login": login, "security_key": secret}
    ).text

    print("✅ Auth is ready", auth)

    access_token = json.loads(auth)["access_token"]

    r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
    data = json.loads(r.text)

    print("✅ API request is ready", data)

    return data


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    print("✅ Server is ready")
