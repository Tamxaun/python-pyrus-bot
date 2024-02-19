import unittest
from main import pyrus_api, sentry_sdk, cache, NDS_SECRET_KEY, NDS_LOGIN
from bot.reminder_step import format_fields
from bot.notify_date_shipment import NotifyDateShipment
from flask import Request


class Test_bot_reminder_step(unittest.TestCase):
    def test_field_scan(self):
        forms_test = pyrus_api.get_request("https://api.pyrus.com/v4/forms/1058514")
        task_test = pyrus_api.get_request("https://api.pyrus.com/v4/tasks/201740291")

        self.assertNotIsInstance(forms_test, type(None))
        self.assertNotIsInstance(task_test, type(None))

        if forms_test is not None and task_test is not None:
            fields = format_fields(
                forms_test["fields"],
                task_test["task"]["fields"],
                1,
                field_html_tag_begin="<li>",
                field_html_tag_end="</li>",
            )

            print("🚀 fields", fields)

        self.assertEqual(True, True)


class Test_bot_notify_date_shipment(unittest.TestCase):
    def test_find_field(self):
        try:
            task_test = pyrus_api.get_request(
                "https://api.pyrus.com/v4/tasks/201900023"
            )
        except:
            task_test = None

        if task_test is None or NDS_SECRET_KEY is None or NDS_LOGIN is None:
            raise Exception(task_test)

        def find_fields(fields: dict, name: str, type_field: str = "text"):
            print("🚚 run find_fields!")
            for field in fields:
                isNestedField = (
                    "value" in field
                    and isinstance(field["value"], dict)
                    and "fields" in field["value"]
                    and isinstance(field["value"]["fields"], dict)
                )

                print("field", field["name"])

                if isNestedField:
                    print("isNestedField", isNestedField)
                    return find_fields(field["value"]["fields"], name)
                if (
                    "type" in field
                    and field["type"] == "date"
                    and "name" in field
                    and field["name"] == "Дата отгрузки"
                ):
                    print("🚚 return a field")
                    return field

            return None

        field = find_fields(
            fields=task_test["task"]["fields"], name="Дата отгрузки", type_field="date"
        )

        print("field", field)


if __name__ == "__main__":
    unittest.main()
