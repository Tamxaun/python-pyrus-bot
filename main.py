import os
import hmac
import hashlib
import json
import requests
import random
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
    task_was_created = (
        task["create_date"] == task["last_modified_date"] and len(task["steps"]) == 1
    )
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
    print("⌛ Starting API Auth request to Pyrus")

    secret = str.encode(SECRET_KEY)
    login = str.encode(LOGIN)

    auth = requests.get(
        "https://api.pyrus.com/v4/auth", params={"login": login, "security_key": secret}
    ).text

    access_token = json.loads(auth)["access_token"]

    return access_token


def _pyrus_get_api_request(url):
    print("⌛ Making API GET request")

    access_token = _auth_pyrus()

    r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
    data = json.loads(r.text)

    print("✅ API GET request is ready", data)

    return data


def _pyrus_post_api_request(url, data):
    print("⌛ Making API POST request")

    access_token = _auth_pyrus()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    r = requests.post(url=url, data=data, headers=headers)
    data = r.json()

    print("✅ API POST request is ready", data, r.status_code)

    return data


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
        # Check if field has visibility_condition
        visibility_condition = task_field.get("visibility_condition")
        if visibility_condition is None:
            return True

        # Check if field has children (conditions) lv 1
        conditions = visibility_condition.get("children")
        if conditions is None:
            return False

        # TODO Check if field has no other level of children (conditions) but one
        #     {
        #      "id":172,
        #      "type":"file",
        #      "name":"Этикетки на упаковку",
        #      "tooltip":"",
        #      "visibility_condition":{
        #         "field_id":0,
        #         "condition_type":11,
        #         "value":"",
        #         "children":[
        #            {
        #               "field_id":51,
        #               "condition_type":3,
        #               "value":""
        #            }
        #         ]
        #      }
        #   },

        # Loop over conditions (children - lv 1)
        for condition in conditions:
            has_correct_value = (
                False  # Flag for checking if in one condition has correct value
            )

            # Get options of the current conditon (children - lv 2 - options))
            condition_options = condition.get("children")
            if condition_options is None:
                id = condition["field_id"]
                value = int(condition["value"])
                field = [field for field in task_fields if field["id"] == id][-1]
                # Check to find corrent field and if it has correct value
                if (
                    "value" in field
                    and "choice_ids" in field["value"]
                    and value in field["value"]["choice_ids"]
                ):
                    has_correct_value = True
                    break

            # Loop over options (children - lv 2)
            for option in condition_options:
                id = option["field_id"]
                value = int(option["value"])
                field = [field for field in task_fields if field["id"] == id][-1]

                # Check to find corrent field and if it has correct value
                if (
                    "value" in field
                    and "choice_ids" in field["value"]
                    and value in field["value"]["choice_ids"]
                ):
                    has_correct_value = True
                    break

            if not has_correct_value:
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
