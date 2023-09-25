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
    task_fields = task["fields"]
    current_step_num = int(task["current_step"])
    current_step = task["steps"][current_step_num - 1]
    prev_step = task["steps"][current_step_num - 2] if current_step_num > 1 else []
    current_approvals = task["approvals"][current_step_num - 1]
    prev_approvals = (
        task["approvals"][current_step_num - 2] if current_step_num > 1 else []
    )
    comment = task["comments"][-1]

    print("✅ Task is ready", task)
    print("✅ current_step is ready", current_step_num)
    print("✅ step is ready", current_step)
    print("✅ approvals is ready", current_approvals)

    has_approval_choice = "approval_choice" in comment
    has_approvals_added = "approvals_added" in comment
    has_approvals_rerequested = "approvals_rerequested" in comment
    has_approvals_removed = "approvals_removed" in comment
    is_changed_step = "changed_step" in comment

    if has_approval_choice or is_changed_step:
        not_approved_names = [
            f"<a href='https://pyrus.com/t#pp{approval['person']['id']}'>{approval['person']['first_name']} {approval['person']['last_name']}</a>"
            for approval in current_approvals
            if str(approval["approval_choice"]) == "waiting"
        ]
        approved_names = [
            f"<a href='https://pyrus.com/t#pp{approval['person']['id']}'>{approval['person']['first_name']} {approval['person']['last_name']}</a>"
            for approval in prev_approvals
            if str(approval["approval_choice"]) == "approved"
        ]

        form = _make_api_request(
            f"https://api.pyrus.com/v4/forms/{int(task['form_id'])}"
        )
        form_fields = list(
            filter(
                lambda field: _filter_required_fields(field, current_step_num),
                form["fields"],
            )
        )
        fields = [
            f'{"✅" if "value" in task_field else "❌"}{form_field["name"]}'
            for form_field in form_fields
            for task_field in task_fields
            if form_field["id"] == task_field["id"]
        ]
        formatted_fields = [f"<li>{field}</li>" for field in fields]
        print("✅ formatted_fields is ready", formatted_fields)

        comment_text = ""
        if is_changed_step:  # step changed
            # comment_text = "{}<br>Отличная работа! 👍<br>Этап <b>{}</b> завершен ✅<br><br>{}<br>{}</b>Приступить к исполнению следующего этапа <b>{}</b><br><ul>{}</ul>".format(
            #     "<br>".join(approved_names),
            #     prev_step["name"],
            #     "<br>".join(not_approved_names),
            #     current_step["name"],
            #     "".join(formatted_fields),
            # )
            comment_text = f"{'{}<br>Отличная работа! 👍<br>Этап <b>{}</b> завершен ✅<br><br>'.format('<br>'.join(approved_names), prev_step['name']) if prev_step else ''}{'<br>'.join(not_approved_names)} Приступить к исполнению следующего этапа <b>{current_step['name']}</b><br><ul>{''.join(formatted_fields)}</ul>"
        elif (
            comment["approval_choice"] == "approved" and not is_changed_step
        ):  # step not changed
            comment_text = "{} выполнил свою часть работы на этапе <b>{}</b><br><br>{}<br>Ваша часть работы на этапе <b>{}</b> не завершена, приступите к её исполнению<br><ul>{}</ul>".format(
                ", ".join(approved_names),
                current_step["name"],
                "<br>".join(not_approved_names),
                current_step["name"],
                "".join(formatted_fields),
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


def _filter_required_fields(field, current_step_num):
    if "info" in field and "required_step" in field["info"]:
        return int(field["info"]["required_step"]) == current_step_num
    else:
        return False


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    print("✅ Server is ready")
