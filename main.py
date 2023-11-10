import os
import hmac
import hashlib
import json
import requests
import random
from flask import Flask
from flask import request
from flask_caching import Cache

SECRET_KEY = os.getenv("SECRET_KEY")
LOGIN = os.getenv("LOGIN")

config = {"DEBUG": False, "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300}

app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)
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
    print("✅ Task is ready", task)
    task_fields = task["fields"]
    current_step_num = int(task["current_step"])
    print("✅ current_step_num is ready", current_step_num)
    filtered_step = [item for item in task["steps"] if item["step"] == current_step_num]
    if not filtered_step:
        print("⛔ Step is not found")
        print("⚠️ No response")
        return "{}", 200
    current_step = filtered_step[-1]
    print("✅ step is ready", current_step)
    prev_step = task["steps"][current_step_num - 2] if current_step_num > 1 else []
    task_was_created = (
        task["create_date"] == task["last_modified_date"] and len(task["steps"]) == 1
    )
    current_approvals = task["approvals"][current_step_num - 1]
    print("✅ approvals is ready", current_approvals)
    prev_approvals = (
        task["approvals"][current_step_num - 2] if current_step_num > 1 else []
    )
    comment = task["comments"][-1]

    has_approval_choice = "approval_choice" in comment
    has_approvals_added = "approvals_added" in comment
    has_approvals_rerequested = "approvals_rerequested" in comment
    has_approvals_removed = "approvals_removed" in comment
    is_changed_step = "changed_step" in comment

    if has_approval_choice or task_was_created or is_changed_step:
        current_not_approved_names = [
            f"<a href='https://pyrus.com/t#pp{approval['person']['id']}'>{approval['person']['first_name']} {approval['person']['last_name']}</a>"
            for approval in current_approvals
            if str(approval["approval_choice"]) == "waiting"
        ]
        current_approved_names = [
            f"<a href='https://pyrus.com/t#pp{approval['person']['id']}'>{approval['person']['first_name']} {approval['person']['last_name']}</a>"
            for approval in current_approvals
            if str(approval["approval_choice"]) == "approved"
        ]
        prev_approved_names = [
            f"<a href='https://pyrus.com/t#pp{approval['person']['id']}'>{approval['person']['first_name']} {approval['person']['last_name']}</a>"
            for approval in prev_approvals
            if str(approval["approval_choice"]) == "approved"
        ]

        form = _pyrus_get_api_request(
            f"https://api.pyrus.com/v4/forms/{int(task['form_id'])}"
        )

        if form is None:
            print("⚠️ Form not found, id:", task["form_id"], task)
            return "{}", 200

        # print("form", form)

        formatted_fields = _formatFields(
            form["fields"], task_fields, current_step_num, "<li>", "</li>"
        )
        # print("✅ formatted_fields is ready", formatted_fields)

        welcome_text_list = [
            "Отличная работа! 👍",
            "Так держать! 🙏",
            "Огонь 🔥",
            "Терпение и труд всё перетрут 💪",
            "Дай пять 🙏",
            "Супер",
            "Отпад 😎",
        ]
        welcome_text_random = random.choice(welcome_text_list)

        comment_text = ""

        if is_changed_step:  # step changed
            if prev_step:  # create success next stage message
                _pyrus_post_api_request(
                    # https://api.pyrus.com/v4/tasks/11613/comments
                    url=f"https://api.pyrus.com/v4/tasks/{int(task['id'])}/comments",
                    data=json.dumps(
                        {
                            "formatted_text": f"{'<br>'.join(prev_approved_names)}<br>{welcome_text_random}<br>Этап <b>{prev_step['name']}</b> завершен ✅<br><br>"
                        }
                    ),
                )
            comment_text = f"{'<br>'.join(current_not_approved_names)}<br>Приступить к исполнению следующего этапа <b>{current_step['name']}</b><ul>{''.join(formatted_fields)}</ul>"
        elif task_was_created:  # task was created
            comment_text = "{}<br>Приступить к исполнению первого этапа <b>{}</b> 🏁<br><ul>{}</ul>".format(
                "<br>".join(current_not_approved_names),
                current_step["name"],
                "".join(formatted_fields),
            )
        elif (
            comment["approval_choice"] == "approved" and not is_changed_step
        ):  # step not changed but was approved
            comment_text = "{} выполнил свою часть работы на этапе <b>{}</b><br><br>{}<br>Ваша часть работы на этапе <b>{}</b> не завершена, приступите к её исполнению ⏳<br><ul>{}</ul>".format(
                ", ".join(current_approved_names),
                current_step["name"],
                "<br>".join(current_not_approved_names),
                current_step["name"],
                "".join(formatted_fields),
            )
        elif (
            comment["approval_choice"] == "revoked" and not is_changed_step
        ):  # step not changed and was revoked
            comment_text = "{}<br>Ваша часть работы на этапе <b>{}</b> не завершена, приступите к её исполнению ⏳<br><ul>{}</ul>".format(
                "<br>".join(current_not_approved_names),
                current_step["name"],
                "".join(formatted_fields),
            )

        print("✅ Response is ready", '{{ "formatted_text":"{}" }}'.format(comment_text))

        return ('{{ "formatted_text":"{}" }}'.format(comment_text), 200)

    print("⚠️ No response")
    return "{}", 200


def _auth_pyrus():
    print("⌛ Starting API authentication request to Pyrus")

    secret = str.encode(SECRET_KEY)
    login = str.encode(LOGIN)

    auth = requests.get(
        "https://api.pyrus.com/v4/auth", params={"login": login, "security_key": secret}
    ).text

    access_token = json.loads(auth)["access_token"]

    if access_token is None:
        print("❌ Failed to get authentication token from Pyrus")
        return None

    print("✅ Success to get authentication token from Pyrus")

    return access_token


def _pyrus_get_api_request(url):
    print("⌛ Making API GET request")

    access_token = cache.get("auth_pyrus_token")
    if access_token is None:
        print(
            "⚠️ API GET Response authentication token is not in cache, creating a new one..."
        )
        access_token = _auth_pyrus()
        print("ℹ️ API GET Response saving authentication token in cache...")
        cache.set("auth_pyrus_token", access_token)

        if access_token is None:
            print("⚠️ API GET Response authentication token is not ready")
            return None
    else:
        print("ℹ️ API GET Response authentication token in cache")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    r = requests.get(url, headers=headers)
    r_data = json.loads(r.text)

    if r.status_code == 200:
        print("✅ API GET Response is ready", r.status_code)
        return r_data
    elif r.status_code == 401:
        print("⚠️ API GET Response authentication token is expired")
        access_token = _auth_pyrus()
        cache.set("auth_pyrus_token", access_token)
        _pyrus_get_api_request(url)
    else:
        print("⚠️ API GET Response is not ready", r.status_code)
        return None


def _pyrus_post_api_request(url, data):
    print("⌛ Making API POST request")

    access_token = cache.get("auth_pyrus_token")
    if access_token is None:
        print(
            "⚠️ API POST Response authentication token is not in cache, creating a new one..."
        )
        access_token = _auth_pyrus()
        print("ℹ️ API GET Response saving authentication token in cache...")
        cache.set("auth_pyrus_token", access_token)

        if access_token is None:
            print("⚠️ API POST Response authentication token is not ready")
            return None
    else:
        print("ℹ️ API POST Response authentication token in cache")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    r = requests.post(url=url, data=data, headers=headers)
    r_data = r.json()

    if r.status_code == 200:
        print("✅ API POST Response is ready", r.status_code)
        return r_data
    elif r.status_code == 401:
        print("⚠️ API POST Response authentication token is expired")
        access_token = _auth_pyrus()
        cache.set("auth_pyrus_token", access_token)
        _pyrus_post_api_request(url, data)
    else:
        print("⚠️ API POST Response is not ready", r.status_code)
        return None


def _filter_required_fields(field, current_step_num):
    if "info" in field and "required_step" in field["info"]:
        return int(field["info"]["required_step"]) == current_step_num
    else:
        return False


def _formatFields(
    form_fields,
    task_fields,
    required_step,
    field_html_tag_begin="<li>",
    field_html_tag_end="</li>",
):
    filtered_fields_list = []
    formated_fields_list = []

    def _filtered_field(field_id, task_fields):
        found_field = {}

        for fields_from_list in task_fields:
            # if second level
            if "value" in fields_from_list and "fields" in fields_from_list["value"]:
                # if this is group check visiability
                if not _check_visibility_condition(fields_from_list, task_fields):
                    continue

                # find field in group by id
                for fields_from_list_lv_2 in fields_from_list["value"]["fields"]:
                    if fields_from_list_lv_2["id"] == field_id:
                        found_field = fields_from_list_lv_2

            # if one level
            if fields_from_list["id"] == field_id:
                found_field = fields_from_list

        if not _check_visibility_condition(found_field, task_fields):
            return None

        return found_field

    def _check_visibility_condition(task_field, task_fields):
        def check_field(current_field):
            if (
                field is None
                or current_field["condition_type"] is None
                or current_field["field_id"] is None
                or current_field["value"] is None
            ):
                print(
                    "⛔ check_field is not ready",
                    field,
                    current_field["condition_type"],
                    current_field["field_id"],
                    current_field["value"],
                )
                return False

            condition_type = int(current_field["condition_type"])
            field_id = current_field["field_id"]
            value = current_field["value"]
            filtered_field = [field for field in task_fields if field["id"] == field_id]
            if not filtered_field:
                print("⛔ filtered_field is not ready")
                return False
            chosen_field = filtered_field[-1]

            # Check if field has condition_type 3 or 2 (Заполнено и не Заполнено)
            if condition_type == 2 or condition_type == 3:
                type_chosen_field = chosen_field.get("type")
                value_chosen_field = chosen_field.get("value")
                if type_chosen_field == "multiple_choice":
                    if (
                        condition_type == 2 and value_chosen_field is None
                    ):  # Не заполнено
                        return True
                    if (
                        condition_type == 3 and value_chosen_field is not None
                    ):  # Заполнено
                        return True
                if type_chosen_field == "checkmark":
                    if condition_type == 2 and value_chosen_field == "unchecked":
                        return True
                    if condition_type == 3 and value_chosen_field == "checked":
                        return True
            if (
                "value" in chosen_field
                and "choice_ids" in chosen_field["value"]
                and int(value) in chosen_field["value"]["choice_ids"]
            ):
                return True

            return False

        # Check if field has visibility_condition
        visibility_condition = task_field.get("visibility_condition")
        if visibility_condition is None:
            return True

        # Check if field has children (conditions) lv 1
        conditions = visibility_condition.get("children")
        if conditions is None:
            return False

        # Loop over conditions (children - lv 1)
        for condition in conditions:
            # Get options of the current conditon (children - lv 2 - options))
            condition_options = condition.get("children")
            if condition_options is None:
                is_valid_field = check_field(condition)
                if not is_valid_field:
                    return False
                continue

            has_correct_value_lv2 = (
                False  # Flag for checking if in one condition has correct value
            )

            # Loop over options (children - lv 2)
            for option in condition_options:
                # Check to find corrent field and if it has correct value
                if check_field(option):
                    has_correct_value_lv2 = True
                    break

            if not has_correct_value_lv2:
                return False

        return True

    for field in form_fields:
        if (
            "info" in field
            and "required_step" in field["info"]
            and field["info"]["required_step"] == required_step
        ):
            found_field = _filtered_field(field["id"], task_fields)
            if found_field:
                filtered_fields_list.append(found_field)
        elif "info" in field and "fields" in field["info"]:
            for field_lv_two in field["info"]["fields"]:
                if (
                    "info" in field_lv_two
                    and "required_step" in field_lv_two["info"]
                    and field_lv_two["info"]["required_step"] == required_step
                ):
                    found_field = _filtered_field(field_lv_two["id"], task_fields)
                    if found_field:
                        filtered_fields_list.append(found_field)

    for (
        filtered_field
    ) in filtered_fields_list:  # loop over filtered fields from form API
        for task_field in task_fields:  # loop over fields from task API
            if (
                "value" in task_field and "fields" in task_field["value"]
            ):  # field has second level of fields
                for task_field_lv_2 in task_field["value"]["fields"]:
                    if filtered_field["id"] == task_field_lv_2["id"]:
                        formated_fields_list.append(
                            f'{field_html_tag_begin}{"✅" if "value" in task_field_lv_2 and task_field_lv_2["value"] != "unchecked" or "value" in task_field_lv_2 and task_field_lv_2["value"] == "checked" else "✔️" if "value" in task_field_lv_2 and task_field_lv_2["value"] == "unchecked" else "❌"}{filtered_field["name"]}{field_html_tag_end}'
                        )
            else:
                if filtered_field["id"] == task_field["id"]:
                    formated_fields_list.append(
                        f'{field_html_tag_begin}{"✅" if "value" in task_field and task_field["value"] != "unchecked" or "value" in task_field and task_field["value"] == "checked" else "✔️" if "value" in task_field and task_field["value"] == "unchecked" else "❌"}{filtered_field["name"]}{field_html_tag_end}'
                    )

    return formated_fields_list


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    print("✅ Server is ready")
